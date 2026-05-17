"""
================================================================================
LABYRINTH — Save / Load System
================================================================================
Five-slot save system with full serialisation, migration, and delete.
Methods mixed into Game via SaveLoadMixin.
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
from constants import GameConstants
from records import RecordsManager
from player import Player
from typing import Optional


class SaveLoadMixin:
    """Save/load/delete methods. Mixed into Game."""

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
                    except:
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
                        'items': room.items,
                        'enemies': room.enemies,
                        'visited': room.visited,
                        'exits': room.exits
                    } for room_id, room in floor_rooms.items()
                }
            
            with open(save_path, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            logger.info(f"Game saved to slot {choice}: {self.player.name} (Lvl {self.player.level}, Floor {self.player.current_floor})")
            print(f"✓ Game saved to slot {choice}!")
        except Exception as e:
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
                    except:
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
            
            self.floors = {}
            for floor_str, floor_data in save_data['floors'].items():
                floor_num = int(floor_str)
                self.floors[floor_num] = {}
                
                for room_id, room_data in floor_data.items():
                    if room_id == 'start':
                        name, desc, atmo = "Entrance Hall", "The dungeon entrance.", "Adamus the Loyal has set up shop here. Use 'shop' to trade."
                    elif 'boss' in room_id:
                        template = BossConfig.get_boss_room_template(floor_num)
                        name, desc, atmo = template.name, template.description, template.atmosphere
                    elif 'stairs' in room_id:
                        name, desc, atmo = "Ancient Stairway", "Stone stairs descend deeper.", ""
                    elif 'secret' in room_id:
                        name, desc, atmo = "Secret Treasure Vault", "A hidden vault glitters with treasures!", "Countless riches!"
                    else:
                        templates = RoomTemplateConfig.get_templates_for_floor(floor_num)
                        if templates:
                            template = random.choice(templates)
                            name, desc, atmo = template.name, template.description, template.atmosphere
                        else:
                            name, desc, atmo = "Mysterious Room", "A dark room.", ""
                    
                    self.floors[floor_num][room_id] = Room(
                        name, desc, floor_num,
                        room_data['items'], room_data['exits'],
                        room_data['enemies'], atmo
                    )
                    self.floors[floor_num][room_id].visited = room_data['visited']
            
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
            
        except Exception as e:
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
                    except:
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
        except Exception as e:
            logging.error(f"Delete save error: {e}", exc_info=True)
            print(f"✗ Delete failed: {e}")
    

    # ─────────────────────────────────────────────────────────────
