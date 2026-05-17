"""
================================================================================
LABYRINTH — Player Actions
================================================================================
All in-game player commands: movement, inventory, combat dispatch,
item use, class management, and map display.
Mixed into Game via ActionsMixin.
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
from constants import GameConstants, BossConfig
from weapons import WeaponSystem, WeaponComparison
from items import ItemHandler
from records import RecordsManager
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from room import Room
    from player import Player


class ActionsMixin:
    """Player action methods. Mixed into Game."""

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
            boss_floor = self.player.current_floor
            boss_config = BossConfig.generate(boss_floor)
            if boss_config['name'] not in self.player.bosses_defeated:
                print(f"! Blocked! Defeat {boss_config['name']} first!")
                return
        
        old_floor = self.player.current_floor
        
        if direction in ['down', 'up'] and 'floor' in next_id:
            next_floor = int(next_id.split('_')[0].replace('floor', ''))
            if next_floor != self.player.current_floor:
                self.player.current_floor = next_floor
                print(f"→ Floor {self.player.current_floor}")
                RecordsManager.update(total_floors_cleared=1,
                                      best_floor_reached=next_floor)
                
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
    

    def fight_enemy(self, enemy_name: str):
        """Fight enemy"""
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
        """Equip wearable item - FIXED"""
        if not item_name:
            wearables = [i for i in self.player.inventory if i in GameConstants.WEARABLE_ITEMS]
            if not wearables:
                print("No wearables!")
                return
            
            from collections import Counter
            stat_labels = {'strength':'STR','intelligence':'INT','agility':'AGI','luck':'LCK','vitality':'VIT','faith':'FTH','arcane':'ARC'}
            counts = Counter(wearables)
            unique_wearables = list(dict.fromkeys(wearables))
            print("Wearables:")
            for i, item in enumerate(unique_wearables, 1):
                effect = GameConstants.WEARABLE_ITEMS[item]
                lbl = stat_labels.get(effect['stat'], effect['stat'].upper()[:3])
                prefix = f"[{counts[item]}]" if counts[item] > 1 else ""
                print(f"  {i}. {prefix}{item} (+{effect['bonus']} {lbl})")
            wearables = unique_wearables  # use deduped list for choice
            
            try:
                choice = int(input("Choose: ")) - 1
                if 0 <= choice < len(wearables):
                    item_name = wearables[choice]
                else:
                    return
            except (ValueError, KeyboardInterrupt):
                print("Cancelled")
                return
        
        if item_name and item_name in self.player.inventory and item_name in GameConstants.WEARABLE_ITEMS:
            effect = GameConstants.WEARABLE_ITEMS[item_name]
            self.player.inventory.remove(item_name)
            self.player.stats[effect['stat']] += effect['bonus']
            self.player.wearables.append({'item': item_name, 'stat': effect['stat'], 'bonus': effect['bonus']})
            print(f"*** Equipped {item_name}! +{effect['bonus']} {effect['stat']}")
        else:
            print(f"You don't have '{item_name}' or it's not a wearable")
    

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
        """Use special actionable items"""
        if not item_name:
            print("Use what?")
            return
        
        if item_name == 'old map' and item_name in self.player.special_items:
            print("You study the old map...")
            self.show_map()
            return

        # d20 lives in special_items — handled below but needs early inventory bypass
        if item_name in ("gambler's d20", "d20") and "gambler's d20" not in self.player.special_items:
            print("You don't have a Gambler's d20.")
            return
        
        if item_name not in self.player.inventory:
            print(f"Don't have '{item_name}'")
            return
        
        if item_name not in GameConstants.ACTIONABLE_ITEMS:
            print(f"Can't use '{item_name}' like that")
            return
        
        action_type = GameConstants.ACTIONABLE_ITEMS[item_name]
        room = self.get_current_room()
        
        # TORCH - Open secret rooms
        if action_type == 'light' and item_name == 'torch':
            if 'Hidden Alcove' in room.name and not self.player.secret_room_unlocked:
                print("\n*** You place the torch in the wall sconce...")
                print("A hidden door slides open!")
                
                self.player.secret_room_unlocked = True
                self.player.inventory.remove('torch')
                
                secret_id = f"floor{self.player.current_floor}_secret"
                room.exits['secret'] = secret_id
                
                if secret_id not in self.floors[self.player.current_floor]:
                    self.floors[self.player.current_floor][secret_id] = Room(
                        "Secret Treasure Vault",
                        "A hidden vault glitters with treasures!",
                        self.player.current_floor,
                        ['weapon cache', 'weapon cache', 'ultimate health potion',
                         'experience gem', 'wisdom gem', 'legendary artifact'],
                        {'out': self.player.current_room},
                        [],
                        "Countless riches await!"
                    )
                
                print("\nUse 'go secret' to enter!")
            else:
                if 'torch' not in self.player.item_hints_shown:
                    self.player.item_hints_shown.add('torch')
                    print("You hold up the torch. Nothing happens here.")
                    print("  ★ HINT: Find the Hidden Alcove — it has a torch sconce on the wall.")
                    print("         The sconce looks like it could hold something. Use the torch there.")
                else:
                    print("The torch flickers. You need a Hidden Alcove with a wall sconce.")
        
        # RUSTY KEY - Open locked vaults
        elif action_type == 'key' and item_name == 'rusty key':
            if room.name == 'Locked Vault':
                print("\n*** The key fits perfectly! The chest opens!")
                self.player.inventory.remove('rusty key')
                
                treasures = ['weapon cache', 'weapon cache', 'legendary artifact',
                            'ultimate health potion', 'experience gem', 'power ring']
                for t in treasures:
                    if t not in room.items:
                        room.items.append(t)
                
                print(f"\nTreasures: {', '.join(treasures)}")
                print("The key crumbles to dust...")
            else:
                if 'rusty key' not in self.player.item_hints_shown:
                    self.player.item_hints_shown.add('rusty key')
                    print("You examine the key. It looks like it would fit a large lock...")
                    print("  ★ HINT: Find the Locked Vault — a sealed room with an ornate chest")
                    print("         and an old rusty keyhole. Use the key there to claim the treasure.")
                else:
                    print("The rusty key is waiting for the Locked Vault.")
        
        # BONE KEY - Open bone crypts
        elif action_type == 'bone_key' and item_name == 'bone key':
            if room.name == 'Bone Crypt':
                print("\n*** The bone key dissolves into the skeletal lock!")
                print("The bone door crumbles away, revealing hidden treasures!")
                
                self.player.inventory.remove('bone key')
                
                treasures = ['weapon cache', 'weapon cache', 'soul crystal',
                            'arcane pendant', 'titan gauntlet', 'wisdom gem']
                for t in treasures:
                    if t not in room.items:
                        room.items.append(t)
                
                print(f"\nTreasures: {', '.join(treasures)}")
            else:
                if 'bone key' not in self.player.item_hints_shown:
                    self.player.item_hints_shown.add('bone key')
                    print("The bone key rattles ominously. This is meant for a bone door...")
                    print("  ★ HINT: Find the Bone Crypt — a chamber where ancient bones line the walls")
                    print("         and a sealed bone door blocks the way deeper. The key fits that lock.")
                else:
                    print("The bone key rattles. It belongs in the Bone Crypt.")
        
        # DEMON SEAL - Banish demons and open demon gates
        elif action_type == 'demon_seal' and item_name == 'demon seal':
            if 'Demon Gate' in room.name:
                print("\n*** You press the demon seal into the gate!")
                print("The demonic chains shatter! A portal opens to the abyss!")
                
                self.player.inventory.remove('demon seal')
                
                treasures = ['weapon cache', 'weapon cache', 'weapon cache',
                            'demon seal', 'soul crystal', 'shadow cloak', 'elixir of life']
                for t in treasures:
                    if t not in room.items:
                        room.items.append(t)
                
                # Bonus: Remove all demon enemies instantly
                demon_enemies = [e for e in room.enemies if 'demon' in e.lower()]
                for demon in demon_enemies:
                    room.enemies.remove(demon)
                    print(f"The {demon} is banished back to the abyss!")
                
                print(f"\nTreasures from the abyss: {', '.join(treasures)}")
            elif any('demon' in e.lower() for e in room.enemies):
                print("\n*** You activate the demon seal!")
                demons = [e for e in room.enemies if 'demon' in e.lower()]
                for demon in demons:
                    room.enemies.remove(demon)
                    self.player.gain_experience(GameConstants.ENEMIES[demon.lower()]['exp'])
                    print(f"The {demon} is banished! +{GameConstants.ENEMIES[demon.lower()]['exp']} exp")
                self.player.inventory.remove('demon seal')
                print("The seal crumbles to ash...")
            else:
                if 'demon seal' not in self.player.item_hints_shown:
                    self.player.item_hints_shown.add('demon seal')
                    print("The demon seal pulses with dark energy. It is meant for demons...")
                    print("  ★ HINT: Use it in a Demon Gate room (sealed by arcane chains)")
                    print("         or carry it into any room with demon enemies to banish them instantly.")
                else:
                    print("The seal pulses. Take it to a Demon Gate or use it against demon enemies.")
        
        # CRYSTAL SHARD - Activate crystal mechanisms
        elif action_type == 'crystal' and item_name == 'crystal shard':
            if 'Crystal Chamber' in room.name:
                print("\n*** You insert the crystal shard into the mechanism!")
                print("The chamber floods with brilliant light!")
                
                self.player.inventory.remove('crystal shard')
                
                # Restore all mana and boost max mana
                old_max = self.player.max_mana
                self.player.max_mana += 30
                self.player.mana = self.player.max_mana
                
                # Boost intelligence
                self.player.stats['intelligence'] += 5
                
                treasures = ['weapon cache', 'ice crystal', 'magic scroll', 'arcane pendant']
                for t in treasures:
                    if t not in room.items:
                        room.items.append(t)
                
                print(f"*** Max Mana +30 ({old_max} → {self.player.max_mana})! Intelligence +5!")
                print(f"Treasures: {', '.join(treasures)}")
            else:
                if 'crystal shard' not in self.player.item_hints_shown:
                    self.player.item_hints_shown.add('crystal shard')
                    print("The crystal shard glows softly. It needs a crystal mechanism...")
                    print("  ★ HINT: Find the Crystal Chamber — every surface covered in crystalline")
                    print("         formations with a dormant mechanism at the centre. Insert the shard there.")
                else:
                    print("The shard glows. Bring it to the Crystal Chamber.")
        
        # VOID ESSENCE - Stabilize void portals
        elif item_name in ("gambler's d20", "d20") and "gambler's d20" in self.player.special_items:
            room = self.get_current_room()
            roll = random.randint(1, 20)
            if room.enemies:
                enemy = room.enemies[0]
                print(f"\n  ⚄ You roll the d20 against {enemy}... {roll}!")
                if roll == 20:
                    print(f"  ★ NATURAL 20! Pure luck obliterates {enemy}!")
                    print(f"  (The d20 shatters. One nat 20 per die.)")
                    self.player.special_items.remove("gambler's d20")
                    room.enemies.remove(enemy)
                    ng_e = getattr(self.player, 'ng_plus', 0)
                    enemy_pool = GameConstants.NG_PLUS_ENEMIES if ng_e > 0 else GameConstants.ENEMIES
                    self.player.gain_experience(enemy_pool.get(enemy.lower(), GameConstants.ENEMIES.get(enemy.lower(), {'exp': 50})).get('exp', 50))
                elif roll == 1:
                    print(f"  ✗ Nat 1. You trip, the d20 rolls into a crack. {enemy} looks delighted.")
                    self.player.special_items.remove("gambler's d20")
                    dmg = random.randint(5, 15)
                    self.player.health -= dmg
                    print(f"  You take {dmg} embarrassment damage.")
                else:
                    print(f"  Not a 20. The d20 stays with you.")
            else:
                print(f"\n  ⚄ You roll the d20 for fun... {roll}.")
                if roll == 20:
                    print(f"  ★ NAT 20! Nothing happens. But that felt incredible.")
                elif roll == 1:
                    print(f"  ✗ Nat 1. You stub your toe on the floor. -1 HP.")
                    self.player.health = max(1, self.player.health - 1)

        elif action_type == 'void' and item_name == 'void essence':
            if 'Void Tear' in room.name:
                print("\n*** You channel the void essence into the portal!")
                print("The tear stabilizes, revealing the void's secrets!")
                
                self.player.inventory.remove('void essence')
                
                # Major stat boost and legendary loot
                self.player.stats['strength'] += 4
                self.player.stats['intelligence'] += 4
                self.player.stats['agility'] += 4
                
                treasures = ['weapon cache', 'weapon cache', 'void essence',
                            'legendary artifact', 'ultimate health potion', 'wisdom gem']
                for t in treasures:
                    if t not in room.items:
                        room.items.append(t)
                
                print("*** All stats +4! The void rewards you!")
                print(f"Treasures: {', '.join(treasures)}")
            else:
                if 'void essence' not in self.player.item_hints_shown:
                    self.player.item_hints_shown.add('void essence')
                    print("The void essence writhes with otherworldly power. It needs a void tear...")
                    print("  ★ HINT: Find the Void Tear — a room where reality fractures, with a")
                    print("         swirling unstable portal. Channel the essence into it to stabilise it.")
                else:
                    print("The essence writhes. It belongs in the Void Tear room.")
        
        # PRIMORDIAL RUNE - Activate ancient monuments
        elif action_type == 'rune' and item_name == 'primordial rune':
            if 'Primordial Monument' in room.name:
                print("\n*** You place the rune upon the monument!")
                print("Ancient power flows through the ages!")
                
                self.player.inventory.remove('primordial rune')
                
                # Massive permanent bonuses
                old_hp = self.player.max_health
                old_mp = self.player.max_mana
                
                self.player.max_health += 50
                self.player.max_mana += 40
                self.player.health = self.player.max_health
                self.player.mana = self.player.max_mana
                
                self.player.stats['strength'] += 6
                self.player.stats['intelligence'] += 6
                self.player.stats['agility'] += 6
                
                treasures = ['weapon cache', 'weapon cache', 'weapon cache',
                            'legendary artifact', 'ultimate health potion', 'soul crystal']
                for t in treasures:
                    if t not in room.items:
                        room.items.append(t)
                
                print(f"*** Max HP +50 ({old_hp} → {self.player.max_health})!")
                print(f"*** Max MP +40 ({old_mp} → {self.player.max_mana})!")
                print("*** All stats +6! You are blessed by the ancients!")
                print(f"Treasures: {', '.join(treasures)}")
            else:
                if 'primordial rune' not in self.player.item_hints_shown:
                    self.player.item_hints_shown.add('primordial rune')
                    print("The primordial rune hums with ancient power. It belongs on a monument...")
                    print("  ★ HINT: Find the Primordial Monument — an ancient stone covered in glowing")
                    print("         runic inscriptions. Place the rune there to unlock its full power.")
                else:
                    print("The rune hums. Place it on the Primordial Monument.")
        
        # ANCIENT MEDALLION - Offer at shrines
        elif action_type == 'offering' and item_name == 'ancient medallion':
            if 'Shrine' in room.name:
                print("\n*** The altar erupts with brilliant light!")
                print("Ancient power flows through you!")
                
                self.player.inventory.remove('ancient medallion')
                
                if self.player.character_class == 'warrior':
                    self.player.stats['strength'] += 8
                    self.player.stats['agility'] += 3
                    print("*** Strength +8! Agility +3!")
                elif self.player.character_class == 'mage':
                    self.player.stats['intelligence'] += 8
                    self.player.stats['strength'] += 3
                    print("*** Intelligence +8! Strength +3!")
                else:
                    self.player.stats['agility'] += 8
                    self.player.stats['intelligence'] += 3
                    print("*** Agility +8! Intelligence +3!")
                
                self.player.max_health += 20
                self.player.health = self.player.max_health
                self.player.max_mana += 15
                self.player.mana = self.player.max_mana
                
                print(f"*** Max health +20! Max mana +15! Fully healed!")
            else:
                if 'ancient medallion' not in self.player.item_hints_shown:
                    self.player.item_hints_shown.add('ancient medallion')
                    print("You hold the medallion. It should be placed on an altar...")
                    print("  ★ HINT: Find the Sacred Shrine — an ancient room with a stone altar")
                    print("         that has a circular indentation. Place the medallion there.")
                else:
                    print("The medallion waits for the Sacred Shrine.")
        
        elif action_type == 'map':
            print("You study the old map...")
            self.show_map()
    

    def upgrade_class(self):
        """Upgrade class tier"""
        if not self.player.can_upgrade_class():
            if self.player.class_tier >= 3:
                print("Already max tier!")
            else:
                next_level = GameConstants.CLASS_UPGRADE_LEVELS[self.player.class_tier - 1]
                print(f"Need level {next_level}")
            return
        
        current = self.player.get_class_title()
        next_title = GameConstants.CLASS_NAMES[self.player.class_tier + 1][self.player.character_class]
        
        print(f"\n*** CLASS UPGRADE!")
        print(f"Current: {current} (Tier {self.player.class_tier})")
        print(f"Upgrade to: {next_title} (Tier {self.player.class_tier + 1})")
        print("\nBenefits: +5 all stats, +30 HP, +25 MP, +5% loot")
        
        try:
            if input(f"\nUpgrade to {next_title}? (y/n): ").strip().lower() in ['y', 'yes']:
                if self.player.upgrade_class():
                    print("Upgrade successful!")
        except KeyboardInterrupt:
            print("Cancelled")
    

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
