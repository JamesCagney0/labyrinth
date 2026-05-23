"""LABYRINTH — Save/Load/Delete"""
from __future__ import annotations
import random, json, os, logging
from typing import Dict, List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from game import Game

logger = logging.getLogger(__name__)

from constants import GameConstants, BossConfig, RoomTemplateConfig
from utils import safe_input
from records import RecordsManager
from combat  import CombatSystem
from player import Player
from room import Room


class SaveLoadMixin:
    """Save, load and delete methods. Mixed into Game."""

    def _list_save_slots(self) -> list:
        """List all save slots with their contents. Returns list of occupied slot numbers.

        Prints a formatted slot listing as a side effect — used by save_game,
        load_game, and delete_save to avoid duplicating the same 15-line loop.
        """
        occupied = []
        for slot in range(1, GameConstants.MAX_SAVE_SLOTS + 1):
            save_path = os.path.join(GameConstants.SAVE_DIRECTORY, f"save{slot}.json")
            if os.path.exists(save_path):
                try:
                    with open(save_path, 'r') as f:
                        data        = json.load(f)
                        p           = data.get('player', {})
                        name        = p.get('name', 'Unknown')
                        char_class  = p.get('character_class', 'warrior').title()
                        level       = p.get('level', 1)
                        floor       = p.get('current_floor', 1)
                        print(f"{slot}. {name} — {char_class} Lvl {level} — Floor {floor}")
                        occupied.append(slot)
                except (json.JSONDecodeError, OSError, KeyError, TypeError):
                    print(f"{slot}. [Corrupted Save]")
                    occupied.append(slot)
            else:
                print(f"{slot}. [Empty Slot]")
        return occupied

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
            
            self._list_save_slots()
            print(f"{GameConstants.MAX_SAVE_SLOTS + 1}. Cancel")
            
            try:
                choice = int(safe_input(f"\nChoose slot (1-{GameConstants.MAX_SAVE_SLOTS}): ").strip())
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
                    confirm = safe_input(f"Overwrite slot {choice}? (y/n): ").strip().lower()
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
            
            available_saves = self._list_save_slots()
            if not available_saves:
                print("\nNo save files found!")
                return False
            print(f"{GameConstants.MAX_SAVE_SLOTS + 1}. Cancel")
            
            try:
                choice = int(safe_input(f"\nChoose slot (1-{GameConstants.MAX_SAVE_SLOTS}): ").strip())
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
                    safe_input("  [ Press Enter to continue ]")
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
            
            available_saves = self._list_save_slots()
            if not available_saves:
                print("\nNo save files to delete!")
                return
            print(f"{GameConstants.MAX_SAVE_SLOTS + 1}. Cancel")
            
            try:
                choice = int(safe_input(f"\nDelete slot (1-{GameConstants.MAX_SAVE_SLOTS}): ").strip())
                if choice == GameConstants.MAX_SAVE_SLOTS + 1:
                    return
                if choice not in available_saves:
                    print("Invalid or empty slot!")
                    return
            except (ValueError, KeyboardInterrupt):
                return
            
            save_path = os.path.join(GameConstants.SAVE_DIRECTORY, f"save{choice}.json")
            
            confirm = safe_input(f"Delete slot {choice}? This cannot be undone! (y/n): ").strip().lower()
            if confirm in ['y', 'yes']:
                os.remove(save_path)
                print(f"✓ Slot {choice} deleted!")
                logger.info(f"Save file deleted: slot {choice}")
            else:
                print("Cancelled.")
        except OSError as e:
            logging.error(f"Delete save error: {e}", exc_info=True)
            print(f"✗ Delete failed: {e}")
    

