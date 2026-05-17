"""
LABYRINTH — Game orchestrator
"""
from __future__ import annotations
import random, json, os, logging
from typing import Dict, List, Optional, Set, Tuple, Any, TYPE_CHECKING, Callable
from difflib import get_close_matches
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

from constants import GameConstants, BossConfig, RoomTemplateConfig
from records import RecordsManager
from room import Room
from player import Player
from weapons import WeaponSystem, WeaponComparison
from items import ItemHandler
from combat import DamageCalculator, CombatSystem
from map_gen import MapGenerator

class CommandRegistry:
    """Command registration and fuzzy dispatch system."""

    def __init__(self):
        self.commands = {}
    
    def register(self, *names):
        """Decorator for registering commands"""
        def decorator(func):
            for name in names:
                self.commands[name.lower()] = func
            return func
        return decorator
    
    def execute(self, command: str, args: List[str], game: 'Game') -> None:
        """Execute command with smarter fuzzy matching"""
        cmd = command.lower()
        
        # Direct match
        if cmd in self.commands:
            try:
                self.commands[cmd](game, *args)
            except Exception as e:
                logging.error(f"Command error: {e}", exc_info=True)
                print(f"Error: {e}")
            return
        
        # Special case: direction typed but no exit that way
        if cmd in ['north', 'south', 'east', 'west', 'n', 's', 'e', 'w', 'up', 'down']:
            print(f"Can't go {cmd} from here!")
            return
        
        # Fuzzy matching — never suggest 'out' as a guess for unrelated commands
        matches = get_close_matches(cmd, self.commands.keys(), n=1, cutoff=0.7)
        if matches and matches[0] != 'out':
            print(f"Did you mean '{matches[0]}'?")
        else:
            print("Unknown command. Type 'help'")


#################################################################################
# HALL OF RECORDS — persistent cross-run stats
#################################################################################


class Game:
    """Main game controller"""
    
    def __init__(self):
        self.player: Optional[Player] = None
        self.floors: Optional[Dict[int, Dict[str, Room]]] = None
        self.running = True
        self.combat = None
        self.registry = CommandRegistry()
        self._register_commands()
        
    def _register_commands(self):
        """Register all game commands"""
        r = self.registry.register
        
        @r('help', 'h')
        def cmd_help(g): g.show_help()
        
        @r('look', 'l')
        def cmd_look(g): 
            g.look_around()
            g.show_room_summary()
        
        @r('go')
        def cmd_go(g, direction): g.move(direction)
        
        @r('north', 'n')
        def cmd_north(g): g.move('north')
        
        @r('south', 's')
        def cmd_south(g): g.move('south')
        
        @r('east', 'e')
        def cmd_east(g): g.move('east')
        
        @r('west', 'w')
        def cmd_west(g): g.move('west')
        
        @r('up')
        def cmd_up(g): g.move('up')
        
        @r('down')
        def cmd_down(g): g.move('down')
        
        # Exit secret rooms (and any 'out' direction)
        @r('out', 'o', 'back', 'b')
        def cmd_out(g): g.move('out')
        
        @r('take', 'get')
        def cmd_take(g, *args): 
            g.take_item(' '.join(args))
            g.show_room_summary()
        
        @r('takeall')
        def cmd_takeall(g): 
            g.take_all_items()
            g.show_room_summary()
        
        @r('inventory', 'inv', 'i')
        def cmd_inventory(g): 
            g.show_inventory()
            g.show_room_summary()
        
        @r('stats', 'status')
        def cmd_stats(g): 
            g.player.show_stats()
            g.show_room_summary()
        
        @r('fight', 'attack')
        def cmd_fight(g, *args): 
            g._fight_enemy_command(' '.join(args))
            if g.running:  # Only show if player survived
                g.show_room_summary()
        
        @r('fightall', 'attackall')
        def cmd_fightall(g): 
            g.fight_all_enemies()
            if g.running:  # Only show if player survived
                g.show_room_summary()
        
        @r('heal')
        def cmd_heal(g, *args): 
            ItemHandler.use_item(g.player, 'healing', ' '.join(args) if args else None)
            g.show_room_summary()
        
        @r('exp', 'experience')
        def cmd_exp(g, *args): 
            ItemHandler.use_item(g.player, 'experience', ' '.join(args) if args else None)
            g.show_room_summary()
        
        @r('equip', 'wear')
        def cmd_equip(g, *args): 
            g.equip_wearable(' '.join(args) if args else None)
            g.show_room_summary()
        
        @r('switch')
        def cmd_switch(g, *args): g.player.switch_weapon(' '.join(args) if args else None)
        
        @r('discard', 'drop')
        def cmd_discard(g, *args): 
            g.discard_item(' '.join(args))
            g.show_room_summary()
        
        @r('use')
        def cmd_use(g, *args):
            item = ' '.join(args)
            # Accept 'd20' as shorthand for the full item name
            if item == 'd20':
                item = "gambler's d20"
            g.use_special_item(item)
            g.show_room_summary()
        
        @r('upgrade')
        def cmd_upgrade(g):
            p = g.player

            # Fusion tier upgrade path (tiers 6-10)
            if getattr(p, 'fusion_parents', None):
                if p.class_tier >= 10:
                    print(f"  {p.get_class_title()} is at maximum tier (10).")
                elif not p.can_upgrade_fusion():
                    needed = GameConstants.FUSION_UPGRADE_LEVELS.get(p.class_tier + 1, '?')
                    print(f"  Need Level {needed} to advance to Tier {p.class_tier + 1}.")
                else:
                    old_title = p.get_class_title()
                    if p.upgrade_fusion():
                        new_title = p.get_class_title()
                        print(f"\n  ★★ FUSION ASCENSION — Tier {p.class_tier}!")
                        print(f"  {old_title}  →  {new_title}")
                        print(f"  +{GameConstants.FUSION_TIER_STAT_BONUS} to all stats  |  +15 max HP")
                g.show_room_summary()
                return

            # Base class upgrade path (tiers 1-5)
            if not p.can_upgrade_class():
                if p.class_tier >= 5:
                    print("  Tier 5 reached. Fuse your class in NG+ to continue ascending.")
                else:
                    levels = GameConstants.CLASS_UPGRADE_LEVELS
                    tier   = p.class_tier
                    needed = levels[tier - 1] if tier - 1 < len(levels) else '?'
                    print(f"  Need Level {needed} to upgrade.")
                return
            if p.upgrade_class():
                print(f"\n  ★ Class upgraded to Tier {p.class_tier}!")
                print(f"  You are now: {p.get_class_title()}")
            g.show_room_summary()
        
        @r('shop', 'buy')
        def cmd_shop(g): 
            g.open_shop()
            g.show_room_summary()
        
        @r('map')
        def cmd_map(g): 
            if g.player.has_map():
                g.show_map()
                g.show_room_summary()
            else:
                print("You need a map to use this command!")
                print("Look for one on the ground or buy one from a merchant.")
        
        @r('save')
        def cmd_save(g): g.save_game()
        
        @r('load')
        def cmd_load(g): g.load_game()
        
        @r('delete')
        def cmd_delete(g): g.delete_save()
        
        @r('quit', 'exit')
        def cmd_quit(g): g.quit_game()

        @r('fuse', 'fusion')
        def cmd_fuse(g): g.fuse_class_menu()
    
    def start_game(self):
        """Start game with looping menu"""
        TITLE = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ██╗      █████╗ ██████╗ ██╗   ██╗██████╗ ██╗███╗   ██╗████████╗██╗  ██╗  ║
