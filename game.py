"""
LABYRINTH — Game Orchestrator
The Game class wires all systems together via focused mixins.
"""
from __future__ import annotations
import logging
from typing import Dict, List, Optional, TYPE_CHECKING
from difflib import get_close_matches

logger = logging.getLogger(__name__)

from constants   import GameConstants, BossConfig, RoomTemplateConfig
from records     import RecordsManager
from room        import Room
from player      import Player
from weapons     import WeaponSystem, WeaponComparison
from items       import ItemHandler
from combat      import DamageCalculator, CombatSystem
from map_gen     import MapGenerator
from actions     import ActionsMixin
from shop        import ShopMixin
from save_load   import SaveLoadMixin
from ng_plus     import NGPlusMixin
from dungeon     import DungeonMixin
from utils       import safe_input
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





class Game(DungeonMixin, SaveLoadMixin, NGPlusMixin, ShopMixin, ActionsMixin):
    """
    Main game orchestrator.
    All gameplay systems live in focused mixin modules:
      DungeonMixin   — floor/room generation
      SaveLoadMixin  — save, load, delete
      NGPlusMixin    — NG+ transition, victory screen
      ShopMixin      — Adamus shop: buy and sell
      ActionsMixin   — all player commands and in-game actions
    """

    def __init__(self):
        self.player: Optional[Player] = None
        self.floors: Optional[Dict[int, Dict[str, Room]]] = None
        self.running = True
        self.combat = None
        self.registry = CommandRegistry()
        self._last_input = ''
        self.debug_mode  = True
        self.mature_mode  = True
        self._register_commands()
        
    def _register_commands(self):
        """Register all game commands"""
        r = self.registry.register
        
        @r('help', 'h')
        def cmd_help(g): g.show_help(full='all' in g._last_input)
        
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
                room = g.get_current_room()
                if 'old map' in room.items:
                    print("You need a map — there's one right here. Try 'take old map' or 'takeall'.")
                else:
                    print("You need a map to use this command.")
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
    

        # ── Debug commands (only active when game.debug_mode = True) ──
        @r('warp')
        def cmd_warp(g, *args):
            if not g.debug_mode:
                print("Unknown command. Type 'help'")
                return
            try:
                floor = int(args[0]) if args else 1
                if floor < 1 or floor > GameConstants.NUM_FLOORS:
                    print(f"  Floor must be 1-{GameConstants.NUM_FLOORS}")
                    return
                g.player.current_floor = floor
                start = 'start' if floor == 1 else f'floor{floor}_start'
                if start in g.floors.get(floor, {}):
                    g.player.current_room = start
                else:
                    g.player.current_room = next(iter(g.floors[floor]))
                g.player.visited_rooms.add(g.player.current_room)
                print(f"  [DEBUG] Warped to floor {floor}")
                g.look_around()
                g.show_room_summary()
            except (IndexError, ValueError):
                print("  Usage: warp <floor>")

        @r('give')
        def cmd_give(g, *args):
            if not g.debug_mode:
                print("Unknown command. Type 'help'")
                return
            if not args:
                print("  Usage: give <item>  |  give gold <amount>")
                return
            item = ' '.join(args)
            # Special case: give gold <amount>
            parts = item.split()
            if parts[0] == 'gold' and len(parts) > 1:
                try:
                    amount = int(parts[1])
                    g.player.gold_coins += amount
                    print(f"  [DEBUG] +{amount} gold (now {g.player.gold_coins}g)")
                    return
                except ValueError:
                    pass
            # Route through the regular item handler directly — no room round-trip
            # so failed adds don't leave debris in the room's item list
            g._handle_regular_item(item)

        @r('levelup')
        def cmd_levelup(g, *args):
            if not g.debug_mode:
                print("Unknown command. Type 'help'")
                return
            try:
                target = int(args[0]) if args else g.player.level + 1
                while g.player.level < target:
                    g.player.experience = g.player.experience_to_next
                    g.player.gain_experience(0)
                print(f"  [DEBUG] Now Level {g.player.level}")
            except (IndexError, ValueError):
                print("  Usage: levelup <target_level>")

        @r('fullheal')
        def cmd_fullheal(g, *args):
            if not g.debug_mode:
                print("Unknown command. Type 'help'")
                return
            g.player.health = g.player.max_health
            g.player.mana   = g.player.max_mana
            print(f"  [DEBUG] HP and MP fully restored")

        @r('unlock')
        def cmd_unlock(g, *args):
            if not g.debug_mode:
                print("Unknown command. Type 'help'")
                return
            target = args[0].lower() if args else ''
            if target in ('voidwalker', 'void_walker', 'void walker'):
                from records import RecordsManager
                RecordsManager.update(void_walker_unlocked=True, runs_completed=1)
                print("  [DEBUG] Void Walker unlocked")
            elif target == 'all':
                from records import RecordsManager
                RecordsManager.update(void_walker_unlocked=True, runs_completed=1)
                print("  [DEBUG] All unlocks applied")
            else:
                print("  Usage: unlock voidwalker | unlock all")

        @r('debugfuse')
        def cmd_debugfuse(g, *args):
            if not g.debug_mode:
                print("Unknown command. Type 'help'")
                return
            if len(args) < 2:
                print("  Usage: debugfuse <class1> <class2>")
                print("  Classes: warrior mage rogue paladin berserker void_walker")
                return
            c1 = args[0].lower().replace(' ', '_')
            c2 = args[1].lower().replace(' ', '_')
            p  = g.player
            # Force to tier 5 first
            p.class_tier = 5
            if p.fuse_class(c2 if p.character_class == c1 else c1):
                print(f"  [DEBUG] Fused {c1} + {c2} → {p.get_class_title()}")
            else:
                print(f"  [DEBUG] Fusion failed — check class names")

        @r('debugngplus')
        def cmd_debugngplus(g, *args):
            if not g.debug_mode:
                print("Unknown command. Type 'help'")
                return
            valid_worlds = list(GameConstants.NG_PLUS_WORLDS.keys())
            world = args[0].lower() if args else None
            if world and world not in valid_worlds:
                print(f"  Unknown world. Valid options:")
                for w in valid_worlds:
                    print(f"    {w}")
                return
            print(f"  [DEBUG] Forcing NG+ transition{' → ' + world if world else ''}...")
            # Clear state exactly as a real NG+ transition would
            p = g.player
            p.bosses_defeated = []
            p.ng_plus = max(0, getattr(p, 'ng_plus', 0))  # preserve if already set
            g._start_new_game_plus(preselected_world=world)

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
                choice = safe_input("\nChoice: ")
                
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
                        safe_input("  [ Press Enter to return ]")
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
        # Show mature content notice once if --mature not passed
        if not getattr(self, 'mature_mode', False):
            if not getattr(self, '_mature_asked', False):
                self._mature_asked = True
                # Mature content is opt-in only — default is family-friendly
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

                self._last_input = cmd_input  # track for help all and debug
                parts = cmd_input.split()
                command = parts[0]
                args = parts[1:]
                
                self.registry.execute(command, args, self)

                if self.player and self.running:
                    self.player.show_status_summary()
                    
            except EOFError:
                break  # stdin closed — exit cleanly
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
            name = safe_input("Name: ") or "Adventurer"
            
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
            choice = safe_input("Class: ")
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
                wchoice = int(safe_input("Choose (1-8): ") or "0") - 1
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
    

    def quit_game(self):
        """Exit game"""
        try:
            if safe_input("\nSave before quitting? (y/n): ").lower() in ['y', 'yes']:
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


