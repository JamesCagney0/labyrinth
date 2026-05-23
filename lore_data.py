"""LABYRINTH — Lore, narrative and NG+ title screens"""
from __future__ import annotations
import logging
from typing import Dict, List

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
                                 "  'You were not supposed to make it here.'",

        # ── FRACTURED LABYRINTH ──────────────────────────────────
        'The Glitch':            "The room stutters.\n"
                                 "  You see yourself — from three different angles simultaneously.\n"
                                 "  One of those angles is wrong.\n"
                                 "  \"Oh,\" it says, in a voice made of interference. \"A new variable.\"",

        'The Undying Architect': "It is building something as you arrive.\n"
                                 "  From nothing. With nothing.\n"
                                 "  It does not look at you.\n"
                                 "  \"You are either the final piece or the structural flaw,\" it says.\n"
                                 "  \"I will determine which.\"",

        'The Hollow King':       "The Hollow King does not speak.\n"
                                 "  It has nothing to speak with.\n"
                                 "  But something in this room — some absence — turns to face you.\n"
                                 "  The cold that touches your chest is not temperature.\n"
                                 "  It is the feeling of being noticed by something with no face.",

        'The Shadow Itself':     "Every shadow in the room leaves its surface and moves here.\n"
                                 "  Not toward you — to it.\n"
                                 "  The Darkness does not speak. It does not need to.\n"
                                 "  It is simply all of it, now, in one place.\n"
                                 "  Looking at you.",

        'The Infernal Echo':     "\"AGAIN,\" it says.\n"
                                 "  The word bounces off the walls and comes back hotter.\n"
                                 "  \"I have ended things like you before. I will end things like you again.\n"
                                 "  I will end them in a fire that began before you were born\n"
                                 "  and will continue after you are ash.\"",

        'Absolute Zero':         "It doesn't speak immediately.\n"
                                 "  It lets the temperature drop.\n"
                                 "  Eight degrees. Five. Zero.\n"
                                 "  When it finally speaks, the words crystallise in the air:\n"
                                 "  \"At absolute zero, nothing moves. Nothing changes. Nothing survives.\n"
                                 "  I find this\" — the word drops like a stone — \"preferable.\"",

        'The Void Prince':       "\"I do not grant audiences,\" the Void Prince says,\n"
                                 "  from a throne made of the space where something used to be.\n"
                                 "  \"And yet here you are.\n"
                                 "  I find this\" — the silence stretches — \"mildly interesting.\"",

        'The Fracture God':      "It has one finger touching the crack in the wall.\n"
                                 "  Just one finger. Not pushing. Waiting.\n"
                                 "  \"If I press now,\" it says, without turning,\n"
                                 "  \"the room becomes two rooms. If I press harder, this floor becomes two floors.\n"
                                 "  I wonder how hard I would need to press\n"
                                 "  to make you into two yous.\"",

        'The First Beast':       "It opens its eyes.\n"
                                 "  This is not remarkable. Things open their eyes.\n"
                                 "  But The First Beast opens its eyes for the first time. Every time.\n"
                                 "  The sound it makes has no name.\n"
                                 "  You feel it in the part of you that is older than language.\n"
                                 "  That part says: run.",

        'The Origin Breaker':    "It is standing in the exact centre of the room.\n"
                                 "  Not close to the centre. The exact centre, to a precision\n"
                                 "  that should not be possible in a room with no measuring instruments.\n\n"
                                 "  It looks at you.\n\n"
                                 "  \"You shouldn't be here,\" it says.\n"
                                 "  Not as a threat. Not as a warning.\n"
                                 "  As a statement of fact, the way you'd note a number that doesn't balance.\n\n"
                                 "  \"This is the end of the dungeon's geometry. Beyond this point,\n"
                                 "  the architecture stops making promises.\n"
                                 "  You won the game. I am what winning looks like.\"\n\n"
                                 "  It takes one step forward. The room agrees with the step.\n\n"
                                 "  \"Now. Let us find out what you're made of.\n"
                                 "  Before I unmake it.\"",

        # ── THE DROWNED KINGDOM ──────────────────────────────────
        'The Tide Warden':       "\"Leave.\"\n"
                                 "  One word. The water in the room moves with it.\n"
                                 "  \"I have said this to everyone who came before you.\n"
                                 "  They left.\"",

        'The Drowned Admiral':   "The fleet appears in the walls.\n"
                                 "  Silhouettes of ships, still burning, still sinking, still following orders.\n"
                                 "  \"You have crossed into Admiral's waters,\" it says.\n"
                                 "  \"These waters do not accept trespassers.\n"
                                 "  They accept only the drowned.\"",

        'The Coral Throne':      "It does not stand. It does not sit.\n"
                                 "  It has grown into the room — throne and king indistinguishable.\n"
                                 "  The coral has spread as far as the walls allow.\n"
                                 "  When it speaks, the words come from everywhere.\n"
                                 "  \"You are soft,\" it observes. \"The reef will fix that.\"",

        'The Siren Queen':       "\"Don't fight it.\"\n"
                                 "  Her voice lands on you like warm water.\n"
                                 "  \"The song is not a weapon. It is a comfort. Come closer.\"\n"
                                 "  She smiles. It is the most beautiful thing you have ever seen.\n"
                                 "  Something in the back of your skull says: that is the point.",

        'The Pressure God':      "You feel it before you see it.\n"
                                 "  Not cold. Not heat. Pressure. The feeling of depth.\n"
                                 "  As if you are two miles underwater right now.\n"
                                 "  As if you have always been two miles underwater.\n"
                                 "  As if air was the dream.\n"
                                 "  \"Yes,\" it says. \"Exactly like that.\"",

        'The Abyssal Duke':      "The court is already assembled.\n"
                                 "  You are the only one in it still breathing.\n"
                                 "  The Duke looks at you with the professional curiosity\n"
                                 "  of something that has been judging visitors for centuries.\n"
                                 "  \"Interesting,\" it says finally. \"You're alive.\n"
                                 "  How novel. How temporary.\"",

        'The Leviathan Prince':  "The room is not big enough for it.\n"
                                 "  The Leviathan Prince is not entirely in this room.\n"
                                 "  It is mostly in the ocean this dungeon has replaced,\n"
                                 "  and in the dark water at the edge of every map ever drawn.\n"
                                 "  The part of it that is here turns to face you.\n"
                                 "  That part alone is larger than anything should be.",

        'The Sunken God':        "Its eyes open. This takes twelve seconds.\n"
                                 "  The eyelids move like the opening of something geological.\n"
                                 "  It has been here since before this was a dungeon.\n"
                                 "  Since before this was a kingdom. Since before there were kingdoms.\n"
                                 "  It has never seen anyone make it this far.\n"
                                 "  It is — and this is purely academic — impressed.",

        'The Deep Ancient':      "It has been sleeping for longer than the ocean.\n"
                                 "  You woke it.\n"
                                 "  For a long time it does not speak.\n"
                                 "  It simply breathes — great slow tides of air through something vast.\n"
                                 "  Finally, in a voice that is the sound of pressure:\n"
                                 "  \"The last one who reached me came eleven thousand years ago.\n"
                                 "  They did not win.\n"
                                 "  But they made it interesting.\n"
                                 "  Let us see if you can match that.\"",

        'The Drowned Eternal':   "It does not move when you enter.\n"
                                 "  It has been still so long that coral has grown\n"
                                 "  over its shoulders and through its hair.\n"
                                 "  Then it speaks.\n\n"
                                 "  \"I knew you were coming.\"\n\n"
                                 "  The water in the room moves toward it. Not a current — a decision.\n\n"
                                 "  \"Every adventurer who descended into the Drowned Kingdom —\n"
                                 "  every one, across every run, across every version of this place —\n"
                                 "  was walking here. To this room. To me.\n"
                                 "  They didn't know it. Neither did you.\n\n"
                                 "  But I did.\n"
                                 "  I have been waiting for specifically you\n"
                                 "  for longer than you have been alive.\"\n\n"
                                 "  It finally moves. The coral cracks. The room fills.\n\n"
                                 "  \"The flood is not a punishment.\n"
                                 "  It is a homecoming.\n"
                                 "  Let me show you.\"",

        # ── THE ASHEN WASTES ─────────────────────────────────────
        'The Cinder King':       "The flames lean toward it.\n"
                                 "  Not away — toward.\n"
                                 "  As if the fire in this place has a king, and the king has arrived.\n"
                                 "  \"You came through my wastes,\" it says.\n"
                                 "  \"Everything that entered my wastes burned.\n"
                                 "  You will observe that tradition.\"",

        'The Pyre Lord':         "The pyre was built before you arrived.\n"
                                 "  Exactly your size.\n"
                                 "  \"I plan ahead,\" the Pyre Lord says.\n"
                                 "  It sounds almost proud.",

        'The Char Warden':       "\"How many warnings did you pass?\"\n"
                                 "  It gestures at the scorched stone, the burned-out rooms, the ash.\n"
                                 "  \"All of that was a warning.\n"
                                 "  Every step you took was a warning.\n"
                                 "  You are remarkably bad at taking warnings.\"",

        'The Slag Queen':        "She emerges from the floor. Slowly. Without urgency.\n"
                                 "  The magma runs off her like water.\n"
                                 "  \"I respect persistence,\" she says.\n"
                                 "  \"I respect it the way fire respects wood.\n"
                                 "  Thoroughly. Finally.\"",

        'The Infernal Titan':    "It is tall enough that its head is in the ceiling.\n"
                                 "  The ceiling has accommodated this.\n"
                                 "  \"The wave comes,\" it says. \"It always comes.\n"
                                 "  You can stand in front of it or behind it.\n"
                                 "  There is nowhere else.\"",

        'The Ash God':           "Everything in the room has already burned.\n"
                                 "  Including, it seems, the air.\n"
                                 "  The Ash God speaks from inside the incineration:\n"
                                 "  \"This place was a forest once. Then a city. Then a kingdom.\n"
                                 "  Then ash. Then god.\n"
                                 "  You will follow the same progression. Faster.\"",

        'The Burning Prince':    "\"My father burned everything he touched.\"\n"
                                 "  The crown is made of something that was bone once.\n"
                                 "  \"I burned everything he missed.\n"
                                 "  There was not much. But there was you.\n"
                                 "  There has always been, eventually, you.\"",

        'The Last Conflagration':"It is not a creature exactly.\n"
                                 "  It is the fire at the end of things, given just enough shape to fight.\n"
                                 "  When it speaks, the words are heat:\n"
                                 "  \"This is not destruction. This is succession.\n"
                                 "  Everything that was here before made room for this.\n"
                                 "  You will make room too.\"",

        'The Eternal Pyre':      "The eyes are made of the oldest flame.\n"
                                 "  Before fire had names. Before fire had uses.\n"
                                 "  Before anything was warm enough to burn.\n"
                                 "  \"I was burning,\" it says,\n"
                                 "  \"before you understood warmth.\n"
                                 "  I will be burning after you understand nothing.\"",

        'The First Fire':        "It does not look like fire.\n"
                                 "  It looks like the memory of fire — the moment before the first spark.\n"
                                 "  The potential of burning, given form.\n\n"
                                 "  \"I remember you,\" it says.\n\n"
                                 "  This makes no sense. You have never been here.\n\n"
                                 "  \"Not you specifically. But you. Your kind.\n"
                                 "  The ones who climbed down and climbed down and climbed down.\n"
                                 "  Every one of you. I remember all of you.\n"
                                 "  You are all the same person to me. The person who found me.\n\n"
                                 "  I have been waiting since I was invented.\n"
                                 "  Since that first moment — the first heat, the first light,\n"
                                 "  the first terrible beautiful consuming thing —\n"
                                 "  I have been waiting for someone worth burning for.\n\n"
                                 "  Is it you?\"\n\n"
                                 "  The room brightens.\n\n"
                                 "  \"Let's find out.\"",

        # ── THE MECHANICAL DEPTHS ────────────────────────────────
        'The First Foreman':     "\"You are not supposed to be here.\"\n"
                                 "  It checks something — a manifest, perhaps.\n"
                                 "  \"You are not on the manifest.\n"
                                 "  This is a significant operational irregularity.\n"
                                 "  I am going to resolve it.\"",

        'The Iron Warden':       "The assembly line continues behind it.\n"
                                 "  It doesn't turn to look at you.\n"
                                 "  \"Unauthorised entity detected,\" it says, in a voice like a gear catching.\n"
                                 "  \"Initiating removal protocol.\n"
                                 "  This will not take long.\"",

        'The Brass Overlord':    "It disassembles from the walls.\n"
                                 "  Panel by panel, gear by gear, until a figure stands where the wall was.\n"
                                 "  \"The Brass Overlord oversees all operations in this facility,\" it says.\n"
                                 "  \"Your operation is not sanctioned.\n"
                                 "  Prepare to be disassembled.\"",

        'The Clock King':        "The ticking stops.\n"
                                 "  Every clock, every gear, every pendulum — stops.\n"
                                 "  \"Time,\" says the Clock King, in a voice like a mainspring releasing,\n"
                                 "  \"is mine.\n"
                                 "  I stopped it once to make a point.\n"
                                 "  I can stop other things for the same reason.\"",

        'The Steam Titan':       "The pressure gauge on its chest is in the red.\n"
                                 "  Has been in the red for years.\n"
                                 "  \"VENTING,\" it says. \"COMBAT PROTOCOL: ENGAGED.\n"
                                 "  OUTCOME: PREDETERMINED.\"\n"
                                 "  The gauge does not move into safe territory.\n"
                                 "  There is no safe territory here.",

        'The Gear God':          "Every gear in the cathedral begins to move.\n"
                                 "  In sequence. In perfect harmony.\n"
                                 "  The Gear God stands at the centre of it.\n"
                                 "  \"You have witnessed the principle of motion,\" it says.\n"
                                 "  \"You are about to become part of it.\n"
                                 "  This is an honour. You did not earn it. You receive it anyway.\"",

        'The Iron Prince':       "It raises one hand. The automatons in the court stop moving.\n"
                                 "  \"My father built this place,\" the Iron Prince says.\n"
                                 "  \"My mother was the concept of efficiency.\n"
                                 "  I was designed for this moment specifically —\n"
                                 "  the moment someone reached the court who shouldn't.\n"
                                 "  Here you are. And here I am.\n"
                                 "  The design is sound.\"",

        'The Grand Mechanism':   "The gears are the size of houses.\n"
                                 "  When it turns its attention to you, everything moves.\n"
                                 "  \"I am the Grand Mechanism,\" it says — both name and statement.\n"
                                 "  \"This dungeon runs because I run. The enemies move because I move.\n"
                                 "  Everything in these Depths exists to serve the Mechanism.\n"
                                 "  You have reached the Mechanism.\n"
                                 "  The Mechanism will now determine your function.\"",

        'The Eternal Engine':    "It was built to run forever. And it has.\n"
                                 "  The heat coming off it is not incidental — it is structural.\n"
                                 "  \"All that power,\" it says, in a voice like a turbine winding up,\n"
                                 "  \"and you reached me. Efficient. I respect that.\n"
                                 "  Now let me show you what efficiency looks like\n"
                                 "  when it is applied to the task of stopping you.\"",

        'The Prime Constructor': "The blueprints are everywhere.\n"
                                 "  Every surface — floor, walls, ceiling — covered.\n"
                                 "  Your blueprint is on the wall opposite the door.\n"
                                 "  It has been there since before you were born.\n\n"
                                 "  The Prime Constructor is reviewing it.\n\n"
                                 "  \"Standard architecture,\" it says, without looking up.\n"
                                 "  \"Nothing surprising here. I've seen this design before.\"\n"
                                 "  A gear turns somewhere deep inside it.\n"
                                 "  \"The previous models were also confident.\"\n\n"
                                 "  It finally looks up. Its eyes are compasses, pointing at you.\n\n"
                                 "  \"I have built everything in these Depths.\n"
                                 "  Every trap. Every enemy. Every floor.\n"
                                 "  I did not build you.\n"
                                 "  This is the one variable I cannot calculate.\n\n"
                                 "  It interests me.\n\n"
                                 "  Let us see how you perform against the Final Blueprint.\n"
                                 "  I will be taking notes.\"",

        # ── THE PLAGUE CATHEDRAL ─────────────────────────────────
        'The First Abbot':       "\"Welcome, child.\"\n"
                                 "  The warmth in its voice is not metaphorical.\n"
                                 "  It radiates something. Something contagious.\n"
                                 "  \"The Cathedral accepts all who come in faith.\n"
                                 "  You came in something other than faith.\n"
                                 "  We will correct that.\"",

        'The Plague Bishop':     "It has been kneeling at the altar when you arrive.\n"
                                 "  It stands slowly. With great dignity.\n"
                                 "  \"This is a place of worship,\" it says.\n"
                                 "  \"I will ask you to show appropriate reverence.\n"
                                 "  The reverence the Cathedral prefers\n"
                                 "  is not something you will survive.\"",

        'The Blight Cardinal':   "\"Every name on these walls,\" it says,\n"
                                 "  gesturing at the carved stone,\n"
                                 "  \"was a visitor like you. They were blessed.\n"
                                 "  They became part of something larger than themselves.\n"
                                 "  I offer you the same honour.\n"
                                 "  It is more honour than you deserve.\"",

        'The Rot Archon':        "The velvet is no longer recognisable as velvet.\n"
                                 "  Neither is the Archon entirely recognisable as human.\n"
                                 "  \"The rot is not corruption,\" it says. \"The rot is completion.\n"
                                 "  Everything returns to this. Eventually.\n"
                                 "  I merely accelerate the timeline.\"",

        'The Plague Titan':      "It walks down the aisle slowly.\n"
                                 "  The pews rot where it passes.\n"
                                 "  \"The Titan is the Cathedral's fist,\" it says.\n"
                                 "  \"The Cathedral has been patient for long enough.\n"
                                 "  You have been patient long enough.\n"
                                 "  Let us end patience together.\"",

        'The Cathedral God':     "\"Sit down.\"\n"
                                 "  The pews are full. They have been full for centuries.\n"
                                 "  \"I have been delivering this sermon,\" the Cathedral God says,\n"
                                 "  \"since before the language it was written in existed.\n"
                                 "  You will hear it.\n"
                                 "  Then you will become part of the congregation. Permanently.\"",

        'The Plague Prince':     "It is beautiful.\n"
                                 "  This is the first thing you notice and you cannot stop noticing it.\n"
                                 "  The second thing you notice is that the beauty is wrong.\n"
                                 "  Wrong the way a flower growing through a skull is wrong.\n"
                                 "  \"My congregation is devoted,\" the Plague Prince says.\n"
                                 "  \"They gave me everything.\n"
                                 "  Would you like to receive my sacrament in return?\"",

        'The High Inquisitor':   "The case file is open. Your case file.\n"
                                 "  \"I have been investigating this case,\" it says,\n"
                                 "  \"since before you arrived.\n"
                                 "  The evidence is thorough. The verdict is decided.\n"
                                 "  We are now at the sentencing phase.\"\n"
                                 "  It closes the file.\n"
                                 "  \"I find the defendant guilty of continued existence\n"
                                 "  without sanctioned purpose.\n"
                                 "  The sentence is consistent with all previous sentences.\"",

        'The Plague Saint':      "Its eyes are full of faith. Not metaphorically.\n"
                                 "  The faith in its eyes is a substance.\n"
                                 "  \"The Saint died for this,\" it says.\n"
                                 "  \"For this place. For this sacrament.\n"
                                 "  For the miracle the Cathedral performs on every living thing\n"
                                 "  that passes through its doors.\"\n"
                                 "  Its hands are folded. This does not make them less dangerous.",

        'The Eternal Pestilence':"The altar is warm.\n"
                                 "  It has been warm since the first prayer was said here.\n"
                                 "  The first prayer was said a very long time ago.\n\n"
                                 "  The Eternal Pestilence stands behind it.\n"
                                 "  It has always stood behind it.\n\n"
                                 "  \"You have made an offering,\" it says.\n"
                                 "  \"The offering of your continued existence.\n"
                                 "  The Cathedral accepts.\"\n\n"
                                 "  It spreads its hands in benediction.\n\n"
                                 "  \"I have spread across every kingdom that tried to contain me.\n"
                                 "  Every physician who treated me. Every fire that tried to burn me out.\n"
                                 "  I was here before the Cathedral. The Cathedral was built around me.\n"
                                 "  I am the reason this place was built.\n"
                                 "  I am the reason anything in here was built.\n\n"
                                 "  And you walked through all of it.\n"
                                 "  Through my children and my disciples and my architecture.\n"
                                 "  You reached me.\"\n\n"
                                 "  The warmth of the altar intensifies.\n\n"
                                 "  \"I accept your offering.\n"
                                 "  Now let me give you mine.\n"
                                 "  In the name of everything this Cathedral has ever asked of the faithful:\n"
                                 "  kneel.\"",
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