║   ██║     ██╔══██╗██╔══██╗╚██╗ ██╔╝██╔══██╗██║████╗  ██║╚══██╔══╝██║  ██║  ║
║   ██║     ███████║██████╔╝ ╚████╔╝ ██████╔╝██║██╔██╗ ██║   ██║   ███████║  ║
║   ██║     ██╔══██║██╔══██╗  ╚██╔╝  ██╔══██╗██║██║╚██╗██║   ██║   ██╔══██║  ║
║   ███████╗██║  ██║██████╔╝   ██║   ██║  ██║██║██║ ╚████║   ██║   ██║  ██║  ║
║   ╚══════╝╚═╝  ╚═╝╚═════╝    ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝  ║
║                                                                              ║
║              ═══  The Dungeon Does Not Forgive. Will You?  ═══              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Deep beneath a forgotten city lies a shifting dungeon of ten floors,       ║
║  each darker and more lethal than the last. Adventurers enter seeking       ║
║  glory, treasure, or answers. Few return. Fewer still reach the bottom.     ║
║                                                                              ║
║  You are not the first to descend. You may not be the last.                 ║
║  But you might be the one who makes it out.                                 ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝"""
        while True:
            print(TITLE)
            print(f"  Version {GameConstants.VERSION}  |  LABYRINTH")
            print()
            print("  1. New Game")
            print("  2. Load Game")
            print("  3. Delete Save")
            print("  4. Hall of Records")
            print("  5. Quit")
            print()
            
            try:
                choice = input("\nChoice: ").strip()
                
                if choice == '1':
                    self._create_character()
                    break  # Exit menu loop and start game
                
                elif choice == '2':
                    if self.load_game():
                        break  # Successfully loaded, start game
                    # If load failed or cancelled, loop back to menu
                    continue
                
                elif choice == '3':
                    self.delete_save()
                    continue

                elif choice == '4':
                    RecordsManager.display()
                    try:
                        input("  [ Press Enter to return ]")
                    except KeyboardInterrupt:
                        pass
                    continue

                elif choice == '5':
                    print("\nGoodbye!")
                    return
                
                else:
                    print("Invalid choice. Please enter 1, 2, 3, or 4.")
                    continue
                    
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                return
        
        # Game starts here after menu selection
        # Guard: if NG+ or victory screen already ran a session and quit,
        # self.running will be False — don't re-enter.
        if not self.player:
            return
        self.running = True
        self.combat = CombatSystem(self)
        print("\nType 'help' for commands")
        self.look_around()
        self.show_room_summary()
        self._game_loop()
        # After _game_loop exits (quit or game over) return cleanly.
        # Do not loop back to the menu — main() handles the process exit.
        return
    
    def _game_loop(self):
        """Main game loop"""
        while self.running:
            try:
                cmd_input = input("\n> ").strip().lower()
                if not cmd_input:
                    continue
                
                parts = cmd_input.split()
                command = parts[0]
                args = parts[1:]
                
                self.registry.execute(command, args, self)

                if self.player and self.running:
                    self.player.show_status_summary()
                    
            except KeyboardInterrupt:
                logger.info("Game interrupted by user")
                print("\n\nInterrupted. Save before quitting!")
                break
            except Exception as e:
                logging.error(f"Game loop error: {e}", exc_info=True)
                print(f"Error: {e}")
    
    def _create_character(self):
        """Create new character"""
        try:
            name = input("Name: ").strip() or "Adventurer"
            
            rec = RecordsManager.load()
            void_unlocked = rec.get('void_walker_unlocked', False)
            print("\n╔════════════════════════════════════════╗")
            print("║  Choose Your Class                     ║")
            print("╠════════════════════════════════════════╣")
            print("║ 1. Warrior      — Strength & grit      ║")
            print("║ 2. Mage         — Arcane power         ║")
            print("║ 3. Rogue        — Speed & crits        ║")
            print("║ 4. Paladin      — Holy champion        ║")
            print("║ 5. Berserker    — Pure rage            ║")
            if void_unlocked:
                print("║ 6. Void Walker  — Beyond the veil      ║")
            else:
                print("║ 6. ???          — [Beat the game]      ║")
            print("╚════════════════════════════════════════╝")
            choice = input("Class: ").strip()
            class_map = {'1': 'warrior', '2': 'mage', '3': 'rogue',
                         '4': 'paladin', '5': 'berserker'}
            if choice == '6' and void_unlocked:
                class_map['6'] = 'void_walker'
            char_class = class_map.get(choice, 'warrior')

            # Class description
            descriptions = {
                'warrior':     'STR-focused melee fighter. High HP, grows into a Titan Knight.',
                'mage':        'INT/Arcane spellcaster. Fragile but devastating with magic.',
                'rogue':       'AGI/Luck master. Highest crit rate, stealth weapons.',
                'paladin':     'Holy melee warrior. Divine Smite ability, holy weapon bonus.',
                'berserker':   'Rage fighter. Built-in damage scaling as HP drops. Massive HP pool.',
                'void_walker': 'Lowest HP in the game. Crits deal 2.5x damage. Vampiric heals 25%.\n             Boss ability: Phase — once per fight, skip an enemy attack entirely.',
            }
            print(f"\n{descriptions[char_class]}")

            self.player = Player(name, char_class)

            weapons = WeaponSystem.create_starting_weapons()[char_class]
            print("\n╔══ Starting Weapon ══════════════════════════════════╗")
            for i, w in enumerate(weapons, 1):
                t_names = [GameConstants.WEAPON_TRAITS.get(t, {}).get('name', t) for t in w.get('traits', [])]
                t_str = f" [{', '.join(t_names)}]" if t_names else ""
                print(f"  {i}. {w['name']:22} {w['damage']:2} dmg{t_str}")
            print("╚════════════════════════════════════════════════════╝")
            try:
                wchoice = int(input("Choose (1-8): ").strip()) - 1
                weapon = weapons[wchoice] if 0 <= wchoice < len(weapons) else weapons[0]
            except (ValueError, IndexError):
                weapon = weapons[0]
            self.player.equip_weapon(weapon.copy())
            
            logger.info(f"New character: {name} ({char_class}) with {weapon['name']}")
            
            self._generate_dungeon()
            
            print(f"\nWelcome, {name} the {char_class.title()}!")
            print(f"Weapon: {weapon['name']}")
            print(f"{GameConstants.NUM_FLOORS} floors await!")
            print(f"\n=== LABYRINTH v{GameConstants.VERSION} ===")
            
        except Exception as e:
            logging.error(f"Character creation error: {e}", exc_info=True)
            self.player = Player("Adventurer", "warrior")
            self._generate_dungeon()
    
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
        unique_item_types = {'rusty key', 'bone key', 'torch', 'ancient medallion',
                              'journal_1','journal_2','journal_3','journal_4','journal_5',
                              "gambler's d20"}
        # Which floor each journal entry appears on
        JOURNAL_FLOORS = {2: 'journal_1', 4: 'journal_2', 5: 'journal_3',
                          7: 'journal_4', 9: 'journal_5'}
        
        # Pre-locate the special destination templates by name for injection
        vault_tmpl          = next(t for t in RoomTemplateConfig.SPECIAL_ROOMS if t.name == 'Locked Vault')
        bone_crypt_tmpl     = next(t for t in RoomTemplateConfig.SPECIAL_ROOMS if t.name == 'Bone Crypt')
        forgotten_game_tmpl = RoomTemplateConfig.FORGOTTEN_GAME_ROOM

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
            DEST_NAMES = {'Locked Vault', 'Bone Crypt', 'Forgotten Game Room'}
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

                # Calculate wearable cap for dungeon generation
                p_lvl      = self.player.level
                max_stack  = 1 if p_lvl < 5 else 2 if p_lvl < 10 else 3 if p_lvl < 15 else 4
                def _gen_at_cap(item_name):
                    if item_name not in GameConstants.WEARABLE_ITEMS:
                        return False
                    if GameConstants.WEARABLE_ITEMS[item_name].get('cursed'):
                        return False
                    count = sum(1 for w in self.player.wearables if w['item'] == item_name)
                    return count >= max_stack

                for item in items:
                    if item in unique_item_types:
                        if item not in self.player.unique_items_spawned:
                            filtered_items.append(item)
                            self.player.unique_items_spawned.add(item)
                            if item in ('rusty key', 'bone key'):
                                key_floor[item] = floor_num
                    elif item in THINNED_ITEMS and random.random() < 0.5:
                        pass
                    elif _gen_at_cap(item):
                        pass  # skip wearables the player is already capped on
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
            logger.debug(f"Injected {tmpl.name} on F{fnum}")

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

        # Forgotten Game Room — always spawns once, on a random floor between 3 and 7
        if "gambler's d20" not in self.player.unique_items_spawned:
            fg_floor = random.randint(3, 7)
            fg_rooms = all_floors_rooms[fg_floor]
            fg_id    = f"floor{fg_floor}_forgotten"
            fg_rooms[fg_id] = Room(
                forgotten_game_tmpl.name,
                forgotten_game_tmpl.description,
                fg_floor,
                list(forgotten_game_tmpl.items),
                {}, [],
                forgotten_game_tmpl.atmosphere
            )
            self.player.unique_items_spawned.add("gambler's d20")

        # Finalise: add boss/stairs rooms then connect and store
        for floor_num in range(1, GameConstants.NUM_FLOORS + 1):
            rooms = all_floors_rooms[floor_num]
            floor_start_id = 'start' if floor_num == 1 else f"floor{floor_num}_start"

            boss_template = BossConfig.get_boss_room_template(floor_num)
            boss_config   = BossConfig.generate(floor_num)
            boss_room_id  = f"floor{floor_num}_boss"
            rooms[boss_room_id] = Room(boss_template.name, boss_template.description, floor_num,
                                       ['ultimate health potion'],
                                       {}, [boss_config['name']], boss_template.atmosphere)

            if floor_num < GameConstants.NUM_FLOORS:
                stairs_id = f"floor{floor_num}_stairs"
                rooms[stairs_id] = Room("Ancient Stairway", "Stone stairs descend deeper.", floor_num)

            self._connect_rooms(rooms, floor_start_id)

            self.floors[floor_num] = rooms
            total_rooms += len(rooms)
            logger.debug(f"Floor {floor_num}: {len(rooms)} rooms")
        
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
    
    def get_current_room(self) -> Room:
        """Get player's current room"""
        return self.floors[self.player.current_floor][self.player.current_room]
    
    def show_room_summary(self):
        """Display quick summary of current room"""
        room = self.get_current_room()
        print(f"\n--- {room.name} ---")
        
        if room.items:
            print(f"Items: {', '.join(room.items)}")
        else:
            print("Items: None")
        
        if room.exits:
            exits_list = []
            for direction, target_id in room.exits.items():
                # Check if the exit leads to a visited room
                is_visited = target_id in self.player.visited_rooms
                
                if direction == 'out':
                    exits_list.append("OUT (back to previous room)")
                    continue
                elif direction == 'secret':
                    continue  # Never hint at secret exits in room summary
                elif direction in ['up', 'down']:
                    marker = direction.upper()
                else:
                    marker = direction[0].upper()
                
                # Add (?) if unexplored
                if not is_visited:
                    marker += "(?)"
                
                exits_list.append(marker)
            print(f"Exits: {' | '.join(exits_list)}")
        else:
            print("Exits: None")
    
    def show_help(self):
        """Context-aware help"""
        room = self.get_current_room()
        
        print("\n" + "="*40)
        print("COMMANDS")
        print("="*40)
        print("look | go <dir> (n/s/e/w/up/down)")
        
        if room.enemies:
            print("fight <enemy> | fightall")
        
        if room.items or self.player.inventory:
            print("take <item> | takeall")
        
        print("inventory | stats")
        
        if any(i in GameConstants.HEALING_ITEMS for i in self.player.inventory):
            print("heal")
        if any(i in GameConstants.EXPERIENCE_ITEMS for i in self.player.inventory):
            print("exp")
        if any(i in GameConstants.WEARABLE_ITEMS for i in self.player.inventory):
            print("equip")
        if any(i in GameConstants.ACTIONABLE_ITEMS for i in self.player.inventory) or self.player.special_items:
            print("use <item>")
        if self.player.inventory_weapons:
            print("switch")
        if self.player.inventory or self.player.special_items:
            print("discard <item>")
        
        if self.player.current_floor == 1 and self.player.current_room == 'start':
            print("shop - Merchant available HERE")
        elif self.player.current_floor > 1 and 'start' in self.player.current_room:
            print("shop - Merchant available HERE")
        elif self.player.gold_coins > 0:
            print("shop - Visit floor start for merchant")
        
        if self.player.can_upgrade_class():
            print("upgrade")
        
        print("map | save | load | delete | quit")
        
        if self.player.has_map():
            print("\n★ Map doesn't use inventory space")
        if room.enemies and len(room.enemies) > 1:
            print("★ Use 'fightall' to fight all enemies")
        
        print("="*40)
    
    def look_around(self):
        """Look at current room"""
        room = self.get_current_room()
        room.describe()
        self.player.visited_rooms.add(self.player.current_room)
    
    def move(self, direction: str):
        """Move in direction"""
        room = self.get_current_room()
        
        if direction not in room.exits:
            print("Can't go that way!")
            return
        
        next_id = room.exits[direction]
        
        if direction == 'down':
            boss_floor  = self.player.current_floor
            ng          = getattr(self.player, 'ng_plus', 0)
            if ng > 0:
                world_key   = getattr(self.player, 'ng_world', 'fractured_labyrinth')
                boss_config = BossConfig.generate_ng_plus(boss_floor, ng, world_key,
                                                           weapon_scale=max(1.0, getattr(self.player, 'ng_weapon_scale', 1.0)))
            else:
                boss_config = BossConfig.generate(boss_floor)
            if boss_config['name'] not in self.player.bosses_defeated:
                print(f"! Blocked! Defeat {boss_config['name']} first!")
                return
        
        old_floor = self.player.current_floor
        
        if direction in ['down', 'up'] and 'floor' in next_id:
            next_floor = int(next_id.split('_')[0].replace('floor', ''))
            if next_floor != self.player.current_floor:
                self.player.current_floor = next_floor
                print(f"\n→ Floor {self.player.current_floor}")
                RecordsManager.update(total_floors_cleared=1,
                                      best_floor_reached=next_floor)
                # Floor lore (v7.5.2)
                lore = GameConstants.FLOOR_LORE.get(next_floor)
                if lore:
                    print()
                    print(lore)
                
                if not self.player.has_map() and old_floor != next_floor:
                    start_room_id = f"floor{next_floor}_start"
                    if start_room_id in self.floors[next_floor]:
                        start_room = self.floors[next_floor][start_room_id]
                        if 'old map' not in start_room.items:
                            start_room.items.append('old map')
                            logger.info(f"Spawned new map in floor {next_floor} start room (player left previous map behind)")
                            print("★ You notice a map on the ground here!")
        
        self.player.current_room = next_id
        self.player.visited_rooms.add(next_id)
        print(f"You go {direction}.")

        # Status effects tick between rooms
        if getattr(self.player, 'status_effects', {}):
            for eff, turns in list(self.player.status_effects.items()):
                se = GameConstants.STATUS_EFFECTS.get(eff, {})
                if 'dmg_per_turn' in se and turns > 0:
                    tick = max(1, se['dmg_per_turn'] // 2)
                    self.player.health -= tick
                    print(f"  {se['icon']} {eff.capitalize()} ticks: -{tick} HP "
                          f"({turns-1} turns left)")
                    if self.player.health <= 0:
                        self.player.health = 1
                self.player.status_effects[eff] = turns - 1
            self.player.status_effects = {
                k: v for k, v in self.player.status_effects.items() if v > 0
            }

        self.look_around()
        self.show_room_summary()
    
    def show_inventory(self):
        """Show organized inventory"""
        print(f"\n=== INVENTORY ({len(self.player.inventory)}/{self.player.max_inventory}) ===")
        
        if self.player.weapon:
            print(f"Equipped: {self.player.weapon['name']} ({self.player.weapon['damage']} dmg)")
        
        if self.player.special_items:
            print("\n[Special Items - No inventory space]")
            for item in self.player.special_items:
                print(f"  ★ {item}")
        
        if not self.player.inventory and not self.player.special_items:
            print("Empty")
            return
        
        categories = {
            'Healing': [i for i in self.player.inventory if i in GameConstants.HEALING_ITEMS],
            'Experience': [i for i in self.player.inventory if i in GameConstants.EXPERIENCE_ITEMS],
            'Wearables': [i for i in self.player.inventory if i in GameConstants.WEARABLE_ITEMS],
            'Special': [i for i in self.player.inventory if i in GameConstants.ACTIONABLE_ITEMS],
            'Weapons': [i for i in self.player.inventory if i.startswith("WEAPON:")],
            'Other': [i for i in self.player.inventory if not any([
                i in GameConstants.HEALING_ITEMS, i in GameConstants.EXPERIENCE_ITEMS,
                i in GameConstants.WEARABLE_ITEMS, i in GameConstants.ACTIONABLE_ITEMS,
                i.startswith("WEAPON:")
            ])]
        }
        
        for category, items in categories.items():
            if not items:
                continue
            print(f"\n{category}:")
            if category == 'Wearables':
                from collections import Counter
                counts = Counter(items)
                entries = []
                for item, count in counts.items():
                    wi = GameConstants.WEARABLE_ITEMS.get(item, {})
                    stat_lbl = {'strength':'STR','intelligence':'INT','agility':'AGI',
                                'luck':'LCK','vitality':'VIT','faith':'FTH','arcane':'ARC'
                                }.get(wi.get('stat',''), wi.get('stat','?').upper()[:3])
                    bonus = wi.get('bonus', '?')
                    prefix = f"[{count}]" if count > 1 else ""
                    entries.append(f"{prefix}{item} (+{bonus} {stat_lbl})")
                for i in range(0, len(entries), 2):
                    left = entries[i]
                    right = entries[i+1] if i+1 < len(entries) else ""
                    print(f"  {left:<32}  {right}")
            else:
                for item in items:
                    display = item[8:] if item.startswith("WEAPON:") else item
                    print(f"  - {display}")
    
    def take_item(self, item_name: str):
        """Take item from room"""
        if not item_name:
            print("Take what?")
            return
        
        room = self.get_current_room()
        
        if room.enemies:
            print("! Defeat enemies first!")
            return
        
        if item_name not in room.items:
            print(f"No '{item_name}' here.")
            return
        
        if not self.player.can_add_item() and item_name not in GameConstants.WEARABLE_ITEMS and item_name != 'old map':
            print("Inventory full!")
            return
        
        room.items.remove(item_name)
        
        if item_name == "weapon cache":
            self._handle_weapon_cache()
        elif item_name == "champion's prize":
            self._handle_champions_prize()
        else:
            self._handle_regular_item(item_name)
    
    def take_all_items(self):
        """Pick up all items in the room"""
        room = self.get_current_room()
        
        if room.enemies:
            print("! Defeat enemies first!")
            return
        
        if not room.items:
            print("No items here.")
            return
        
        taken = 0
        for item in room.items[:]:
            if item == 'old map' or item in GameConstants.WEARABLE_ITEMS or self.player.can_add_item():
                room.items.remove(item)
                if item == "weapon cache":
                    self._handle_weapon_cache()
                elif item == "champion's prize":
                    self._handle_champions_prize()
                else:
                    self._handle_regular_item(item)
                taken += 1
        
        if taken:
            print(f"\n+ Picked up {taken} item(s)")
        if room.items:
            print(f"X Inventory full! Left: {', '.join(room.items)}")
    
    def _handle_weapon_cache(self):
        """Handle opening a weapon cache"""
        new_weapon = WeaponSystem.generate_weapon(self.player)
        
        if new_weapon.get('special') == 'instant_kill':
            print("\n*** LEGENDARY GOLDEN GUN! 6 INSTANT KILLS! ***")
        
        comparison = WeaponComparison.compare_weapons(new_weapon, self.player.weapon, self.player)
        print(comparison)
        
        if not self.player.weapon or new_weapon['damage'] > self.player.weapon['damage']:
            try:
                if input("\nEquip this weapon? (y/n): ").strip().lower() in ['y', 'yes']:
                    if self.player.weapon:
                        print(f"Replaced {self.player.weapon['name']}")
                    self.player.equip_weapon(new_weapon)
                else:
                    self.player.add_weapon_to_inventory(new_weapon)
            except KeyboardInterrupt:
                self.player.add_weapon_to_inventory(new_weapon)
        else:
            try:
                if input("\nWeaker weapon. Take anyway? (y/n): ").strip().lower() in ['y', 'yes']:
                    self.player.add_weapon_to_inventory(new_weapon)
                else:
                    print("Left weapon behind.")
            except KeyboardInterrupt:
                print("Left weapon behind.")
    
    def _handle_champions_prize(self):
        """Handle champion's prize - FIXED to respect level restrictions"""
        # Choose rarity based on player level
        if self.player.level >= 15:
            rarity = random.choice(['epic', 'legendary', 'mythic'])
        elif self.player.level >= 10:
            rarity = random.choice(['epic', 'legendary'])
        elif self.player.level >= 5:
            rarity = 'epic'
        else:
            rarity = 'rare'  # For early game, give rare instead
        
        weapon = WeaponSystem.generate_weapon(self.player, rarity)
        
        print(f"\n*** CHAMPION'S PRIZE! ({rarity.upper()}) ***")
        comparison = WeaponComparison.compare_weapons(weapon, self.player.weapon, self.player)
        print(comparison)
        
        try:
            if input("\nEquip this weapon? (y/n): ").strip().lower() in ['y', 'yes']:
                if self.player.weapon:
                    print(f"Replaced {self.player.weapon['name']}")
                self.player.equip_weapon(weapon)
            else:
                self.player.add_weapon_to_inventory(weapon)
        except KeyboardInterrupt:
            self.player.add_weapon_to_inventory(weapon)
    
    def _handle_regular_item(self, item: str):
        """Handle picking up a regular item"""
        if item in GameConstants.EXPERIENCE_ITEMS:
            self.player.gain_experience(GameConstants.EXPERIENCE_ITEMS[item]['amount'])
            return
        
        if item == 'golden coin':
            coins = random.randint(3, 10)
            self.player.gold_coins += coins
            self.player.total_gold_earned += coins
            print(f"+ {coins} gold coins!")
            return
        
        if item in GameConstants.WEARABLE_ITEMS:
            self.player.inventory.append(item)
            print(f"+ {item} (wearable)")
            return
        
        self.player.add_item(item)
    
    def _fight_enemy_command(self, enemy_name: str):
        """Command handler: routes fight to CombatSystem."""
        if not enemy_name:
            print("Fight what?")
            return
        
        room = self.get_current_room()
        
        matching = None
        for e in room.enemies:
            if e.lower() == enemy_name.lower():
                matching = e
                break
        
        if not matching:
            print(f"No '{enemy_name}' here!")
            if room.enemies:
                print(f"Enemies: {', '.join(room.enemies)}")
            return
        
        if not self.player.weapon:
            print("! No weapon!")
            try:
                if input("Fight anyway? (y/n): ").strip().lower() not in ['y', 'yes']:
                    return
            except KeyboardInterrupt:
                return
        
        # Check base game boss names
        is_boss = any(matching == BossConfig.generate(f)['name'] for f in range(1, 11))
        # Also check all NG+ world boss names
        if not is_boss:
            for world_data in GameConstants.NG_PLUS_WORLDS.values():
                if any(matching == world_data['boss_data'][f]['name']
                       for f in range(1, 11)):
                    is_boss = True
                    break

        # ── Pre-combat weapon swap option (regular fights only) ───
        if not is_boss and self.player.inventory_weapons:
            en_lower = matching.lower()
            weaknesses = GameConstants.ENEMY_WEAKNESSES.get(en_lower, {})
            # Check if any stored weapon has a weakness advantage current doesn't
            current_traits = set(self.player.weapon.get('traits', [])) if self.player.weapon else set()
            current_match = bool(current_traits & set(weaknesses.keys()))
            for stored_w in self.player.inventory_weapons:
                stored_traits = set(stored_w.get('traits', []))
                if stored_traits & set(weaknesses.keys()) and not current_match:
                    trait_names = [GameConstants.WEAPON_TRAITS.get(t, {}).get('name', t)
                                   for t in stored_traits & set(weaknesses.keys())]
                    print(f"  ◈ TIP: {stored_w['name']} ({', '.join(trait_names)}) is effective against {matching}!")
            try:
                prep = input("Swap weapon before fighting? (y/n, Enter to skip): ").strip().lower()
                if prep in ('y', 'yes', 'swap'):
                    self.player.switch_weapon()
            except KeyboardInterrupt:
                pass

        if is_boss:
            success = self.combat.fight_boss(matching, self.player, room)
        else:
            success = self.combat.fight_enemy(matching, self.player, room)
        
        if not success:
            self.running = False
    
    def fight_all_enemies(self):
        """Fight all enemies in room sequentially"""
        room = self.get_current_room()
        
        if not room.enemies:
            print("No enemies here!")
            return
        
        if not self.player.weapon:
            print("! No weapon!")
            try:
                if input("Fight anyway? (y/n): ").strip().lower() not in ['y', 'yes']:
                    return
            except KeyboardInterrupt:
                return
        
        bosses = [e for e in room.enemies if any(e == BossConfig.generate(f)['name'] for f in range(1, 11))]
        if bosses:
            print(f"! Cannot use 'fightall' on bosses: {', '.join(bosses)}")
            print("Fight bosses individually with 'fight <boss name>'")
            return
        
        total_enemies = len(room.enemies)
        print(f"\n*** Fighting all {total_enemies} enemies! ***")
        print(f"Starting HP: {self.player.health}/{self.player.max_health}\n")
        
        defeated = 0
        enemies_copy = room.enemies.copy()
        
        for enemy_name in enemies_copy:
            if enemy_name not in room.enemies:
                continue
            
            print(f"\n--- Enemy {defeated + 1}/{total_enemies}: {enemy_name} ---")
            
            enemy_stats = GameConstants.ENEMIES.get(enemy_name.lower())
            if enemy_stats:
                estimated_damage = enemy_stats['damage'] - (self.player.stats['agility'] // 3)
                estimated_damage = max(1, estimated_damage)
                
                if self.player.health <= estimated_damage * 2:
                    print(f"\n! WARNING: Low health ({self.player.health} HP)")
                    print(f"! {enemy_name} deals ~{estimated_damage} damage per hit")
                    print("! Consider:")
                    print("  - Use 'heal' to restore health")
                    print("  - Fight enemies one at a time")
                    try:
                        choice = input("Continue fighting? (y/n): ").strip().lower()
                        if choice not in ['y', 'yes']:
                            print("Stopped fighting. Enemies remaining.")
                            return
                    except KeyboardInterrupt:
                        print("\nStopped fighting.")
                        return
            
            success = self.combat.fight_enemy(enemy_name, self.player, room)
            
            if not success:
                self.running = False
                return
            
            defeated += 1
        
        print(f"\n*** VICTORY! Defeated all {defeated} enemies! ***")
        print(f"Final HP: {self.player.health}/{self.player.max_health}")
    
    def equip_wearable(self, item_name: Optional[str]):
        """Equip wearable item with level-gated stack limit."""
        if not item_name:
            wearables = [i for i in self.player.inventory if i in GameConstants.WEARABLE_ITEMS]
            if not wearables:
                print("No wearables!")
                return

            from collections import Counter
            stat_labels = {'strength':'STR','intelligence':'INT','agility':'AGI',
                           'luck':'LCK','vitality':'VIT','faith':'FTH','arcane':'ARC'}
            counts = Counter(wearables)
            unique_wearables = list(dict.fromkeys(wearables))
            print("Wearables:")
            for i, item in enumerate(unique_wearables, 1):
                effect = GameConstants.WEARABLE_ITEMS[item]
                lbl    = stat_labels.get(effect['stat'], effect['stat'].upper()[:3])
                prefix = f"[{counts[item]}]" if counts[item] > 1 else ""
                print(f"  {i}. {prefix}{item} (+{effect['bonus']} {lbl})")
            wearables = unique_wearables

            try:
                choice = int(input("Choose: ")) - 1
                if 0 <= choice < len(wearables):
                    item_name = wearables[choice]
                else:
                    return
            except (ValueError, KeyboardInterrupt):
                print("Cancelled")
                return

        if not (item_name and item_name in self.player.inventory
                and item_name in GameConstants.WEARABLE_ITEMS):
            print(f"You don't have '{item_name}' or it's not a wearable")
            return

        # ── Level-gated stack limit ───────────────────────────────
        # Cursed items are powerful enough on their own — no stacking
        effect = GameConstants.WEARABLE_ITEMS[item_name]
        if not effect.get('cursed'):
            lvl = self.player.level
            if   lvl < 5:  max_stack = 1
            elif lvl < 10: max_stack = 2
            elif lvl < 15: max_stack = 3
            else:           max_stack = 4

            already = sum(1 for w in self.player.wearables if w['item'] == item_name)
            if already >= max_stack:
                needed_lvl = {1: 5, 2: 10, 3: 15}.get(already, None)
                if needed_lvl:
                    print(f"  You're already wearing {already}x {item_name}.")
                    print(f"  Reach Level {needed_lvl} to equip another copy.")
                else:
                    print(f"  Maximum {max_stack} copies of {item_name} allowed.")
                return

        self.player.inventory.remove(item_name)
        if effect.get('cursed'):
            if effect.get('hp_penalty'):
                self.player.max_health += effect['hp_penalty']
                self.player.health = min(self.player.health, self.player.max_health)
            self.player.stats[effect['stat']] = self.player.stats.get(effect['stat'], 0) + effect['bonus']
            self.player.wearables.append({'item': item_name, 'stat': effect['stat'], 'bonus': effect['bonus']})
            cursed_desc = effect.get('desc', '+' + str(effect['bonus']) + ' ' + effect['stat'])
            print(f"*** Cursed item equipped: {item_name}! {cursed_desc}")
        else:
            self.player.stats[effect['stat']] = self.player.stats.get(effect['stat'], 0) + effect['bonus']
            self.player.wearables.append({'item': item_name, 'stat': effect['stat'], 'bonus': effect['bonus']})
            print(f"*** Equipped {item_name}! +{effect['bonus']} {effect['stat']}")
    
    def discard_item(self, item_name: str):
        """Discard item"""
        if not item_name:
            print("Discard what?")
            return
        
        for item in self.player.special_items:
            if item.lower() == item_name.lower() or item_name.lower() in item.lower():
                if self.player.discard_special_item(item):
                    print(f"Discarded: {item} (can find a new one on next floor)")
                    return
        
        for item in self.player.inventory:
            if item.lower() == item_name.lower() or item_name.lower() in item.lower():
                if item.startswith("WEAPON:"):
                    weapon_name = item[8:]
                    for i, w in enumerate(self.player.inventory_weapons):
                        if w['name'] == weapon_name:
                            self.player.inventory_weapons.pop(i)
                            break
                self.player.inventory.remove(item)
                print(f"Discarded: {item}")
                return
        print(f"Don't have '{item_name}'")
    def use_special_item(self, item_name: str):
        """Use a special/quest item. Dispatches to a focused handler per item."""
        if not item_name:
            print("Use what?")
            return

        # Old map — lives in special_items, not inventory
        if item_name == 'old map':
            if item_name in self.player.special_items:
                print("You study the old map...")
                self.show_map()
            else:
                print("You don't have an old map.")
            return

        # d20 — also lives in special_items
        if item_name in ("gambler's d20", "d20"):
            if "gambler's d20" not in self.player.special_items:
                print("You don't have a Gambler's d20.")
            else:
                self._use_d20()
            return

        if item_name not in self.player.inventory:
            print(f"Don't have '{item_name}'")
            return

        if item_name not in GameConstants.ACTIONABLE_ITEMS:
            print(f"Can't use '{item_name}' like that")
            return

        handler = {
            'torch':             self._use_torch,
            'rusty key':         self._use_rusty_key,
            'bone key':          self._use_bone_key,
            'demon seal':        self._use_demon_seal,
            'crystal shard':     self._use_crystal_shard,
            'void essence':      self._use_void_essence,
            'primordial rune':   self._use_primordial_rune,
            'ancient medallion': self._use_ancient_medallion,
            'journal_1':         lambda: self._read_journal('journal_1'),
            'journal_2':         lambda: self._read_journal('journal_2'),
            'journal_3':         lambda: self._read_journal('journal_3'),
            'journal_4':         lambda: self._read_journal('journal_4'),
            'journal_5':         lambda: self._read_journal('journal_5'),
        }.get(item_name)

        if handler:
            handler()
        else:
            print(f"Can't use '{item_name}' here.")

    # ── Special item handlers ─────────────────────────────────────

    def _use_d20(self):
        """Gambler's d20 — instant-kill chance in any fight."""
        room = self.get_current_room()
        if not room.enemies:
            print("No enemies here to use the d20 on.")
            return
        roll = random.randint(1, 20)
        print(f"\n  ⚄ You roll the Gambler's d20... {roll}!")
        if roll == 20:
            print("  ★ NATURAL 20! Cosmic annihilation!")
            for enemy in list(room.enemies):
                ng_e = getattr(self.player, 'ng_plus', 0)
                if ng_e > 0:
                    wk = getattr(self.player, 'ng_world', 'fractured_labyrinth')
                    ep = GameConstants.NG_PLUS_WORLDS.get(wk, {}).get('enemies', GameConstants.NG_PLUS_ENEMIES)
                else:
                    ep = GameConstants.ENEMIES
                self.player.gain_experience(ep.get(enemy.lower(), {'exp': 50}).get('exp', 50))
                room.enemies.clear()
            print("  ★ All enemies annihilated! (The d20 shatters.)")
            self.player.special_items.remove("gambler's d20")
        elif roll == 1:
            print("  ✗ Critical failure. The d20 bounces away. Gone forever.")
            self.player.special_items.remove("gambler's d20")
        else:
            print("  Not a 20. The d20 stays in your pocket.")

    def _use_torch(self):
        """Torch — unlocks Hidden Alcove secret rooms."""
        room = self.get_current_room()
        if 'Hidden Alcove' in room.name and not self.player.secret_room_unlocked:
            print("\n*** You place the torch in the wall sconce...")
            print("A hidden door slides open!")
            self.player.secret_room_unlocked = True
            self.player.inventory.remove('torch')
            # Add passage to the secret room
            for r_id, r in self.floors[self.player.current_floor].items():
                if 'Secret' in r.name and r_id not in room.exits.values():
                    room.exits['secret'] = r_id
                    print(f"  A hidden passage leads to: {r.name}")
                    break
        else:
            if 'torch' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('torch')
                print("You hold up the torch. Nothing happens here.")
                print("  ★ HINT: Find the Hidden Alcove — it has a torch sconce on the wall.")
                print("         The sconce looks like it could hold something. Use the torch there.")
            else:
                print("The torch flickers. You need a Hidden Alcove with a wall sconce.")

    def _use_rusty_key(self):
        """Rusty key — opens the Locked Vault."""
        room = self.get_current_room()
        if room.name == 'Locked Vault':
            if getattr(room, '_activated', False):
                print("The vault has already been opened. Nothing remains.")
                return
            print("\n*** You insert the rusty key into the ancient lock...")
            print("The vault opens! Inside: piles of treasure!")
            self.player.inventory.remove('rusty key')
            gold = random.randint(50, 150)
            self.player.gold_coins += gold
            self.player.total_gold_earned += gold
            room.items.extend(['ultimate health potion', 'power ring', 'experience gem'])
            room._activated = True
            print(f"  +{gold} gold coins!")
            print("  Found: ultimate health potion, power ring, experience gem")
        else:
            if room.name == 'Locked Vault':
                print("The vault has already been opened.")
                return
            if 'rusty key' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('rusty key')
                print("You examine the key. It looks like it would fit a large lock...")
                print("  ★ HINT: Find the Locked Vault — a sealed room with an ornate chest")
                print("         and an old rusty keyhole. Use the key there to claim the treasure.")
            else:
                print("The rusty key is waiting for the Locked Vault.")

    def _use_bone_key(self):
        """Bone key — opens the Bone Crypt."""
        room = self.get_current_room()
        if room.name == 'Bone Crypt' and not getattr(room, '_activated', False):
            print("\n*** The bone key rattles as you insert it into the bone door...")
            print("Ancient remains and forbidden knowledge lie within!")
            self.player.inventory.remove('bone key')
            room.items.extend(['wisdom gem', 'shadow cloak', 'ancient medallion'])
            room._activated = True
            self.player.gain_experience(200)
            print("  Found: wisdom gem, shadow cloak, ancient medallion")
            print("  +200 XP from the forbidden knowledge!")
        else:
            if room.name == 'Bone Crypt':
                print("The crypt has already been opened. Nothing more remains here.")
                return
            if 'bone key' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('bone key')
                print("The bone key rattles ominously. This is meant for a bone door...")
                print("  ★ HINT: Find the Bone Crypt — a chamber where ancient bones line the walls")
                print("         and a sealed bone door blocks the way deeper. The key fits that lock.")
            else:
                print("The bone key rattles. It belongs in the Bone Crypt.")

    def _use_demon_seal(self):
        """Demon seal — banishes demons or opens Demon Gates."""
        room = self.get_current_room()
        demons = [e for e in room.enemies if 'demon' in e.lower() or 'devil' in e.lower()]
        if room.name == 'Demon Gate':
            if getattr(room, '_activated', False):
                print("The gate has already been shattered. Nothing remains to unseal.")
                return
            print("\n*** You press the demon seal against the arcane chains...")
            print("The gate shatters! A reward lies beyond!")
            self.player.inventory.remove('demon seal')
            room.items.extend(['power ring', 'ultimate health potion'])
            room._activated = True
            print("  Found: power ring, ultimate health potion")
        elif demons:
            print(f"\n*** You brandish the demon seal! The demons recoil!")
            for d in demons:
                room.enemies.remove(d)
                ng_e = getattr(self.player, 'ng_plus', 0)
                ep = (GameConstants.NG_PLUS_WORLDS.get(
                    getattr(self.player, 'ng_world', 'fractured_labyrinth'), {})
                    .get('enemies', GameConstants.NG_PLUS_ENEMIES) if ng_e > 0
                    else GameConstants.ENEMIES)
                exp = ep.get(d.lower(), {'exp': 85}).get('exp', 85)
                print(f"  The {d} is banished! +{exp} exp")
                self.player.gain_experience(exp)
            self.player.inventory.remove('demon seal')
        else:
            if 'demon seal' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('demon seal')
                print("The demon seal pulses with dark energy. It's meant for demons...")
                print("  ★ HINT: Use it in a Demon Gate room (sealed by arcane chains)")
                print("         or carry it into any room with demon enemies to banish them instantly.")
            else:
                print("The seal pulses. Take it to a Demon Gate or use it against demon enemies.")

    def _use_crystal_shard(self):
        """Crystal shard — activates Crystal Chamber mechanism."""
        room = self.get_current_room()
        if room.name == 'Crystal Chamber' and not getattr(room, '_activated', False):
            print("\n*** You insert the crystal shard into the mechanism...")
            print("The crystals resonate! Energy surges through you!")
            self.player.inventory.remove('crystal shard')
            for stat in ['strength', 'intelligence', 'agility']:
                self.player.stats[stat] = self.player.stats.get(stat, 0) + 3
            self.player.max_health += 20
            self.player.health = min(self.player.health + 20, self.player.max_health)
            room._activated = True
            print("  +3 STR, +3 INT, +3 AGI, +20 Max HP!")
        elif room.name == 'Crystal Chamber':
            print("The mechanism has already been activated. Its power is spent.")
        else:
            if 'crystal shard' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('crystal shard')
                print("The crystal shard glows softly. It needs a crystal mechanism...")
                print("  ★ HINT: Find the Crystal Chamber — every surface covered in crystalline")
                print("         formations with a dormant mechanism at the centre. Insert the shard there.")
            else:
                print("The shard glows. Bring it to the Crystal Chamber.")

    def _use_void_essence(self):
        """Void essence — seals the Void Tear."""
        room = self.get_current_room()
        if room.name == 'Void Tear' and not getattr(room, '_activated', False):
            print("\n*** You channel the void essence into the tear...")
            print("The void tears seals shut! Reality stabilises!")
            self.player.inventory.remove('void essence')
            self.player.stats['intelligence'] = self.player.stats.get('intelligence', 0) + 5
            self.player.stats['luck']          = self.player.stats.get('luck', 0) + 3
            self.player.gain_experience(300)
            room._activated = True
            print("  +5 INT, +3 LCK, +300 XP!")
        elif room.name == 'Void Tear':
            print("The tear has already been sealed. Reality holds firm here.")
        else:
            if 'void essence' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('void essence')
                print("The void essence writhes with otherworldly power. It needs a void tear...")
                print("  ★ HINT: Find the Void Tear — a room where reality fractures, with a")
                print("         swirling unstable portal. Channel the essence into it to stabilise it.")
            else:
                print("The essence writhes. It belongs in the Void Tear room.")

    def _use_primordial_rune(self):
        """Primordial rune — charges the Primordial Monument."""
        room = self.get_current_room()
        if room.name == 'Primordial Monument' and not getattr(room, '_activated', False):
            print("\n*** You place the primordial rune on the monument...")
            print("Ancient power flows into you!")
            self.player.inventory.remove('primordial rune')
            for stat in self.player.stats:
                self.player.stats[stat] = self.player.stats.get(stat, 0) + 2
            self.player.max_health += 30
            self.player.health = min(self.player.health + 30, self.player.max_health)
            room._activated = True
            print("  +2 to ALL stats, +30 Max HP!")
        elif room.name == 'Primordial Monument':
            print("The monument's power has already been channelled. It stands silent.")
        else:
            if 'primordial rune' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('primordial rune')
                print("The primordial rune hums with ancient power. It belongs on a monument...")
                print("  ★ HINT: Find the Primordial Monument — an ancient stone covered in glowing")
                print("         runic inscriptions. Place the rune there to unlock its full power.")
            else:
                print("The rune hums. Place it on the Primordial Monument.")

    def _read_journal(self, journal_key: str):
        """Read a discoverable journal entry."""
        entry = GameConstants.JOURNAL_ENTRIES.get(journal_key)
        if entry:
            print("\n" + "─"*52)
            print(entry)
            print("─"*52)
            print("  (The journal is worn but readable. You keep it.)")
        else:
            print("The journal is too damaged to read.")

    def _use_ancient_medallion(self):
        """Ancient medallion — activates the Sacred Shrine."""
        room = self.get_current_room()
        if room.name == 'Sacred Shrine' and not getattr(room, '_activated', False):
            print("\n*** You place the medallion on the altar...")
            print("The shrine awakens! Ancient blessings wash over you!")
            self.player.inventory.remove('ancient medallion')
            self.player.max_health += 50
            self.player.health = min(self.player.health + 50, self.player.max_health)
            self.player.stats['strength']     = self.player.stats.get('strength', 0) + 4
            self.player.stats['vitality']     = self.player.stats.get('vitality', 0) + 4
            self.player.rarity_boost         += 15
            room._activated = True
            print("  +50 Max HP, +4 STR, +4 VIT, +15% weapon rarity boost!")
        elif room.name == 'Sacred Shrine':
            print("The shrine has already bestowed its blessing. The altar is still.")
        else:
            if 'ancient medallion' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('ancient medallion')
                print("You hold the medallion. It should be placed on an altar...")
                print("  ★ HINT: Find the Sacred Shrine — an ancient room with a stone altar")
                print("         that has a circular indentation. Place the medallion there.")
            else:
                print("The medallion waits for the Sacred Shrine.")
    def open_shop(self):
        """Open shop"""
        if self.player.current_floor > 1 and 'start' not in self.player.current_room:
            print("! No shop here. Visit the floor's starting room to find a merchant.")
            return
        
        if self.player.current_floor == 1 and self.player.current_room != 'start':
            print("! No shop here. Return to the entrance hall to find a merchant.")
            return
        
        rec = RecordsManager.load()
        # One-time acknowledgment the first shop visit after clearing the game
        if rec.get('runs_completed', 0) > 0 and not rec.get('adamus_impressed', False):
            RecordsManager.update(adamus_impressed=True)
            print("\n" + "="*50)
            print("  ☠  ADAMUS THE LOYAL — Purveyor of Fine Goods  ☠")
            print("="*50)
            print(f"  '{self.player.name}.'")
            print(f"  Adamus pauses. Sets down whatever he was doing.")
            print(f"  He doesn't look at you.")
            print(f"  'You actually did it. I didn't think you had it in you.'")
            print(f"  A long pause.")
            print(f"  \"Don't make me say that again. Now. What do you need.\"")
            print("-"*50)
            print(f"  Your Gold: {self.player.gold_coins}")
        else:
            ADAMUS_GREETINGS = [
                f"Well well well, look what the cat dragged in. What do ya want, {self.player.name}?",
                f"Ah, {self.player.name}. My least favourite customer. What'll it be?",
                f"Back again, you absolute bottom-feeder? Adamus is open for business.",
                f"Ohhh great. You. What is it this time, dipsh*t?",
                f"You smell like dungeon floor and disappointment. Welcome to my shop.",
                f"Holy hell, you're still alive? Remarkable. What do you need?",
            ]
            ADAMUS_QUIPS = [
                "Why did the skeleton go to the bar alone? Because he had no body to go with him. Unlike you, who has no body BECAUSE nobody likes you.",
                "A priest, a rogue, and a warrior walk into a bar. The bartender looks up and says 'what is this, some kind of joke?' Yes. It's you. You're the joke.",
                "You know what's the difference between you and a bucket of manure? The bucket.",
                "My therapist told me I project my insecurities onto others. I told him that's a very stupid thing for a moron like him to say.",
                "A man walks into a library and asks for books about paranoia. The librarian whispers 'they're right behind you.' Anyway, something IS behind you.",
                "Why don't scientists trust atoms? Because they make up everything. Like the stories you tell yourself about being a hero.",
                "I asked my dog what two minus two is. He said nothing. He's smarter than you.",
                "You're like a software update — every time I see you, I think 'not now.'",
                "My doctor told me I needed to watch my drinking. I'm watching it right now. What's your excuse for everything else?",
                "What do you and a broken pencil have in common? Absolutely pointless.",
                "You're not stupid. You just have bad luck thinking.",
                "I'd roast you but my mother told me not to burn garbage.",
                "You must have been born on a highway — that's where most accidents happen.",
                "I've met some real pieces of work in this dungeon. You're the whole furniture set.",
                "If I wanted to hear from an ass, I'd fart. And yet here you are.",
            ]

            greeting = random.choice(ADAMUS_GREETINGS)
            quip     = random.choice(ADAMUS_QUIPS)
            print("\n" + "="*50)
            print("  ☠  ADAMUS THE LOYAL — Purveyor of Fine Goods  ☠")
            print("="*50)
            print(f"  '{greeting}'")
            print(f"  '{quip}'")
            print("-"*50)
            print(f"  Your Gold: {self.player.gold_coins}")
        
        # Pick the right tier for this floor
        floor = self.player.current_floor
        tier_stock = {}
        for (lo, hi), stock in GameConstants.SHOP_TIERS.items():
            if lo <= floor <= hi:
                tier_stock = stock
                break
        if not tier_stock:
            tier_stock = {k: (v, '', None) for k, v in GameConstants.SHOP_ITEMS.items()}

        # Filter class-restricted items
        items = [
            (name, price, desc)
            for name, (price, desc, cls_filter) in tier_stock.items()
            if cls_filter is None or cls_filter == self.player.character_class
        ]

        tier_labels = {(1,2):'Floors 1-2', (3,4):'Floors 3-4', (5,6):'Floors 5-6',
                       (7,8):'Floors 7-8', (9,10):'Floors 9-10'}
        tier_name = next((v for (lo,hi),v in tier_labels.items() if lo<=floor<=hi), f'Floor {floor}')



        def _weapon_sell_value(w) -> int:
            """Calculate sell value based on damage and rarity."""
            RARITY_SELL_MULT = {
                'common': 0.30, 'uncommon': 0.38, 'rare': 0.48,
                'epic': 0.60, 'legendary': 0.80, 'mythic': 1.00,
            }
            base   = w.get('damage', 10)
            mult   = RARITY_SELL_MULT.get(w.get('rarity', 'common'), 0.30)
            traits = len(w.get('traits', []))
            value  = int(base * mult) + (traits * 3)
            return max(5, value)

        ADAMUS_SALES = [
            f"Fine. Here's your {{item}}. Don't come crying to me when it doesn't save you.",
            f"There. {{item}}. Pleasure doing business — emphasis on 'business', none on 'pleasure'.",
            f"{{item}}, gone. Your gold, gone. My patience, also gone.",
            f"Enjoy your {{item}}. It's better than you deserve.",
            f"Here. {{item}}. Try not to die before you get any use out of it.",
        ]

        ADAMUS_BUYS = [
            "Fine. I'll take it. Don't expect me to be grateful.",
            "Done. Here's your gold. I've seen better but I won't say when.",
            "Sold. I'll give it a good home. Better than you were giving it.",
            "Transaction complete. Try not to spend it on something stupid.",
            "There. Gold for the weapon. We're even. Don't get sentimental.",
        ]

        ADAMUS_LEGENDARY_CHECKS = [
            f"...Hold on. Let me actually look at this.",
            f"You understand what you're holding, right?",
            f"I've only seen two of these in twenty years of trading.",
        ]

        ADAMUS_MYTHIC_CHECKS = [
            f"Put that away. I'm not buying that. I'm not even — where did you GET this.",
            f"No. Absolutely not. I don't deal in things that could level a city block.",
            f"A mythic. In MY shop. Do you have ANY idea what this is worth.",
        ]

        while True:
            # Filter shop stock: remove wearables the player is already capped on
            lvl = self.player.level
            max_stack = 1 if lvl < 5 else 2 if lvl < 10 else 3 if lvl < 15 else 4
            def _shop_at_cap(item_name):
                if item_name not in GameConstants.WEARABLE_ITEMS:
                    return False
                if GameConstants.WEARABLE_ITEMS[item_name].get('cursed'):
                    return False
                count = sum(1 for w in self.player.wearables if w['item'] == item_name)
                return count >= max_stack
            cur_items = [(name, price, desc) for name, price, desc in items
                         if not _shop_at_cap(name)]


            print(f"\n  Stock: {tier_name}  |  {len(cur_items)} items available")
            for i, (name, price, desc) in enumerate(cur_items, 1):
                can_afford = "  " if self.player.gold_coins >= price else "✗ "
            print("-"*50)
            sell_opts = []
            if self.player.inventory_weapons:
                print(f"\n  Weapons you can sell:")
                for j, w in enumerate(self.player.inventory_weapons):
                    val = _weapon_sell_value(w)
                    rar = w.get('rarity', 'common').upper()
                    print(f"  S{j+1}. {w['name']:<28} {w.get('damage',0):>3}dmg  {rar:<10}  → {val}g")
                    sell_opts.append(w)
                print()
            print(f"  {len(items)+1}. Leave")
            print(f"  Your Gold: {self.player.gold_coins}g")
            print("-"*50)

            try:
                raw = input("\n  Choice (buy # or S# to sell): ").strip()
            except KeyboardInterrupt:
                print("  Adamus waves you off.")
                return

            if not raw:
                continue

            # ── Leave ───────────────────────────────────────────
            if raw in (str(len(items)+1), 'leave', 'exit', 'q'):
                print("  Adamus doesn't say goodbye. He never does.")
                return

            # ── Sell ────────────────────────────────────────────
            if raw.lower().startswith('s') and len(raw) > 1:
                try:
                    sidx = int(raw[1:]) - 1
                    if not (0 <= sidx < len(sell_opts)):
                        print("  Invalid sell choice.")
                        continue
                    w = sell_opts[sidx]
                    val = _weapon_sell_value(w)
                    rarity = w.get('rarity', 'common')
                    wname  = w.get('name', 'Unknown')

                    # Adamus reacts to rarity before confirming
                    if rarity == 'mythic':
                        print(f"\n  Adamus looks at {wname}.")
                        print(f"  '{random.choice(ADAMUS_MYTHIC_CHECKS)}'")
                        print(f"  'I'll give you {val}g. But I'm doing you a disservice.'")
                        print(f"  'Are you absolutely certain you want to sell this?'")
                        try:
                            confirm = input("  Sell mythic weapon? (yes/no): ").strip().lower()
                        except KeyboardInterrupt:
                            confirm = 'no'
                        if confirm not in ('yes', 'y'):
                            print("  Adamus nods. 'Wise.'")
                            continue

                    elif rarity == 'legendary':
                        print(f"\n  Adamus picks up {wname} and turns it over slowly.")
                        print(f"  '{random.choice(ADAMUS_LEGENDARY_CHECKS)}'")
                        print(f"  'I can do {val}g. You sure about this?'")
                        try:
                            confirm = input("  Sell legendary weapon? (yes/no): ").strip().lower()
                        except KeyboardInterrupt:
                            confirm = 'no'
                        if confirm not in ('yes', 'y'):
                            print("  Adamus sets it back down. 'Thought so.'")
                            continue

                    # Complete the sale
                    self.player.inventory_weapons.remove(w)
                    label = f"WEAPON: {{w['name']}}"
                    if label in self.player.inventory:
                        self.player.inventory.remove(label)
                    self.player.gold_coins += val
                    self.player.total_gold_earned += val
                    print(f"  '{random.choice(ADAMUS_BUYS)}'")
                    print(f"  Sold {wname} for {val}g  |  Gold: {{self.player.gold_coins}}g")
                    sell_opts = list(self.player.inventory_weapons)
                    continue
                except (ValueError, IndexError):
                    print("  Invalid sell choice.")
                    continue

            # ── Buy ─────────────────────────────────────────────
            try:
                choice = int(raw)
            except ValueError:
                print("  Adamus stares at you. 'That's not a number.'")
                continue

            if not (1 <= choice <= len(items)):
                print("  Invalid choice.")
                continue

            item, price, desc = items[choice - 1]
            if self.player.gold_coins < price:
                print(f"  'Not enough gold. Need {{price}}g, you have {{self.player.gold_coins}}g.'")
                continue

            if not self.player.can_add_item() and item not in GameConstants.WEARABLE_ITEMS:
                print("  Inventory full!")
                continue

            self.player.gold_coins -= price
            if item == 'weapon cache':
                new_weapon = WeaponSystem.generate_weapon(self.player)
                comparison = WeaponSystem.compare_weapons(new_weapon, self.player)
                print(comparison)
                try:
                    if input("  Equip? (y/n): ").strip().lower() in ('y', 'yes'):
                        if self.player.weapon:
                            self.player.inventory_weapons.append(self.player.weapon)
                        self.player.equip_weapon(new_weapon)
                    else:
                        self.player.inventory_weapons.append(new_weapon)
                except KeyboardInterrupt:
                    self.player.inventory_weapons.append(new_weapon)
            elif item in GameConstants.WEARABLE_ITEMS:
                self.player.inventory.append(item)
            else:
                self.player.add_item(item)

            sale_line = random.choice(ADAMUS_SALES).format(item=item)
            print(f"  '{sale_line}'")
            print(f"  Gold remaining: {{self.player.gold_coins}}g")
    
    def show_map(self):
        """Display visual dungeon map"""
        visual_map = MapGenerator.generate_visual_map(
            self.floors,
            self.player.current_floor,
            self.player.current_room,
            self.player.visited_rooms
        )
        print(visual_map)
    
    def save_game(self):
        """Save game state to selected slot"""
        try:
            # Create saves directory if it doesn't exist
            if not os.path.exists(GameConstants.SAVE_DIRECTORY):
                os.makedirs(GameConstants.SAVE_DIRECTORY)
            
            # Show available save slots
            print("\n" + "="*40)
            print("SAVE GAME")
            print("="*40)
            
            # List existing saves
            for slot in range(1, GameConstants.MAX_SAVE_SLOTS + 1):
                save_path = os.path.join(GameConstants.SAVE_DIRECTORY, f"save{slot}.json")
                if os.path.exists(save_path):
                    try:
                        with open(save_path, 'r') as f:
                            save_data = json.load(f)
                            player_data = save_data.get('player', {})
                            name = player_data.get('name', 'Unknown')
                            level = player_data.get('level', 1)
                            floor = player_data.get('current_floor', 1)
                            print(f"{slot}. {name} - Lvl {level} - Floor {floor}")
                    except (json.JSONDecodeError, OSError, KeyError, TypeError):
                        print(f"{slot}. [Corrupted Save]")
                else:
                    print(f"{slot}. [Empty Slot]")
            
            print(f"{GameConstants.MAX_SAVE_SLOTS + 1}. Cancel")
            
            try:
                choice = int(input(f"\nChoose slot (1-{GameConstants.MAX_SAVE_SLOTS}): ").strip())
                if choice == GameConstants.MAX_SAVE_SLOTS + 1:
                    print("Cancelled.")
                    return
                if choice < 1 or choice > GameConstants.MAX_SAVE_SLOTS:
                    print("Invalid slot!")
                    return
            except (ValueError, KeyboardInterrupt):
                print("Cancelled.")
                return
            
            save_path = os.path.join(GameConstants.SAVE_DIRECTORY, f"save{choice}.json")
            
            # Confirm overwrite if slot exists
            if os.path.exists(save_path):
                try:
                    confirm = input(f"Overwrite slot {choice}? (y/n): ").strip().lower()
                    if confirm not in ['y', 'yes']:
                        print("Cancelled.")
                        return
                except KeyboardInterrupt:
                    print("Cancelled.")
                    return
            
            save_data = {
                'version': GameConstants.VERSION,
                'player': self.player.to_dict(),
                'floors': {}
            }
            
            for floor_num, floor_rooms in self.floors.items():
                save_data['floors'][str(floor_num)] = {
                    room_id: {
                        'name':        room.name,
                        'description': room.description,
                        'atmosphere':  room.atmosphere,
                        'items':       room.items,
                        'enemies':     room.enemies,
                        'visited':     room.visited,
                        'exits':       room.exits,
                        '_activated':  getattr(room, '_activated', False),
                    } for room_id, room in floor_rooms.items()
                }
            
            with open(save_path, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            logger.info(f"Game saved to slot {choice}: {self.player.name} (Lvl {self.player.level}, Floor {self.player.current_floor})")
            print(f"✓ Game saved to slot {choice}!")
        except (OSError, json.JSONEncodeError, TypeError) as e:
            logging.error(f"Save error: {e}", exc_info=True)
            print(f"✗ Save failed: {e}")
    
    def load_game(self) -> bool:
        """Load game state from selected slot"""
        try:
            # Create saves directory if it doesn't exist
            if not os.path.exists(GameConstants.SAVE_DIRECTORY):
                os.makedirs(GameConstants.SAVE_DIRECTORY)
                return False
            
            # Show available save slots
            print("\n" + "="*40)
            print("LOAD GAME")
            print("="*40)
            
            available_saves = []
            for slot in range(1, GameConstants.MAX_SAVE_SLOTS + 1):
                save_path = os.path.join(GameConstants.SAVE_DIRECTORY, f"save{slot}.json")
                if os.path.exists(save_path):
                    try:
                        with open(save_path, 'r') as f:
                            save_data = json.load(f)
                            player_data = save_data.get('player', {})
                            name = player_data.get('name', 'Unknown')
                            level = player_data.get('level', 1)
                            char_class = player_data.get('character_class', 'warrior')
                            floor = player_data.get('current_floor', 1)
                            print(f"{slot}. {name} - {char_class.title()} Lvl {level} - Floor {floor}")
                            available_saves.append(slot)
                    except (json.JSONDecodeError, OSError, KeyError, TypeError):
                        print(f"{slot}. [Corrupted Save]")
                else:
                    print(f"{slot}. [Empty Slot]")
            
            if not available_saves:
                print("\nNo save files found!")
                return False
            
            print(f"{GameConstants.MAX_SAVE_SLOTS + 1}. Cancel")
            
            try:
                choice = int(input(f"\nChoose slot (1-{GameConstants.MAX_SAVE_SLOTS}): ").strip())
                if choice == GameConstants.MAX_SAVE_SLOTS + 1:
                    return False
                if choice not in available_saves:
                    print("Invalid or empty slot!")
                    return False
            except (ValueError, KeyboardInterrupt):
                return False
            
            save_path = os.path.join(GameConstants.SAVE_DIRECTORY, f"save{choice}.json")
            
            with open(save_path, 'r') as f:
                save_data = json.load(f)
            
            if save_data.get('version') != GameConstants.VERSION:
                logger.warning(f"Save version mismatch: {save_data.get('version')} vs {GameConstants.VERSION}")
                print("! Save version mismatch - may have issues")
            
            self.player = Player.from_dict(save_data['player'])

            if self.player.weapon and self.player.weapon.get('special') == 'instant_kill':
                if self.player.weapon.get('uses_remaining', 0) <= 0:
                    logger.info("Golden Gun depleted on load")
                    print("! Your Golden Gun has depleted...")
                    self.player.weapon = None

            # Determine if this is an NG+ save so room names load correctly
            ng         = getattr(self.player, 'ng_plus', 0)
            ng_world   = getattr(self.player, 'ng_world', 'fractured_labyrinth')
            is_ng_plus = ng > 0

            self.floors = {}
            for floor_str, floor_data in save_data['floors'].items():
                floor_num = int(floor_str)
                self.floors[floor_num] = {}

                for room_id, room_data in floor_data.items():
                    # Use saved name/description/atmosphere if present (saves after this fix)
                    # Fall back to reconstruction for older saves that lack these fields
                    if 'name' in room_data:
                        name = room_data['name']
                        desc = room_data['description']
                        atmo = room_data['atmosphere']
                    else:
                        # Legacy save fallback — reconstruct from room_id heuristics
                        if room_id in ('start',) or room_id.endswith('_start'):
                            name = "Entrance Hall" if room_id == 'start' else f"Floor {floor_num} Entrance"
                            desc = "The dungeon entrance."
                            atmo = "Adamus the Loyal has set up shop here. Use 'shop' to trade."
                        elif 'boss' in room_id:
                            tmpl = BossConfig.get_boss_room_template(floor_num)
                            name, desc, atmo = tmpl.name, tmpl.description, tmpl.atmosphere
                        elif 'stairs' in room_id:
                            name, desc, atmo = "Ancient Stairway", "Stone stairs descend deeper.", ""
                        elif 'secret' in room_id:
                            name, desc, atmo = "Secret Treasure Vault", "A hidden vault glitters with treasures!", ""
                        else:
                            templates = RoomTemplateConfig.get_templates_for_floor(floor_num)
                            tmpl = random.choice(templates) if templates else None
                            name = tmpl.name if tmpl else "Mysterious Room"
                            desc = tmpl.description if tmpl else "A dark room."
                            atmo = tmpl.atmosphere if tmpl else ""

                    room = Room(name, desc, floor_num,
                                room_data['items'], room_data['exits'],
                                room_data['enemies'], atmo)
                    room.visited = room_data['visited']
                    if room_data.get('_activated'):
                        room._activated = True
                    self.floors[floor_num][room_id] = room
            
            logger.info(f"Game loaded from slot {choice}: {self.player.name} (Lvl {self.player.level}, Floor {self.player.current_floor})")
            print(f"✓ Welcome back, {self.player.name} the {self.player.get_class_title()}!")

            # If all 10 bosses already defeated (save predates victory screen),
            # offer the victory/NG+ screen right away.
            if len(self.player.bosses_defeated) >= GameConstants.NUM_FLOORS:
                print("\n★ All bosses defeated detected — loading victory screen...")
                try:
                    input("  [ Press Enter to continue ]")
                except KeyboardInterrupt:
                    pass
                self.combat = CombatSystem(self)
                self._victory_screen()
                # After the victory screen / NG+ run completes, go back to
                # the main menu rather than letting start_game fall through
                # to look_around() and _game_loop() again.
                self.player = None
                self.floors = None
                return False

            return True
            
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as e:
            logging.error(f"Load error: {e}", exc_info=True)
            print(f"✗ Load failed: {e}")
            return False
    
    def delete_save(self):
        """Delete a save file"""
        try:
            if not os.path.exists(GameConstants.SAVE_DIRECTORY):
                print("No save files found!")
                return
            
            print("\n" + "="*40)
            print("DELETE SAVE")
            print("="*40)
            
            available_saves = []
            for slot in range(1, GameConstants.MAX_SAVE_SLOTS + 1):
                save_path = os.path.join(GameConstants.SAVE_DIRECTORY, f"save{slot}.json")
                if os.path.exists(save_path):
                    try:
                        with open(save_path, 'r') as f:
                            save_data = json.load(f)
                            player_data = save_data.get('player', {})
                            name = player_data.get('name', 'Unknown')
                            level = player_data.get('level', 1)
                            floor = player_data.get('current_floor', 1)
                            print(f"{slot}. {name} - Lvl {level} - Floor {floor}")
                            available_saves.append(slot)
                    except (json.JSONDecodeError, OSError, KeyError, TypeError):
                        print(f"{slot}. [Corrupted Save]")
                        available_saves.append(slot)
                else:
                    print(f"{slot}. [Empty Slot]")
            
            if not available_saves:
                print("\nNo save files to delete!")
                return
            
            print(f"{GameConstants.MAX_SAVE_SLOTS + 1}. Cancel")
            
            try:
                choice = int(input(f"\nDelete slot (1-{GameConstants.MAX_SAVE_SLOTS}): ").strip())
                if choice == GameConstants.MAX_SAVE_SLOTS + 1:
                    return
                if choice not in available_saves:
                    print("Invalid or empty slot!")
                    return
            except (ValueError, KeyboardInterrupt):
                return
            
            save_path = os.path.join(GameConstants.SAVE_DIRECTORY, f"save{choice}.json")
            
            confirm = input(f"Delete slot {choice}? This cannot be undone! (y/n): ").strip().lower()
            if confirm in ['y', 'yes']:
                os.remove(save_path)
                print(f"✓ Slot {choice} deleted!")
                logger.info(f"Save file deleted: slot {choice}")
            else:
                print("Cancelled.")
        except OSError as e:
            logging.error(f"Delete save error: {e}", exc_info=True)
            print(f"✗ Delete failed: {e}")
    

    # ─────────────────────────────────────────────────────────────

    def _generate_ng_plus_dungeon(self, ng: int):
        """Generate the selected NG+ world dungeon."""
        weapon_scale  = max(1.0, getattr(self.player, 'ng_weapon_scale', 1.0))
        world_key     = getattr(self.player, 'ng_world', 'fractured_labyrinth')
        world_data    = GameConstants.NG_PLUS_WORLDS.get(world_key,
                        GameConstants.NG_PLUS_WORLDS['fractured_labyrinth'])
        world_name    = world_data['display_name']
        JOURNAL_FLOORS = {2: 'journal_1', 4: 'journal_2', 5: 'journal_3',
                          7: 'journal_4', 9: 'journal_5'}

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

            # Inject journal entry if this floor has one
            journal_key = JOURNAL_FLOORS.get(floor_num)
            if journal_key and journal_key not in self.player.unique_items_spawned:
                # Place in a non-boss, non-start room
                candidates = [r for r_id, r in rooms.items()
                              if 'boss' not in r_id and r_id != start_id]
                if candidates:
                    target_room = random.choice(candidates)
                    target_room.items.append(journal_key)
                    self.player.unique_items_spawned.add(journal_key)

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


    def _audit_ng_weapons(self) -> None:
        """Check for overpowered weapons before NG+ and let the player decide.

        The fixed boss-weapon generator caps stored damage at 220 (floor 10).
        Anything above 250 is legacy inflation from the old compounding system.
        Players can keep them (enemies/bosses scale up to match) or discard them
        (normal scaling preserved).
        """
        THRESHOLD = 250   # above the legitimate floor-10 cap of 220
        NORMAL_CEILING = 220   # used to compute the scale factor

        p = self.player

        # Collect every weapon the player has
        all_weapons = []
        if p.weapon:
            all_weapons.append(('equipped', p.weapon))
        for w in getattr(p, 'inventory_weapons', []):
            all_weapons.append(('stored', w))

        overpowered = [(loc, w) for loc, w in all_weapons if w.get('damage', 0) > THRESHOLD]

        if not overpowered:
            p.ng_weapon_scale = 1.0
            return  # nothing to warn about

        # ── Warning screen ────────────────────────────────────────
        print("\n" + "!"*60)
        print("  NG+ WEAPON WARNING")
        print("!"*60)
        print("  The following weapon(s) have damage values well above")
        print("  what the current system generates. They were likely")
        print("  created by an older version of the game.")
        print()
        for loc, w in overpowered:
            name   = w.get('name', w.get('base_name', 'Unknown'))
            dmg    = w.get('damage', 0)
            rarity = w.get('rarity', 'unknown').capitalize()
            print(f"  ✗  [{loc.upper()}] {name}  —  {dmg} damage  ({rarity})")
        print()

        # Show what scaling would look like for the strongest weapon
        max_dmg = max(w.get('damage', 0) for _, w in overpowered)
        scale   = round(max_dmg / NORMAL_CEILING, 2)
        print(f"  If you keep these weapons, all NG+ enemies and bosses")
        print(f"  will have their HP multiplied by x{scale:.2f} to compensate.")
        print(f"  This means bosses that would normally have 568 HP")
        print(f"  would instead have {int(568 * scale)} HP.")
        print()
        print("  OPTIONS:")
        print("  1. Keep all — enemies and bosses scale up to match")
        print("  2. Discard overpowered weapons — normal NG+ scaling")
        print("  3. Choose per weapon")
        print()

        try:
            choice = input("  Choice: ").strip()
        except KeyboardInterrupt:
            choice = '1'

        if choice == '2':
            # Remove all overpowered weapons
            discarded = []
            for loc, w in overpowered:
                name = w.get('name', w.get('base_name', 'Unknown'))
                if loc == 'equipped' and p.weapon and p.weapon.get('damage') == w.get('damage'):
                    p.weapon = None
                elif loc == 'stored':
                    try:
                        p.inventory_weapons.remove(w)
                    except ValueError:
                        pass
                discarded.append(name)
            if discarded:
                print(f"\n  Discarded: {', '.join(discarded)}")
                print("  Normal NG+ scaling will apply.")
            p.ng_weapon_scale = 1.0

        elif choice == '3':
            to_keep = []
            for loc, w in overpowered:
                name = w.get('name', w.get('base_name', 'Unknown'))
                dmg  = w.get('damage', 0)
                try:
                    keep = input(f"  Keep [{loc}] {name} ({dmg} dmg)? (yes/no): ").strip().lower()
                except KeyboardInterrupt:
                    keep = 'yes'
                if keep not in ('yes', 'y'):
                    if loc == 'equipped' and p.weapon and p.weapon.get('damage') == dmg:
                        p.weapon = None
                    elif loc == 'stored':
                        try:
                            p.inventory_weapons.remove(w)
                        except ValueError:
                            pass
                    print(f"  Discarded {name}.")
                else:
                    to_keep.append(w)

            # Re-check what's still overpowered after per-weapon choices
            remaining = [w for w in ([p.weapon] if p.weapon else []) + list(p.inventory_weapons)
                         if w and w.get('damage', 0) > THRESHOLD]
            if remaining:
                max_dmg = max(w.get('damage', 0) for w in remaining)
                p.ng_weapon_scale = round(max_dmg / NORMAL_CEILING, 2)
                print(f"\n  Kept overpowered weapons — scale factor: x{p.ng_weapon_scale:.2f}")
            else:
                p.ng_weapon_scale = 1.0
                print("  All overpowered weapons discarded — normal scaling.")

        else:
            # Keep all, apply scale factor
            p.ng_weapon_scale = scale
            print(f"\n  Keeping all weapons. NG+ scale factor: x{scale:.2f}")

        try:
            input("\n  [ Press Enter to continue ]")
        except KeyboardInterrupt:
            pass

    def _victory_screen(self):
        """Display the endgame victory screen and credits."""
        p = self.player
        bosses = len(p.bosses_defeated)
        turns  = getattr(p, 'total_turns', '?')

        # Update records on first call
        rec = RecordsManager.load()
        first_clear = rec['first_clear_name'] is None
        RecordsManager.update(
            runs_completed=1,
            void_walker_unlocked=True,
            first_clear_name=rec['first_clear_name'] or p.name,
            # Retroactively credit bosses and floor for this run
            # (in case mid-run tracking was missing from older code)
            total_bosses_defeated=len(p.bosses_defeated),
            best_floor_reached=GameConstants.NUM_FLOORS,
        )

        print("\n" + "█" * 70)
        print("█" + " " * 68 + "█")
        print("█" + "  ★  LABYRINTH CONQUERED  ★".center(68) + "█")
        print("█" + " " * 68 + "█")
        print("█" * 70)

        print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   {p.name} the {p.get_class_title():<20}                            ║
║                                                                      ║
║   You descended into the dark and came back with the light.         ║
║   Ten floors. Ten bosses. One survivor.                              ║
║                                                                      ║
║   The Reality Breaker is no more.                                    ║
║   The Labyrinth is silent.  For now.                                 ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║  FINAL STATS                                                         ║
║   Level        : {p.level:<4}                                            ║
║   Bosses felled: {bosses}/10                                             ║
║   Floor reached: {p.current_floor}/10                                     ║
║   Gold on hand : {p.gold_coins}g                                          ║
║   Gold earned  : {getattr(p, 'total_gold_earned', p.gold_coins)}g (total this run)                    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ═══  THANK YOU FOR PLAYING  ═══                                     ║
║                                                                      ║
║  To everyone who play-tested Labyrinth — thank you.                  ║
║  Your feedback, your bug reports, your cursing at goblins,           ║
║  and your completely unreasonable hoarding of power rings            ║
║  all made this game what it is.  You know who you are.               ║
║                                                                      ║
║  Special thanks to Adam — roommate, idea machine, brutally           ║
║  honest critic, and the real reason Adamus the Loyal exists.         ║
║  This one's for you, you absolute bottom-feeder.  ☠                  ║
║                                                                      ║
║  — DEKU                                                              ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝""")

        ng = getattr(p, 'ng_plus', 0)
        ng_label = f"New Game+ Cycle {ng + 1}" if ng > 0 else "New Game+"
        ng_desc  = "a completely different dungeon — harder, stranger, wrong" if ng == 0 else f"another cycle — each one harder than the last"
        print(f"\n  1. {ng_label}  ({ng_desc})")
        print("  2. Return to Main Menu")
        print("  3. Quit")
        print()
        try:
            choice = input("  Choice: ").strip()
        except KeyboardInterrupt:
            choice = '3'

        if choice == '1':
            self._start_new_game_plus()
        elif choice == '2':
            self.player = None
            self.floors = None
            # Don't call start_game() recursively — just return.
            # The original start_game loop will handle the menu naturally.
        else:
            self.quit_game()

    def _start_new_game_plus(self, preselected_world: str = None):
        """Transition into New Game+ with glitch narrative sequence."""
        p = self.player

        def pause(t=1.2):
            try:
                input("")
            except (KeyboardInterrupt, EOFError):
                pass

        # ── Select world immediately and lock it onto the player ────
        if preselected_world:
            chosen_world = preselected_world
        else:
            all_worlds   = list(GameConstants.NG_PLUS_WORLDS.keys())
            random.shuffle(all_worlds)
            prev_world   = getattr(p, 'ng_world', None)
            choices      = [w for w in all_worlds if w != prev_world] or all_worlds
            chosen_world = random.choice(choices)
        world_data    = GameConstants.NG_PLUS_WORLDS[chosen_world]
        world_display = world_data['display_name']
        # Set ng_world NOW so every subsequent call sees the correct world
        p.ng_world = chosen_world

        # Audit overpowered weapons before the glitch sequence
        self._audit_ng_weapons()

        print("\n" + "═"*60)
        print("  [ Press Enter to continue ]")
        print("═"*60)

        print("\nThe Reality Breaker falls.")
        pause()
        print("You stand in the silence of its absence.")
        print("Ten floors conquered. Every boss defeated.")
        print("The Labyrinth should be still.\n")
        pause()

        print("It isn't.\n")
        pause()

        print("The floor underneath you shifts.")
        print("Not shakes — shifts, like a file being overwritten.")
        pause()

        print("The walls start repeating textures.")
        print("The torches flicker in a pattern that isn't random.")
        pause()

        print("You watch a crack open in the air in front of you —")
        print("not in a wall, not in the floor.")
        print("In the air itself.")
        pause()

        print("\nThrough it you can see... this room.")
        print("The same room. Slightly wrong.")
        print("The corpse of the Reality Breaker is there, but it's")
        print("the wrong shape. The wrong colour. Moving.")
        pause()

        print("\nYou look down at your hands.")
        pause()
        print("Your hands are also slightly wrong.\n")
        pause()

        print("The glitch spreads.")
        print("Your armour stutters. Your weapon flickers in and out")
        print("of three different states simultaneously.")
        print("The inventory in your pack rearranges itself alphabetically,")
        print("then backwards, then into an order that has no name.")
        pause()

        print("\nYou try to run.")
        pause()
        print("There is nowhere to run to.")
        print("The room has already been replaced by its own echo.\n")
        pause()

        print("The last thing you see is the Labyrinth logo on the wall")
        print("— the one that was there when you started — and it is")
        print("glitching in a way that looks almost deliberate.")
        print("Almost like a warning that was always there.")
        pause()

        print("\nEverything goes black.\n")
        pause()
        pause()

        print("═"*60)
        print("  You wake up.")
        print("═"*60)
        pause()

        # Show the newly-selected world's lore wake text
        for line in world_data.get('wake_text', '').split('\n'):
            print(line)
        pause()

        print("\nYour stats carried over.")
        print("Your weapons carried over.")
        print("Your scars carried over.\n")
        pause()

        print("None of it will be enough.\n")
        pause()

        # Display the themed title screen for the selected world
        title = GameConstants.NG_PLUS_TITLE_SCREENS.get(
            chosen_world,
            f"\n{'═'*60}\n  WELCOME TO {world_display.upper()}\n{'═'*60}"
        )
        print(title)
        pause()

        print(f"  NG+ Cycle {getattr(p, 'ng_plus', 0) + 1}  |  {world_display}")
        print()
        pause()

        # Commit NG+ state
        p.current_floor   = 1
        p.current_room    = 'start'
        p.visited_rooms   = set()
        p.bosses_defeated = []
        p.secret_room_unlocked = False
        p.unique_items_spawned = set()
        p.ng_plus  = getattr(p, 'ng_plus', 0) + 1
        # ng_world already set at the top of this function

        print(f"  {p.name} the {p.get_class_title()}")
        print(f"  Carrying over: Level {p.level} | {len(p.inventory)} items | {len(p.inventory_weapons)} stored weapons")
        print(f"  The enemies here are unlike anything you faced before.")
        print(f"  They will not go easy on you.\n")

        self._generate_dungeon()  # branches to _generate_ng_plus_dungeon

        self.combat = CombatSystem(self)
        self.look_around()
        self.show_room_summary()
        self._game_loop()


    def fuse_class_menu(self) -> None:
        """Interactive class fusion menu."""""
        p = self.player
        if not p.can_fuse_class():
            if getattr(p, 'fusion_parents', None):
                print("  You have already fused your class.")
            elif p.class_tier < 5:
                print(f"  Fusion requires Tier 5. You are Tier {p.class_tier}.")
            else:
                print("  Fusion is only available in New Game+.")
            return

        base_classes = ['warrior', 'mage', 'rogue', 'paladin', 'berserker']
        rec = RecordsManager.load()
        if rec.get('void_walker_unlocked', False):
            base_classes.append('void_walker')

        current = p.character_class
        available = [(c, GameConstants.get_fusion(current, c))
                     for c in base_classes
                     if c != current and GameConstants.get_fusion(current, c)]

        print(f"\n{'═'*56}")
        print(f"  CLASS FUSION  —  {p.get_class_title()} (Tier 5)")
        print(f"  Choose a class to fuse with:")
        print(f"{'─'*56}")
        for i, (cls, fusion) in enumerate(available, 1):
            print(f"  {i}. + {cls.replace('_',' ').title():16} → {fusion['name']}")
            print(f"      {fusion['description']}")
            print(f"      Boss ability: {fusion['boss_ability_name']}")
        print(f"  0. Cancel")
        print(f"{'═'*56}")

        try:
            choice = input("  Choice: ").strip()
        except KeyboardInterrupt:
            return

        if choice == '0':
            print("  Fusion cancelled.")
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(available):
                target, fusion = available[idx]
                print(f"\n  Fuse {p.get_class_title()} with {target.replace('_',' ').title()}?")
                print(f"  Result: {fusion['name']}")
                print(f"  This cannot be undone.")
                confirm = input("  Confirm? (yes/no): ").strip().lower()
                if confirm in ('yes', 'y'):
                    p.fuse_class(target)
                else:
                    print("  Fusion cancelled.")
            else:
                print("  Invalid choice.")
        except (ValueError, IndexError):
            print("  Invalid choice.")

    def quit_game(self):
        """Exit game"""
        try:
            if input("\nSave before quitting? (y/n): ").strip().lower() in ['y', 'yes']:
                self.save_game()
        except KeyboardInterrupt:
            pass
        
        name = self.player.name if self.player else 'Adventurer'
        floor = self.player.current_floor if self.player else 1
        print("\n" + "="*56)
        print("  LABYRINTH -- Until Next Time")
        print("="*56)
        print(f"  The dungeon remembers you, {name}.")
        print(f"  You reached Floor {floor}/10.")
        print()
        print("  The stairs still descend. The darkness still waits.")
        print("  Come back when you're ready.")
        print("="*56)
        self.running = False

#################################################################################
# MAIN ENTRY POINT
#################################################################################

