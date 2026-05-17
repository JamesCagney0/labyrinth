"""LABYRINTH — Lore, narrative and NG+ title screens"""
from __future__ import annotations
import random, json, os, logging
from typing import Dict, List, Optional, Set, Tuple, Any, TYPE_CHECKING, Callable
from difflib import get_close_matches
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class LoreData:
    """All narrative constants. Imported into GameConstants."""

    NG_PLUS_TITLE_SCREENS = {

        'fractured_labyrinth': """
╔░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░╗
░                                                                              ░
║  ░▒▓██╗   ░▒ ████╗ ██████╗░░ ██╗ ░  ██╗ ██████╗ ████╗ ███╗ ██████╗ ██╗ ██╗ ║
░  ░░ ██║  ██╔░░██╔╝ ██╔══██╗ ░██╗██╔╝ ░█╔══██║ █████╗ ████╗ ╚═██╔═╝ ██║ ██║ ░
║  ░░ ██║  █████╗ ██╔╝ ██████╔╝ ████╔╝  ██████╔╝ ██╔██╗ ██╔██╗  ██║  ███████║ ║
░  ░░ ██║  ██╔══╝ ██╔╗ ██╔══██╗  ██╔╝   ██╔══██╗ ██║╚██╗██║  ██╗ ██║ ██╔══██║ ░
║  ░███████╗██║  ████╔╝  ██║  ██║  ██║   ██║  ██║ ██║ ╚████║  ██║  ██║  ██║  ║
░  ░╚══════╝╚═╝  ╚═════╝  ╚═╝  ╚═╝  ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝  ╚═╝  ╚═╝  ╚═╝  ░
╗                                                                              ╔
░  ░  ═══  T̷H̸E̴ ̴L̸A̷B̵Y̴R̸I̷N̵T̴H̸ ̵H̸A̴S̶ ̷B̶R̴O̸K̷E̵N̶.̴ ̵Y̷O̴U̴ ̸A̵R̵E̷ ̴S̸T̵I̶L̷L̵ ̵I̴N̸ ̷I̶T̷.̸  ░
╚░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░╝""",

        'drowned_kingdom': """
≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋
≈                                                                            ≈
≋   ██████╗ ██████╗  ██████╗ ██╗    ██╗███╗  ██╗███████╗██████╗             ≋
≈   ██╔══██╗██╔══██╗██╔═══██╗██║    ██║████╗ ██║██╔════╝██╔══██╗            ≈
≋   ██║  ██║██████╔╝██║   ██║██║ █╗ ██║██╔██╗██║█████╗  ██║  ██║            ≋
≈   ██║  ██║██╔══██╗██║   ██║██║███╗██║██║╚████║██╔══╝  ██║  ██║            ≈
≋   ██████╔╝██║  ██║╚██████╔╝╚███╔███╔╝██║ ╚███║███████╗██████╔╝            ≋
≈   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚══╝╚══╝ ╚═╝  ╚══╝╚══════╝╚═════╝             ≈
≋                                                                            ≋
≈   ██╗  ██╗██╗███╗  ██╗ ██████╗ ██████╗  ██████╗ ███╗  ███╗               ≈
≋   ██║ ██╔╝██║████╗ ██║██╔════╝ ██╔══██╗██╔═══██╗████╗████║               ≋
≈   █████╔╝ ██║██╔██╗██║██║  ███╗██║  ██║██║   ██║██╔████╔██║               ≈
≋   ██╔═██╗ ██║██║╚████║██║   ██║██║  ██║██║   ██║██║╚██╔╝██║               ≋
≈   ██║  ██╗██║██║ ╚███║╚██████╔╝██████╔╝╚██████╔╝██║ ╚═╝ ██║               ≈
≋   ╚═╝  ╚═╝╚═╝╚═╝  ╚══╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝     ╚═╝               ≋
≈                                                                            ≈
≋              ≈≈≈  Something vast waits below.  ≈≈≈                        ≋
≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋""",

        'ashen_wastes': """
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
▓                                                                              ▓
▓    ████╗  ██████╗██╗  ██╗███████╗███╗  ██╗                                  ▓
▓   ██╔══██╗██╔════╝██║  ██║██╔════╝████╗ ██║                                 ▓
▓   ███████║╚█████╗ ███████║█████╗  ██╔██╗██║                                 ▓
▓   ██╔══██║ ╚═══██╗██╔══██║██╔══╝  ██║╚████║                                 ▓
▓   ██║  ██║██████╔╝██║  ██║███████╗██║ ╚███║                                 ▓
▓   ╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚══╝                                ▓
▓              ██╗    ██╗ █████╗ ███████╗████████╗███████╗███████╗            ▓
▓              ██║    ██║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔════╝            ▓
▓              ██║ █╗ ██║███████║███████╗   ██║   █████╗  ███████╗            ▓
▓              ██║███╗██║██╔══██║╚════██║   ██║   ██╔══╝  ╚════██║            ▓
▓              ╚███╔███╔╝██║  ██║███████║   ██║   ███████╗███████║            ▓
▓               ╚══╝╚══╝ ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚══════╝            ▓
▓                                                                              ▓
▓        ∴ ∴ ∴   Everything here has already burned.   ∴ ∴ ∴                 ▓
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓""",

        'mechanical_depths': """
╔╦══╦══╦══╦══╦══╦══╦══╦══╦══╦══╦══╦══╦══╦══╦══╦══╦══╦══╦══╦══╦══╦══╦══╦══╦╗
╠╣                                                                          ╠╣
╠╣  ⚙  ███╗  ███╗███████╗ ██████╗██╗  ██╗ █████╗ ███╗  ██╗██╗ ██████╗ ⚙  ╠╣
╠╣     ████╗████║██╔════╝██╔════╝██║  ██║██╔══██╗████╗ ██║██║██╔════╝     ╠╣
╠╣     ██╔████╔██║█████╗  ██║     ███████║███████║██╔██╗██║██║██║          ╠╣
╠╣     ██║╚██╔╝██║██╔══╝  ██║     ██╔══██║██╔══██║██║╚████║██║██║          ╠╣
╠╣     ██║ ╚═╝ ██║███████╗╚██████╗██║  ██║██║  ██║██║ ╚███║██║╚██████╗ ⚙  ╠╣
╠╣     ╚═╝     ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚══╝╚═╝ ╚═════╝    ╠╣
╠╣              ██████╗ ███████╗██████╗ ████████╗██╗  ██╗███████╗          ╠╣
╠╣              ██╔══██╗██╔════╝██╔══██╗╚══██╔══╝██║  ██║██╔════╝          ╠╣
╠╣  ⚙           ██║  ██║█████╗  ██████╔╝   ██║   ███████║███████╗     ⚙   ╠╣
╠╣              ██║  ██║██╔══╝  ██╔═══╝    ██║   ██╔══██║╚════██║          ╠╣
╠╣              ██████╔╝███████╗██║        ██║   ██║  ██║███████║          ╠╣
╠╣              ╚═════╝ ╚══════╝╚═╝        ╚═╝   ╚═╝  ╚═╝╚══════╝          ╠╣
╠╣                                                                          ╠╣
╠╣          [ SYSTEM NOMINAL ] [ INTRUDER DETECTED ] [ PROCESSING ]         ╠╣
╚╩══╩══╩══╩══╩══╩══╩══╩══╩══╩══╩══╩══╩══╩══╩══╩══╩══╩══╩══╩══╩══╩══╩══╩══╩╝""",

        'plague_cathedral': """
†════════════════════════════════════════════════════════════════════════════†
†                                                                            †
†    ██████╗ ██╗      █████╗  ██████╗ ██╗   ██╗███████╗                     †
†    ██╔══██╗██║     ██╔══██╗██╔════╝ ██║   ██║██╔════╝                     †
†    ██████╔╝██║     ███████║██║  ███╗██║   ██║█████╗                       †
†    ██╔═══╝ ██║     ██╔══██║██║   ██║██║   ██║██╔══╝                       †
†    ██║     ███████╗██║  ██║╚██████╔╝╚██████╔╝███████╗                     †
†    ╚═╝     ╚══════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝                     †
†                                                                            †
†    ██████╗ █████╗ ████████╗██╗  ██╗███████╗██████╗  █████╗ ██╗            †
†   ██╔════╝██╔══██╗╚══██╔══╝██║  ██║██╔════╝██╔══██╗██╔══██╗██║            †
†   ██║     ███████║   ██║   ███████║█████╗  ██║  ██║███████║██║            †
†   ██║     ██╔══██║   ██║   ██╔══██║██╔══╝  ██║  ██║██╔══██║██║            †
†   ╚██████╗██║  ██║   ██║   ██║  ██║███████╗██████╔╝██║  ██║███████╗       †
†    ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═════╝ ╚═╝  ╚═╝╚══════╝       †
†                                                                            †
†        ✝  The faith here is real. What it worships is not.  ✝             †
†════════════════════════════════════════════════════════════════════════════†""",
    }


    # ── FUSION CLASSES ────────────────────────────────────────────
    # Available in NG+ at tier 5. Key is frozenset of two parent classes.
    # stat_bonus: added on top of the averaged parent stats.
    # passive/boss_ability: string keys checked in combat code.

    FLOOR_LORE: Dict[int, str] = {
        1:  "Floor 1 — The Holding Pens\n"
            "  They say the dungeon was built as a prison. Not for men.\n"
            "  Whatever was held here got out a long time ago.\n"
            "  The guards stayed. They had nowhere else to go.",
        2:  "Floor 2 — The Barracks\n"
            "  Someone was preparing for a war down here.\n"
            "  The weapons are still racked. The soldiers are still standing.\n"
            "  The war never came. They've been waiting ever since.",
        3:  "Floor 3 — The Undercroft\n"
            "  The dead were buried here as a formality.\n"
            "  The formality didn't take.\n"
            "  Whatever animates them now, it isn't the magic that put them down.",
        4:  "Floor 4 — The Arcane Quarter\n"
            "  A researcher named Varek built his laboratory here.\n"
            "  His notes are scattered everywhere. His last entry reads:\n"
            "  \'It is not responding to the ritual. It is responding to ME.\'",
        5:  "Floor 5 — The Elemental Core\n"
            "  The dungeon was built over a ley line convergence.\n"
            "  Someone tapped it. The elements disagree with what was done.\n"
            "  They have been disagreeing, loudly, for three hundred years.",
        6:  "Floor 6 — The Forgotten Sanctum\n"
            "  There was a religion here once. It worshipped something underneath.\n"
            "  The worshippers are gone. The something underneath is still receiving prayers.\n"
            "  It has gotten very patient.",
        7:  "Floor 7 — The Abyss Approach\n"
            "  You can feel it now. A pressure behind your eyes.\n"
            "  Something is aware of you — has been since floor four.\n"
            "  It has been deciding whether you are worth its attention.",
        8:  "Floor 8 — The Void Corridor\n"
            "  Varek's final experiment is down here somewhere.\n"
            "  His notes describe \'a thing that should not exist in three dimensions.\'\n"
            "  He was optimistic about containing it. He was wrong.",
        9:  "Floor 9 — The Throne Approach\n"
            "  The dungeon was not always like this.\n"
            "  Something changed it. Rewrote the walls, replaced the guards,\n"
            "  decorated the ceiling with the names of everyone who made it this far.\n"
            "  Your name is not yet on the ceiling.",
        10: "Floor 10 — The Core\n"
            "  The Reality Breaker did not arrive here. It was made here.\n"
            "  Varek built it as a key. He never specified what it was meant to open.\n"
            "  You are about to find out.",
    }

    # ── Boss intro monologues ────────────────────────────────────
    # One line from the boss before combat. Shown after the boss room desc.

    BOSS_INTROS: Dict[str, str] = {
        'Arena Champion':        "\"Finally. Someone worth killing.\"",
        'Necromancer Lord':      "\"You walk into my domain and expect to leave. Interesting.\n"
                                 "  I will add you to my collection.\"",
        'Stone Titan':           "The titan does not speak. It simply turns to face you.\n"
                                 "  That is worse.",
        'Shadow Assassin':       "\"I've been watching you since floor one.\n"
                                 "  You fight like someone who expects to survive. Charming.\"",
        'Flame Lord':            "\"Everything burns eventually.\n"
                                 "  You are simply next in the queue.\"",
        'Frost Monarch':         "\"Stop.\n  Feel that? That's the cold deciding\n"
                                 "  whether to preserve you or end you.\"",
        'Void Walker Prime':     "It speaks in a frequency that isn't sound.\n"
                                 "  What you feel is not words. It is intent. And the intent is not kind.",
        'Ancient Dragon':        "\"I have slept for three centuries.\n"
                                 "  You are the first thing in three centuries worth waking for.\n"
                                 "  I am not certain that is a compliment.\"",
        'Demon King':            "\"I was summoned. I was bound. I was left here.\n"
                                 "  Whoever bound me is long dead.\n"
                                 "  You will join them shortly.\"",
        'Reality Breaker':       "The Reality Breaker does not speak with language.\n"
                                 "  It speaks with the space between words.\n"
                                 "  What you understand, in the marrow of your bones, is this:\n"
                                 "  \'You were not supposed to make it here.\'",
    }

    # ── Story journal entries ────────────────────────────────────
    # Discoverable across floors. Piece together the dungeon's history.
    # Found in specific room types — injected during dungeon generation.

    JOURNAL_ENTRIES: Dict[str, str] = {
        'journal_1': (
            "[ Researcher's Notes — Entry 1 ]\n"
            "  The ley convergence is stronger than the survey indicated.\n"
            "  I have requisitioned additional containment materials.\n"
            "  The prison warden is cooperative. He does not ask what I am containing.\n"
            "  This is ideal."
        ),
        'journal_2': (
            "[ Researcher's Notes — Entry 7 ]\n"
            "  The entity responds to intent, not incantation.\n"
            "  This means conventional binding will not hold it.\n"
            "  I am working on an alternative.\n"
            "  The guards on floor three have begun reporting sounds from below.\n"
            "  I have told them it is the pipes."
        ),
        'journal_3': (
            "[ Researcher's Notes — Entry 14 ]\n"
            "  I have named the entity the Reality Breaker.\n"
            "  Not for what it does — for what it is.\n"
            "  It exists at the seam between what is and what could be.\n"
            "  It does not break reality. It reminds reality\n"
            "  that it is only one of many possibilities."
        ),
        'journal_4': (
            "[ Warden's Log — Undated ]\n"
            "  Varek has not been seen in four days.\n"
            "  His laboratory is sealed from the inside.\n"
            "  We can hear him working.\n"
            "  He sounds... pleased."
        ),
        'journal_5': (
            "[ Researcher's Notes — Final Entry ]\n"
            "  It is not responding to the ritual.\n"
            "  It is responding to ME.\n"
            "  I think it has been responding to me since the beginning.\n"
            "  I think I was never the researcher here.\n"
            "  I think I was the key.\n"
            "  I think I always knew."
        ),
    }

    # ── NG+ WORLDS ────────────────────────────────────────────────
    # 5 themes; one is picked randomly when NG+ begins and stored as
    # player.ng_world.  Each world is fully self-contained.

    # ── Enemy behaviours (v7.5.2) ────────────────────────────────
    # Defines how specific enemies fight differently in regular combat.
    # Keys:
    #   regen/regen_cond  — HP restored per turn unless weapon has matching trait
    #   dmg_reduce/dmg_cond — fraction of player damage blocked unless matching trait
    #   inflict           — status effect applied on hit: bleed | poison | weaken
    #   buff_others       — True: buffs other enemies in room each turn (+20% dmg)
    #   intent            — text shown before the enemy attacks (warning/flavour)
    #   special_turn      — every N turns: enemy uses special attack
    #   special_dmg_mult  — damage multiplier for the special attack
    #   special_msg       — name of the special attack
