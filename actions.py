"""LABYRINTH — Player actions and commands"""
from __future__ import annotations
import random, json, os, logging
from typing import Dict, List, Optional, Set, Tuple, Any, TYPE_CHECKING, Callable
from difflib import get_close_matches
from collections import Counter
from dataclasses import dataclass, field
if TYPE_CHECKING:
    from game import Game

logger = logging.getLogger(__name__)

from constants import GameConstants, BossConfig
from weapons import WeaponSystem, WeaponComparison
from items import ItemHandler
from records import RecordsManager


class ActionsMixin:
    """All player action methods. Mixed into Game."""

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

