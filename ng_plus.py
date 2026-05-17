"""LABYRINTH — New Game Plus"""
from __future__ import annotations
import random, json, os, logging
from typing import Dict, List, Optional, Set, Tuple, Any, TYPE_CHECKING, Callable
from difflib import get_close_matches
from dataclasses import dataclass, field
if TYPE_CHECKING:
    from game import Game

logger = logging.getLogger(__name__)

from constants import GameConstants
from records import RecordsManager


class NGPlusMixin:
    """NG+ transition and victory methods. Mixed into Game."""

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


