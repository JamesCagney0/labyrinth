"""
================================================================================
LABYRINTH — Dungeon Generation
================================================================================
Generates all dungeon floors, rooms, connections and NG+ world dungeons.
These methods are mixed into the Game class via DungeonMixin.
"""
from __future__ import annotations
import random
import json
import os
import logging
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from difflib import get_close_matches
from dataclasses import dataclass, field

logging.basicConfig(
    filename='game.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d - %(message)s',
    filemode='a'
)
logger = logging.getLogger(__name__)
from constants import GameConstants, BossConfig, RoomTemplateConfig
from room import Room
from typing import Dict, List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from player import Player


class DungeonMixin:
    """Dungeon generation methods. Mixed into Game."""

    def _generate_dungeon(self):
        """Generate complete dungeon with unique item tracking.
        Branches into NG+ content when player.ng_plus > 0."""
        ng = getattr(self.player, 'ng_plus', 0)
        if ng > 0:
            ng_world_key  = getattr(self.player, 'ng_world', 'fractured_labyrinth')
            ng_world_data = GameConstants.NG_PLUS_WORLDS.get(ng_world_key,
                            GameConstants.NG_PLUS_WORLDS['fractured_labyrinth'])
            ng_world_name = ng_world_data['display_name']
        else:
            ng_world_name = 'dungeon'
        logger.info(f"Starting dungeon generation (NG+{ng})...")
        print(f"\n*** Generating {ng_world_name if ng > 0 else 'dungeon'}...")
        self.floors = {}

        if ng > 0:
            self._generate_ng_plus_dungeon(ng)
            return

        # Track unique items across entire dungeon (items that should only spawn once)
        unique_item_types = {'rusty key', 'bone key', 'torch', 'ancient medallion'}
        
        # Pre-locate the special destination templates by name for injection
        vault_tmpl      = next(t for t in RoomTemplateConfig.SPECIAL_ROOMS if t.name == 'Locked Vault')
        bone_crypt_tmpl = next(t for t in RoomTemplateConfig.SPECIAL_ROOMS if t.name == 'Bone Crypt')

        # Track which floor each key lands on so we can guarantee a destination
        key_floor: dict = {}   # key_item_str -> floor_num

        total_rooms = 0
        all_floors_rooms: dict = {}  # floor_num -> rooms dict (built first pass)

        for floor_num in range(1, GameConstants.NUM_FLOORS + 1):
            print(f"Floor {floor_num}...", end=" ")
            rooms = {}

            if floor_num == 1:
                start_id = 'start'
                # Rusty key always starts in the entrance; record which floor it's on
                start_items = ['health potion', 'old map', 'rusty key']
                key_floor['rusty key'] = 1
                self.player.unique_items_spawned.add('rusty key')
                rooms[start_id] = Room("Entrance Hall", "The dungeon entrance awaits.", floor_num,
                                      start_items, {}, [],
                                      "Adamus the Loyal has set up shop here. Use 'shop' to trade.")
            else:
                start_id = f"floor{floor_num}_start"
                rooms[start_id] = Room(f"Floor {floor_num} Entrance", f"You arrive at floor {floor_num}.",
                                      floor_num, ['health potion'], {}, [],
                                      "Adamus the Loyal has set up shop here. Use 'shop' to trade.")

            templates = RoomTemplateConfig.get_templates_for_floor(floor_num)
            enemies   = RoomTemplateConfig.get_enemies_for_floor(floor_num)
            num_rooms = random.randint(GameConstants.MIN_ROOMS_PER_FLOOR - 2, GameConstants.MAX_ROOMS_PER_FLOOR - 2)

            # Filter out destination-only templates from the random pool so they
            # are only injected via the pairing logic below
            DEST_NAMES = {'Locked Vault', 'Bone Crypt'}
            # Deduplicate by name — same template name can appear in both
            # the theme config and SPECIAL_ROOMS, which random.sample would
            # treat as distinct objects and potentially pick both.
            seen_names = set()
            pool = []
            for t in templates:
                if t.name not in DEST_NAMES and t.name not in seen_names:
                    pool.append(t)
                    seen_names.add(t.name)
            selected = random.sample(pool, min(num_rooms, len(pool)))

            THINNED_ITEMS = {'health potion', 'energy drink', 'vitality tonic'}

            for i, template in enumerate(selected):
                room_id    = f"floor{floor_num}_room{i+1}"
                room_enemies = self._get_unique_enemies(enemies, template.enemy_count)

                if template.special_type == 'treasure':
                    room_enemies = ['treasure guardian'] + room_enemies[:1]

                items = self._filter_items_by_class(template.items.copy())
                filtered_items = []
                for item in items:
                    if item in unique_item_types:
                        if item not in self.player.unique_items_spawned:
                            filtered_items.append(item)
                            self.player.unique_items_spawned.add(item)
                            # Record which floor this key landed on
                            if item in ('rusty key', 'bone key'):
                                key_floor[item] = floor_num
                    elif item in THINNED_ITEMS and random.random() < 0.5:
                        pass
                    else:
                        filtered_items.append(item)

                rooms[room_id] = Room(template.name, template.description, floor_num,
                                     filtered_items, {}, room_enemies, template.atmosphere)

            all_floors_rooms[floor_num] = rooms

        # ── Second pass: inject destination rooms near their keys ─
        def _inject_dest(tmpl, key_name, search_floors):
            """Add destination room to the earliest floor in search_floors
               that doesn't already have one."""
            for fnum in search_floors:
                frooms = all_floors_rooms[fnum]
                if any(r.name == tmpl.name for r in frooms.values()):
                    return  # already there
            # Pick the first floor in range and inject
            fnum = search_floors[0]
            frooms = all_floors_rooms[fnum]
            enemies = RoomTemplateConfig.get_enemies_for_floor(fnum)
            idx = len(frooms)
            room_id = f"floor{fnum}_dest{idx}"
            room_enemies = self._get_unique_enemies(enemies, tmpl.enemy_count)
            frooms[room_id] = Room(tmpl.name, tmpl.description, fnum,
                                   tmpl.items.copy(), {}, room_enemies, tmpl.atmosphere)
            print(f"  [injected {tmpl.name} on F{fnum}]", end=" ")

        # Rusty key → Locked Vault should appear on the same floor or the next
        if 'rusty key' in key_floor:
            kf = key_floor['rusty key']
            dest_floors = list(range(kf, min(kf + 2, GameConstants.NUM_FLOORS) + 1))
            _inject_dest(vault_tmpl, 'rusty key', dest_floors)

        # Bone key → Bone Crypt should appear on the same floor or within 2 floors
        if 'bone key' in key_floor:
            kf = key_floor['bone key']
            dest_floors = list(range(kf, min(kf + 2, GameConstants.NUM_FLOORS) + 1))
            _inject_dest(bone_crypt_tmpl, 'bone key', dest_floors)

        # Now finalise: move rooms back into self.floors with boss/stairs rooms
        for floor_num in range(1, GameConstants.NUM_FLOORS + 1):
            rooms = all_floors_rooms[floor_num]
            
            boss_template = BossConfig.get_boss_room_template(floor_num)
            boss_config = BossConfig.generate(floor_num)
            boss_room_id = f"floor{floor_num}_boss"
            # Don't include champion's prize in initial items - added after boss defeat
            rooms[boss_room_id] = Room(boss_template.name, boss_template.description, floor_num,
                                       ['ultimate health potion'],  # FIXED: No champion's prize until boss defeated
                                       {}, [boss_config['name']], boss_template.atmosphere)
            
            if floor_num < GameConstants.NUM_FLOORS:
                stairs_id = f"floor{floor_num}_stairs"
                rooms[stairs_id] = Room("Ancient Stairway", "Stone stairs descend deeper.", floor_num)
            
            self._connect_rooms(rooms, start_id)
            
            self.floors[floor_num] = rooms
            total_rooms += len(rooms)
            print(f"{len(rooms)} rooms")
        
        for floor_num in range(1, GameConstants.NUM_FLOORS):
            stairs_id = f"floor{floor_num}_stairs"
            next_start = f"floor{floor_num+1}_start"
            if stairs_id in self.floors[floor_num] and next_start in self.floors.get(floor_num + 1, {}):
                self.floors[floor_num][stairs_id].exits['down'] = next_start
                self.floors[floor_num + 1][next_start].exits['up'] = stairs_id
        
        logger.info(f"Dungeon generated: {GameConstants.NUM_FLOORS} floors, {total_rooms} total rooms")
        print("*** Complete!")
    

    def _get_unique_enemies(self, pool: List[str], count: int) -> List[str]:
        """Get unique enemies from pool"""
        available = pool.copy()
        random.shuffle(available)
        return available[:min(count, len(available))]
    

    def _filter_items_by_class(self, items: List[str]) -> List[str]:
        """Replace mana items for non-mages"""
        if self.player.character_class == 'mage':
            return items
        
        replacements = {
            'magic scroll': 'energy drink',
            'ice crystal': 'power ring',
            'mana flower': 'armor piece'
        }
        return [replacements.get(i, i) for i in items]
    

    def _connect_rooms(self, rooms: Dict[str, Room], start_id: str):
        """Connect all rooms in floor"""
        directions = ['north', 'south', 'east', 'west']
        reverse = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east'}
        
        room_ids = list(rooms.keys())
        connected = {start_id}
        unconnected = set(room_ids) - connected
        
        while unconnected:
            current = random.choice(list(connected))
            target = random.choice(list(unconnected))
            
            available = [d for d in directions if d not in rooms[current].exits]
            if not available:
                continue
            
            direction = random.choice(available)
            rooms[current].exits[direction] = target
            rooms[target].exits[reverse[direction]] = current
            
            connected.add(target)
            unconnected.remove(target)
        
        for _ in range(len(room_ids) // 3):
            r1, r2 = random.sample(room_ids, 2)
            if r2 not in rooms[r1].exits.values():
                available = [d for d in directions if d not in rooms[r1].exits]
                if available:
                    direction = random.choice(available)
                    if reverse[direction] not in rooms[r2].exits:
                        rooms[r1].exits[direction] = r2
                        rooms[r2].exits[reverse[direction]] = r1
    

    def _generate_ng_plus_dungeon(self, ng: int):
        """Generate the selected NG+ world dungeon."""
        weapon_scale = max(1.0, getattr(self.player, 'ng_weapon_scale', 1.0))
        world_key   = getattr(self.player, 'ng_world', 'fractured_labyrinth')
        world_data  = GameConstants.NG_PLUS_WORLDS.get(world_key,
                      GameConstants.NG_PLUS_WORLDS['fractured_labyrinth'])
        world_name  = world_data['display_name']

        # Map world keys to their room template configs
        room_config_map = {
            'fractured_labyrinth': RoomTemplateConfig.NG_PLUS_THEME_CONFIG,
            'drowned_kingdom':     RoomTemplateConfig.NG_PLUS_DROWNED_THEME,
            'ashen_wastes':        RoomTemplateConfig.NG_PLUS_ASHEN_THEME,
            'mechanical_depths':   RoomTemplateConfig.NG_PLUS_MECHANICAL_THEME,
            'plague_cathedral':    RoomTemplateConfig.NG_PLUS_PLAGUE_THEME,
        }
        room_configs = room_config_map.get(world_key,
                       RoomTemplateConfig.NG_PLUS_THEME_CONFIG)

        total_rooms = 0
        self.floors = {}

        for floor_num in range(1, GameConstants.NUM_FLOORS + 1):
            print(f"Floor {floor_num}...", end=" ")
            rooms = {}

            start_id   = 'start' if floor_num == 1 else f"floor{floor_num}_start"
            start_name = f"{world_name} — Entry" if floor_num == 1 else f"{world_name} — Floor {floor_num}"
            start_desc = f"Adamus is here, somehow. He looks unsurprised." if floor_num == 1 else f"Deeper into {world_name}."
            rooms[start_id] = Room(
                start_name, start_desc, floor_num,
                ['health potion', 'old map'] if floor_num == 1 else ['health potion'],
                {}, [],
                "Adamus the Loyal has set up shop here. Use 'shop' to trade."
            )

            # Pick the right zone template pool for this floor
            zone_data = None
            for zone_key, zone_cfg in room_configs.items():
                floors_range = zone_cfg.get('floors', (1, 2))
                if floors_range[0] <= floor_num <= floors_range[1]:
                    zone_data = zone_cfg
                    break
            if not zone_data:
                zone_data = list(room_configs.values())[-1]

            enemies_pool = world_data['floor_themes'].get(floor_num,
                           list(world_data['enemies'].keys())[:3])

            templates = zone_data['templates']
            num_rooms = random.randint(
                GameConstants.MIN_ROOMS_PER_FLOOR - 2,
                GameConstants.MAX_ROOMS_PER_FLOOR - 2
            )
            selected  = random.sample(templates, min(num_rooms, len(templates)))

            THINNED   = {'health potion', 'energy drink', 'vitality tonic'}
            for i, tmpl in enumerate(selected):
                room_id      = f"floor{floor_num}_room{i+1}"
                room_enemies = self._get_unique_enemies(enemies_pool, tmpl.enemy_count)
                filtered     = [item for item in tmpl.items
                                if item not in THINNED or random.random() >= 0.45]
                rooms[room_id] = Room(
                    tmpl.name, tmpl.description, floor_num,
                    filtered, {}, room_enemies, tmpl.atmosphere
                )

            # Boss room
            boss_tmpl  = BossConfig.get_ng_plus_boss_room_template_for_world(floor_num, world_key)
            boss_cfg   = BossConfig.generate_ng_plus(floor_num, ng,
                                                      world_key=world_key,
                                                      weapon_scale=weapon_scale)
            boss_id    = f"floor{floor_num}_boss"
            rooms[boss_id] = Room(
                boss_tmpl.name, boss_tmpl.description, floor_num,
                ['ultimate health potion'], {},
                [boss_cfg['name']], boss_tmpl.atmosphere
            )

            if floor_num < GameConstants.NUM_FLOORS:
                stairs_id = f"floor{floor_num}_stairs"
                rooms[stairs_id] = Room(
                    f"{world_name} — Descent",
                    "Steps down into something worse.", floor_num
                )

            self._connect_rooms(rooms, start_id)
            self.floors[floor_num] = rooms
            total_rooms += len(rooms)
            print(f"{len(rooms)} rooms")

        for floor_num in range(1, GameConstants.NUM_FLOORS):
            stairs_id  = f"floor{floor_num}_stairs"
            next_start = f"floor{floor_num+1}_start"
            if stairs_id in self.floors[floor_num] and next_start in self.floors.get(floor_num+1, {}):
                self.floors[floor_num][stairs_id].exits['down'] = next_start
                self.floors[floor_num+1][next_start].exits['up'] = stairs_id

        logger.info(f"NG+ dungeon generated ({world_name}): {total_rooms} rooms")
        print(f"*** {world_name} is ready.")

