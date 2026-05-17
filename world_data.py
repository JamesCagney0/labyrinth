"""LABYRINTH — NG+ worlds and fusion class definitions"""
from __future__ import annotations
import random, json, os, logging
from typing import Dict, List, Optional, Set, Tuple, Any, TYPE_CHECKING, Callable
from difflib import get_close_matches
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class WorldData:
    """NG+ world and fusion constants. Imported into GameConstants."""

    FUSION_CLASSES = {
        ('warrior', 'mage'): {
            'name': 'Spellblade',
            'description': 'Physical might fused with arcane power. Strikes can trigger free magic procs.',
            'weapon_types': ['melee', 'magic'],
            'stat_bonus': {'strength': 8, 'intelligence': 8, 'agility': 3, 'luck': 2, 'vitality': 5, 'arcane': 5, 'faith': 0},
            'passive': 'arcane_strike',
            'boss_ability': 'spellblade_surge',
            'boss_ability_name': 'Spellblade Surge',
            'health_per_level': 12,
        },
        ('warrior', 'rogue'): {
            'name': 'Warlord Assassin',
            'description': 'Killing blows restore 15% HP. Can strike twice in one boss turn.',
            'weapon_types': ['melee', 'stealth'],
            'stat_bonus': {'strength': 6, 'intelligence': 1, 'agility': 8, 'luck': 6, 'vitality': 4, 'arcane': 0, 'faith': 0},
            'passive': 'execute_restore',
            'boss_ability': 'blitz_strike',
            'boss_ability_name': 'Blitz Strike',
            'health_per_level': 13,
        },
        ('warrior', 'paladin'): {
            'name': 'Templar',
            'description': 'Holy weapons gain berserker HP-scaling on top of holy aura. Wrath for a massive combined hit.',
            'weapon_types': ['melee'],
            'stat_bonus': {'strength': 7, 'intelligence': 3, 'agility': 2, 'luck': 2, 'vitality': 8, 'arcane': 0, 'faith': 8},
            'passive': 'battle_blessing',
            'boss_ability': 'wrath',
            'boss_ability_name': 'Wrath',
            'health_per_level': 15,
        },
        ('warrior', 'berserker'): {
            'name': 'War Incarnate',
            'description': 'Double berserker HP-scaling. Highest raw damage floor in the game.',
            'weapon_types': ['melee'],
            'stat_bonus': {'strength': 12, 'intelligence': 0, 'agility': 2, 'luck': 1, 'vitality': 10, 'arcane': 0, 'faith': 0},
            'passive': 'double_rage',
            'boss_ability': 'total_war',
            'boss_ability_name': 'Total War',
            'health_per_level': 17,
        },
        ('warrior', 'void_walker'): {
            'name': 'Null Knight',
            'description': 'Phase available once per fight. Heavy hits gain +20% crit chance.',
            'weapon_types': ['melee', 'stealth'],
            'stat_bonus': {'strength': 7, 'intelligence': 2, 'agility': 8, 'luck': 6, 'vitality': 6, 'arcane': 0, 'faith': 0},
            'passive': 'null_weight',
            'boss_ability': 'void_strike',
            'boss_ability_name': 'Void Strike',
            'health_per_level': 12,
        },
        ('mage', 'rogue'): {
            'name': 'Arcane Shadow',
            'description': 'Crits restore 15 MP. Shadow Spell is a guaranteed-crit magic attack.',
            'weapon_types': ['magic', 'stealth'],
            'stat_bonus': {'strength': 1, 'intelligence': 8, 'agility': 8, 'luck': 8, 'vitality': 2, 'arcane': 6, 'faith': 0},
            'passive': 'crit_mana',
            'boss_ability': 'shadow_spell',
            'boss_ability_name': 'Shadow Spell',
            'health_per_level': 9,
        },
        ('mage', 'paladin'): {
            'name': 'Holy Arcanist',
            'description': 'Magic attacks carry holy aura damage vs undead and demons.',
            'weapon_types': ['magic', 'melee'],
            'stat_bonus': {'strength': 2, 'intelligence': 8, 'agility': 2, 'luck': 3, 'vitality': 4, 'arcane': 8, 'faith': 8},
            'passive': 'holy_magic',
            'boss_ability': 'divine_blaze',
            'boss_ability_name': 'Divine Blaze',
            'health_per_level': 10,
        },
        ('mage', 'berserker'): {
            'name': 'Chaos Mage',
            'description': 'Magic damage scales with missing HP like Berserker rage. Chaos Eruption deals massive damage at a cost.',
            'weapon_types': ['magic'],
            'stat_bonus': {'strength': 5, 'intelligence': 10, 'agility': 2, 'luck': 2, 'vitality': 4, 'arcane': 8, 'faith': 0},
            'passive': 'chaos_scaling',
            'boss_ability': 'chaos_eruption',
            'boss_ability_name': 'Chaos Eruption',
            'health_per_level': 11,
        },
        ('mage', 'void_walker'): {
            'name': 'Reality Sorcerer',
            'description': 'Magic turns skip enemy retaliation (Phase Spell). Crits deal 2.5x.',
            'weapon_types': ['magic'],
            'stat_bonus': {'strength': 0, 'intelligence': 10, 'agility': 8, 'luck': 8, 'vitality': 2, 'arcane': 10, 'faith': 0},
            'passive': 'void_resonance',
            'boss_ability': 'phase_spell',
            'boss_ability_name': 'Phase Spell',
            'health_per_level': 9,
        },
        ('rogue', 'paladin'): {
            'name': 'Shadow Knight',
            'description': 'Holy backstab stacks Executioner and Holy Aura simultaneously.',
            'weapon_types': ['stealth', 'melee'],
            'stat_bonus': {'strength': 4, 'intelligence': 2, 'agility': 8, 'luck': 8, 'vitality': 4, 'arcane': 0, 'faith': 6},
            'passive': 'holy_crit',
            'boss_ability': 'holy_backstab',
            'boss_ability_name': 'Holy Backstab',
            'health_per_level': 12,
        },
        ('rogue', 'berserker'): {
            'name': 'Blood Dancer',
            'description': 'Crits trigger the Berserker rage bonus. Triple-hit Frenzy ability.',
            'weapon_types': ['stealth', 'melee'],
            'stat_bonus': {'strength': 6, 'intelligence': 1, 'agility': 10, 'luck': 8, 'vitality': 4, 'arcane': 0, 'faith': 0},
            'passive': 'blood_frenzy',
            'boss_ability': 'frenzy',
            'boss_ability_name': 'Frenzy',
            'health_per_level': 13,
        },
        ('rogue', 'void_walker'): {
            'name': 'Void Phantom',
            'description': 'Highest crit chance in the game. Vanish Strike: Phase then deal a free attack.',
            'weapon_types': ['stealth'],
            'stat_bonus': {'strength': 2, 'intelligence': 4, 'agility': 12, 'luck': 12, 'vitality': 2, 'arcane': 0, 'faith': 0},
            'passive': 'phantom_crit',
            'boss_ability': 'vanish_strike',
            'boss_ability_name': 'Vanish Strike',
            'health_per_level': 9,
        },
        ('paladin', 'berserker'): {
            'name': 'Zealot',
            'description': 'Rage amplifies Holy Aura bonus. The more rage, the holier the fury.',
            'weapon_types': ['melee'],
            'stat_bonus': {'strength': 8, 'intelligence': 2, 'agility': 2, 'luck': 2, 'vitality': 10, 'arcane': 0, 'faith': 8},
            'passive': 'holy_rage',
            'boss_ability': 'divine_fury',
            'boss_ability_name': 'Divine Fury',
            'health_per_level': 15,
        },
        ('paladin', 'void_walker'): {
            'name': 'Void Saint',
            'description': 'Phase extends to 2 uses per fight. Null Smite bypasses enemy defense.',
            'weapon_types': ['melee', 'stealth'],
            'stat_bonus': {'strength': 4, 'intelligence': 4, 'agility': 8, 'luck': 6, 'vitality': 6, 'arcane': 0, 'faith': 8},
            'passive': 'dual_phase',
            'boss_ability': 'null_smite',
            'boss_ability_name': 'Null Smite',
            'health_per_level': 11,
        },
        ('berserker', 'void_walker'): {
            'name': 'Void Berserker',
            'description': 'Rage and Phase combine. Void Rage uses both in one action, then attacks.',
            'weapon_types': ['melee', 'stealth'],
            'stat_bonus': {'strength': 10, 'intelligence': 2, 'agility': 8, 'luck': 4, 'vitality': 8, 'arcane': 0, 'faith': 0},
            'passive': 'void_rage_passive',
            'boss_ability': 'void_rage',
            'boss_ability_name': 'Void Rage',
            'health_per_level': 15,
        },
    }


    # ── Fusion class tier names ───────────────────────────────────
    # Fused classes can be upgraded from tier 5 through tier 10.
    # Tier 5 is the base fusion name. Tiers 6-10 are prestige titles.

    FUSION_CLASS_NAMES: Dict[str, Dict[int, str]] = {
        'spellblade': {
            5: 'Spellblade',      6: 'Runic Blade',
            7: 'Arcanist Knight', 8: 'Spell Reaver',
            9: 'Arcane Destroyer',10: 'Mythic Spellblade',
        },
        'warlord assassin': {
            5: 'Warlord Assassin', 6: 'Blade General',
            7: 'Shadow Warlord',   8: 'Death Commander',
            9: 'Siege Phantom',   10: 'Mythic Warlord',
        },
        'templar': {
            5: 'Templar',       6: 'Holy Crusader',
            7: 'Divine Templar',8: 'Sacred Bulwark',
            9: "God's Sword",  10: 'Mythic Templar',
        },
        'war incarnate': {
            5: 'War Incarnate', 6: 'Warchief',
            7: 'Iron Tyrant',   8: 'Unstoppable Force',
            9: 'Avatar of War', 10: 'Mythic Incarnate',
        },
        'null knight': {
            5: 'Null Knight',    6: 'Void Sentinel',
            7: 'Phase Warden',   8: 'Null Templar',
            9: 'Reality Guard',  10: 'Mythic Null Knight',
        },
        'arcane shadow': {
            5: 'Arcane Shadow',  6: 'Mana Thief',
            7: 'Spell Shade',    8: 'Arcane Revenant',
            9: 'Void Trickster', 10: 'Mythic Arcane Shadow',
        },
        'holy arcanist': {
            5: 'Holy Arcanist',   6: 'Sacred Caster',
            7: 'Divine Scholar',  8: 'Holy Conjurer',
            9: 'Archangel Mage',  10: 'Mythic Holy Arcanist',
        },
        'chaos mage': {
            5: 'Chaos Mage',    6: 'Entropy Caster',
            7: 'Ruin Mage',     8: 'Chaos Incarnate',
            9: 'Mad Archmage',  10: 'Mythic Chaos Mage',
        },
        'reality sorcerer': {
            5: 'Reality Sorcerer', 6: 'Void Conjurer',
            7: 'Phase Mage',       8: 'Reality Shaper',
            9: 'Dimension Lord',   10: 'Mythic Reality Sorcerer',
        },
        'shadow knight': {
            5: 'Shadow Knight',  6: 'Dark Crusader',
            7: 'Blessed Shadow', 8: 'Holy Phantom',
            9: 'Divine Shade',   10: 'Mythic Shadow Knight',
        },
        'blood dancer': {
            5: 'Blood Dancer',  6: 'Frenzy Blade',
            7: 'Gore Dancer',   8: 'Crimson Reaper',
            9: 'Blood Tyrant',  10: 'Mythic Blood Dancer',
        },
        'void phantom': {
            5: 'Void Phantom',   6: 'Null Shade',
            7: 'Phase Stalker',  8: 'Void Revenant',
            9: 'Phantom Sovereign',10: 'Mythic Void Phantom',
        },
        'zealot': {
            5: 'Zealot',         6: 'Rage Saint',
            7: 'Holy Berserker', 8: 'Divine Fury',
            9: "God's Wrath",   10: 'Mythic Zealot',
        },
        'void saint': {
            5: 'Void Saint',     6: 'Null Paladin',
            7: 'Phase Herald',   8: 'Void Crusader',
            9: 'Divine Phantom', 10: 'Mythic Void Saint',
        },
        'void berserker': {
            5: 'Void Berserker', 6: 'Null Rager',
            7: 'Phase Titan',    8: 'Void Destroyer',
            9: 'Chaos Void',     10: 'Mythic Void Berserker',
        },
    }

    # Levels required for fusion tier upgrades (tiers 6-10)

    FUSION_UPGRADE_LEVELS: Dict[int, int] = {
        6: 20, 7: 25, 8: 30, 9: 35, 10: 40,
    }

    # Stat bonus granted on each fusion tier upgrade
    FUSION_TIER_STAT_BONUS: int = 8

    NG_PLUS_WORLDS = {

        # ── 1. THE FRACTURED LABYRINTH ────────────────────────────
        'fractured_labyrinth': {
            'display_name': 'The Fractured Labyrinth',
            'wake_text': (
                "The dungeon is wrong.\n"
                "Not the dungeon you descended. Not the Labyrinth you survived.\n"
                "Something older. Something that was underneath it.\n\n"
                "The walls are fractured. The geometry is broken.\n"
                "The enemies here have never seen sunlight\n"
                "— they've never seen anything that still exists."
            ),
            'enemies': {
                'fracture imp':       {'health': 85,  'damage': 35, 'exp':  60, 'desc': 'A glitching imp with reality-distorted limbs'},
                'void rat':           {'health': 70,  'damage': 30, 'exp':  50, 'desc': 'A massive rat whose fur phases in and out of existence'},
                'corrupted soldier':  {'health': 140, 'damage': 48, 'exp':  90, 'desc': 'A soldier whose armor is fused to his corroded body'},
                'mirror skeleton':    {'health': 120, 'damage': 55, 'exp': 100, 'desc': 'A skeleton that reflects your own fighting style back at you'},
                'null knight':        {'health': 175, 'damage': 62, 'exp': 130, 'desc': 'A knight made of compressed absence'},
                'echo wraith':        {'health': 160, 'damage': 70, 'exp': 145, 'desc': 'A wraith that screams in a voice you recognise as your own'},
                'void mage':          {'health': 130, 'damage': 78, 'exp': 155, 'desc': 'A mage who draws power from the spaces between realities'},
                'flesh horror':       {'health': 190, 'damage': 58, 'exp': 140, 'desc': 'A mass of wrong-angled meat that moves against gravity'},
                'plasma elemental':   {'health': 200, 'damage': 75, 'exp': 175, 'desc': 'An elemental born from collapsed dimensions'},
                'crystal wraith':     {'health': 185, 'damage': 68, 'exp': 165, 'desc': 'A wraith crystallised mid-scream, still screaming'},
                'storm titan':        {'health': 160, 'damage': 85, 'exp': 185, 'desc': 'A titan of living lightning, fractured across a dozen bodies'},
                'void golem':         {'health': 260, 'damage': 65, 'exp': 160, 'desc': 'A golem of solidified void-matter'},
                'fracture demon':     {'health': 220, 'damage': 90, 'exp': 200, 'desc': 'A demon from the wrong dimension, furious about it'},
                'null cultist':       {'health': 195, 'damage': 82, 'exp': 190, 'desc': 'A cultist who contacted the void and survived'},
                'shadow devourer':    {'health': 240, 'damage': 95, 'exp': 215, 'desc': 'A predator that eats shadows and leaves nothing'},
                'entropy spawn':      {'health': 255, 'damage': 100,'exp': 225, 'desc': 'Born from pure entropy — the end of all things, walking'},
                'void titan':         {'health': 300, 'damage': 88, 'exp': 240, 'desc': 'A primordial titan fully consumed by the void'},
                'fractured celestial':{'health': 280, 'damage': 105,'exp': 260, 'desc': 'A celestial knight whose divinity has been inverted'},
                'null guardian':      {'health': 320, 'damage': 92, 'exp': 255, 'desc': 'The guardian of a place that no longer exists'},
            },
            'floor_themes': {
                1:  ['fracture imp', 'void rat', 'corrupted soldier'],
                2:  ['corrupted soldier', 'mirror skeleton', 'fracture imp'],
                3:  ['mirror skeleton', 'null knight', 'echo wraith'],
                4:  ['echo wraith', 'void mage', 'null knight'],
                5:  ['plasma elemental', 'crystal wraith', 'storm titan'],
                6:  ['storm titan', 'void golem', 'plasma elemental'],
                7:  ['fracture demon', 'null cultist', 'shadow devourer'],
                8:  ['shadow devourer', 'entropy spawn', 'fracture demon'],
                9:  ['void titan', 'fractured celestial', 'null guardian'],
                10: ['null guardian', 'void titan', 'fractured celestial'],
            },
            'boss_data': {
                1:  {'name': 'The Glitch',            'special': 'REALITY STUTTER',    'base_health': 380,  'health_scaling': 22, 'damage': 55,  'exp_reward': 400,  'special_bonus': 35, 'stat_bonus': 4, 'min_level': 4},
                2:  {'name': 'The Undying Architect', 'special': 'VOID CONSTRUCTION',  'base_health': 460,  'health_scaling': 25, 'damage': 62,  'exp_reward': 480,  'special_bonus': 40, 'stat_bonus': 4, 'min_level': 6},
                3:  {'name': 'The Hollow King',       'special': 'EMPTINESS WAVE',     'base_health': 540,  'health_scaling': 28, 'damage': 70,  'exp_reward': 560,  'special_bonus': 46, 'stat_bonus': 5, 'min_level': 8},
                4:  {'name': 'The Shadow Itself',     'special': 'ABSOLUTE DARKNESS',  'base_health': 620,  'health_scaling': 31, 'damage': 78,  'exp_reward': 640,  'special_bonus': 52, 'stat_bonus': 5, 'min_level': 10},
                5:  {'name': 'The Infernal Echo',     'special': 'RECURSIVE INFERNO',  'base_health': 720,  'health_scaling': 34, 'damage': 86,  'exp_reward': 720,  'special_bonus': 58, 'stat_bonus': 6, 'min_level': 12},
                6:  {'name': 'Absolute Zero',         'special': 'HEAT DEATH',         'base_health': 820,  'health_scaling': 37, 'damage': 95,  'exp_reward': 820,  'special_bonus': 65, 'stat_bonus': 6, 'min_level': 14},
                7:  {'name': 'The Void Prince',       'special': 'ANNIHILATION FIELD', 'base_health': 940,  'health_scaling': 40, 'damage': 105, 'exp_reward': 940,  'special_bonus': 72, 'stat_bonus': 7, 'min_level': 16},
                8:  {'name': 'The Fracture God',      'special': 'DIMENSIONAL SPLIT',  'base_health': 1080, 'health_scaling': 44, 'damage': 115, 'exp_reward': 1080, 'special_bonus': 80, 'stat_bonus': 7, 'min_level': 18},
                9:  {'name': 'The First Beast',       'special': 'PRIMORDIAL SCREAM',  'base_health': 1240, 'health_scaling': 48, 'damage': 128, 'exp_reward': 1240, 'special_bonus': 90, 'stat_bonus': 8, 'min_level': 20},
                10: {'name': 'The Origin Breaker',    'special': 'ERASURE',            'base_health': 1500, 'health_scaling': 55, 'damage': 145, 'exp_reward': 1500, 'special_bonus': 105,'stat_bonus': 10,'min_level': 22},
            },
            'boss_rooms': {
                1:  ("The Glitch Arena",     "The arena flickers between states of existence.",         "The Glitch manifests from a cascade of corrupted reality."),
                2:  ("The Architect's Ruin", "A structure built and unbuilt simultaneously.",           "The Undying Architect assembles itself from broken geometry."),
                3:  ("The Empty Throne",     "A throne room with no throne, no walls, no floor.",       "The Hollow King rises from the nothing it has always been."),
                4:  ("The Darkness Itself",  "Darkness, made into a room.",                             "The Shadow Itself detaches from every shadow and converges here."),
                5:  ("The Recursive Furnace","A furnace that burns its own heat, forever.",             "The Infernal Echo screams in a voice that has been screaming since before fire."),
                6:  ("The Cold Absolute",    "So cold that entropy itself has slowed. Almost stopped.", "Absolute Zero crystallises from the fundamental temperature of death."),
                7:  ("The Void Court",       "A court where nothing has standing and nothing is law.",  "The Void Prince takes its throne made of absence."),
                8:  ("The Fracture Point",   "The exact location where this reality began to break.",   "The Fracture God touches the crack it made and widens it."),
                9:  ("The First Place",      "The dungeon as it existed before the dungeon existed.",   "The First Beast opens its eyes for the first time. Again."),
                10: ("The End of the Map",   "Beyond this point the dungeon's geometry gives up.",      "The Origin Breaker stands where everything stops. It is smiling."),
            },
        },

        # ── 2. THE DROWNED KINGDOM ────────────────────────────────
        'drowned_kingdom': {
            'display_name': 'The Drowned Kingdom',
            'wake_text': (
                "The air tastes of salt and rot.\n"
                "You are still in the dungeon. But the dungeon is underwater now.\n\n"
                "Not flooded — transformed. The stone has become coral.\n"
                "The torches have become bioluminescent growths that pulse like hearts.\n\n"
                "Something vast moves in the distance.\n"
                "Something that has been waiting for someone foolish enough to descend."
            ),
            'enemies': {
                'tide crawler':      {'health': 80,  'damage': 32, 'exp':  55, 'desc': 'A crab-thing the size of a horse with eyes that glow teal'},
                'drowned soldier':   {'health': 135, 'damage': 46, 'exp':  88, 'desc': 'A soldier preserved by cold water, still following orders from a dead king'},
                'sea wraith':        {'health': 115, 'damage': 52, 'exp':  98, 'desc': 'The ghost of a sailor who forgot to surface'},
                'coral horror':      {'health': 180, 'damage': 60, 'exp': 128, 'desc': 'Coral that grew through a living body and decided it preferred this form'},
                'depth stalker':     {'health': 165, 'damage': 68, 'exp': 140, 'desc': 'Hunts by the pressure displacement of your footsteps'},
                'tide mage':         {'health': 125, 'damage': 76, 'exp': 152, 'desc': 'Commands water as a weapon and considers drowning mercy'},
                'abyssal shark':     {'health': 195, 'damage': 82, 'exp': 172, 'desc': 'Adapted to depths where light is a myth'},
                'kraken spawn':      {'health': 210, 'damage': 72, 'exp': 168, 'desc': 'A child of something much larger, still growing'},
                'current golem':     {'health': 255, 'damage': 62, 'exp': 158, 'desc': 'A golem made of concentrated ocean current'},
                'siren wraith':      {'health': 175, 'damage': 88, 'exp': 182, 'desc': 'Its song draws you closer. Do not get closer.'},
                'pressure elemental':{'health': 195, 'damage': 78, 'exp': 178, 'desc': 'Born from the pressure that crushes ships to planks'},
                'deep cultist':      {'health': 188, 'damage': 80, 'exp': 186, 'desc': 'Worships something ancient that lives in the lowest trench'},
                'tide demon':        {'health': 218, 'damage': 88, 'exp': 198, 'desc': 'A demon that crossed over through the deepest part of the sea'},
                'abyss devourer':    {'health': 238, 'damage': 93, 'exp': 212, 'desc': 'Swallows light. Swallows everything eventually.'},
                'void leviathan':    {'health': 292, 'damage': 86, 'exp': 236, 'desc': 'The skeleton of a creature that predates oceans'},
                'drowned titan':     {'health': 268, 'damage': 102,'exp': 256, 'desc': 'A titan that sank and adapted rather than die'},
                'abyssal guardian':  {'health': 312, 'damage': 90, 'exp': 252, 'desc': 'Guards the thing at the very bottom. Has never failed.'},
                'sea horror':        {'health': 245, 'damage': 97, 'exp': 220, 'desc': 'Resembles nothing that should exist'},
                'the drowned king':  {'health': 330, 'damage': 108,'exp': 270, 'desc': 'The king of this place. Still giving commands. Still being obeyed.'},
            },
            'floor_themes': {
                1:  ['tide crawler', 'drowned soldier', 'sea wraith'],
                2:  ['drowned soldier', 'coral horror', 'tide crawler'],
                3:  ['coral horror', 'depth stalker', 'sea wraith'],
                4:  ['depth stalker', 'tide mage', 'siren wraith'],
                5:  ['abyssal shark', 'kraken spawn', 'pressure elemental'],
                6:  ['current golem', 'pressure elemental', 'abyssal shark'],
                7:  ['tide demon', 'deep cultist', 'abyss devourer'],
                8:  ['abyss devourer', 'sea horror', 'tide demon'],
                9:  ['void leviathan', 'drowned titan', 'abyssal guardian'],
                10: ['abyssal guardian', 'the drowned king', 'void leviathan'],
            },
            'boss_data': {
                1:  {'name': 'The Tide Warden',     'special': 'RIPTIDE',           'base_health': 370,  'health_scaling': 21, 'damage': 53,  'exp_reward': 390,  'special_bonus': 34, 'stat_bonus': 4, 'min_level': 4},
                2:  {'name': 'The Drowned Admiral', 'special': 'DEAD FLEET',        'base_health': 448,  'health_scaling': 24, 'damage': 61,  'exp_reward': 472,  'special_bonus': 39, 'stat_bonus': 4, 'min_level': 6},
                3:  {'name': 'The Coral Throne',    'special': 'REEF CRUSH',        'base_health': 528,  'health_scaling': 27, 'damage': 69,  'exp_reward': 552,  'special_bonus': 45, 'stat_bonus': 5, 'min_level': 8},
                4:  {'name': 'The Siren Queen',     'special': 'DEATH SONG',        'base_health': 610,  'health_scaling': 30, 'damage': 77,  'exp_reward': 630,  'special_bonus': 51, 'stat_bonus': 5, 'min_level': 10},
                5:  {'name': 'The Pressure God',    'special': 'DEEP CRUSH',        'base_health': 708,  'health_scaling': 33, 'damage': 85,  'exp_reward': 710,  'special_bonus': 57, 'stat_bonus': 6, 'min_level': 12},
                6:  {'name': 'The Abyssal Duke',    'special': 'TRENCH SURGE',      'base_health': 808,  'health_scaling': 36, 'damage': 94,  'exp_reward': 810,  'special_bonus': 64, 'stat_bonus': 6, 'min_level': 14},
                7:  {'name': 'The Leviathan Prince','special': 'WORLD SWALLOW',     'base_health': 928,  'health_scaling': 39, 'damage': 104, 'exp_reward': 930,  'special_bonus': 71, 'stat_bonus': 7, 'min_level': 16},
                8:  {'name': 'The Sunken God',      'special': 'TIDAL OBLITERATION','base_health': 1068, 'health_scaling': 43, 'damage': 114, 'exp_reward': 1070, 'special_bonus': 79, 'stat_bonus': 7, 'min_level': 18},
                9:  {'name': 'The Deep Ancient',    'special': 'VOID TIDE',         'base_health': 1228, 'health_scaling': 47, 'damage': 127, 'exp_reward': 1230, 'special_bonus': 89, 'stat_bonus': 8, 'min_level': 20},
                10: {'name': 'The Drowned Eternal', 'special': 'THE FINAL FLOOD',   'base_health': 1488, 'health_scaling': 54, 'damage': 144, 'exp_reward': 1490, 'special_bonus': 104,'stat_bonus': 10,'min_level': 22},
            },
            'boss_rooms': {
                1:  ("The Flooded Gate",       "Seawater pours from the walls in sheets.",              "The Tide Warden rises from the flood."),
                2:  ("The Drowned Bridge",     "A stone bridge over a drop into absolute black water.",  "The Drowned Admiral's fleet materialises from the depths."),
                3:  ("The Coral Throne Room",  "Coral has grown over everything including the throne.",  "The Coral Throne animates."),
                4:  ("The Siren's Grotto",     "Beautiful. The air makes you want to stay.",            "The Siren Queen opens her mouth. Don't listen."),
                5:  ("The Pressure Chamber",   "The walls groan under the weight of miles of water.",   "The Pressure God solidifies from the force itself."),
                6:  ("The Abyssal Court",      "A court that functions two miles underwater.",           "The Abyssal Duke takes its position."),
                7:  ("The Leviathan's Grave",  "The skeleton of something that ate continents.",         "The Leviathan Prince crawls out of its ancestor's ribs."),
                8:  ("The Sunken Temple",      "A place of worship for something that lives below all.", "The Sunken God opens its eyes. They are very large."),
                9:  ("The Ancient Trench",     "The oldest part of any ocean, on any world.",            "The Deep Ancient has been sleeping here since before this planet had water."),
                10: ("The Drowned Everything", "This is not a room. This is the end of dry things.",     "The Drowned Eternal was waiting for you specifically."),
            },
        },

        # ── 3. THE ASHEN WASTES ───────────────────────────────────
        'ashen_wastes': {
            'display_name': 'The Ashen Wastes',
            'wake_text': (
                "The air is wrong. Not thin — consumed.\n"
                "Everything that was here before has burned.\n\n"
                "The stone walls are still warm. Not recently warm — permanently warm.\n"
                "Something burned this place so completely it left a scar in time.\n\n"
                "You are standing in the scar.\n\n"
                "The things that live here weren't born here.\n"
                "They were forged here."
            ),
            'enemies': {
                'ash walker':        {'health': 78,  'damage': 33, 'exp':  54, 'desc': 'Held together by char and something that refuses to let it rest'},
                'cinder hound':      {'health': 95,  'damage': 42, 'exp':  70, 'desc': 'Runs on burning paws, leaves scorched prints on stone'},
                'ember knight':      {'health': 145, 'damage': 50, 'exp':  92, 'desc': 'A knight whose armour melted and resolidified around them'},
                'soot wraith':       {'health': 118, 'damage': 54, 'exp': 100, 'desc': 'A ghost made of smoke — burns you by proximity'},
                'pyro cultist':      {'health': 138, 'damage': 62, 'exp': 120, 'desc': 'Set themselves on fire first. The fire agreed it was a good idea.'},
                'lava golem':        {'health': 270, 'damage': 64, 'exp': 156, 'desc': 'Stone animated by magma in its veins'},
                'ashen titan':       {'health': 185, 'damage': 72, 'exp': 168, 'desc': 'A titan that walked through the apocalypse and came out the other side'},
                'cinder mage':       {'health': 128, 'damage': 80, 'exp': 158, 'desc': 'Casts fire from a place inside them that has never been put out'},
                'fire elemental':    {'health': 202, 'damage': 78, 'exp': 178, 'desc': 'Born from the original fire that started all of this'},
                'smoldering demon':  {'health': 225, 'damage': 88, 'exp': 196, 'desc': 'Arrived through a portal made of flame, considers this an upgrade'},
                'pyroclast spawn':   {'health': 248, 'damage': 98, 'exp': 220, 'desc': 'A volcanic eruption given legs and a grievance'},
                'slag guardian':     {'health': 295, 'damage': 85, 'exp': 234, 'desc': 'Guards the coolest part of this place. Still hot enough to melt iron.'},
                'infernal knight':   {'health': 198, 'damage': 92, 'exp': 205, 'desc': 'Sworn to a lord who burned. Still keeps the oath.'},
                'char beast':        {'health': 232, 'damage': 96, 'exp': 216, 'desc': 'Larger than it should be, angrier than anything should be'},
                'the last flame':    {'health': 158, 'damage': 105,'exp': 228, 'desc': 'The fire that started everything. Still burning. Still spreading.'},
                'ash titan':         {'health': 308, 'damage': 90, 'exp': 244, 'desc': 'A titan made entirely of compressed ash and ancient heat'},
                'infernal guardian': {'health': 318, 'damage': 94, 'exp': 254, 'desc': 'Guards the heat at the core. Has never let it out.'},
                'pyre elemental':    {'health': 275, 'damage': 100,'exp': 238, 'desc': 'Born when a funeral pyre refused to go out'},
                'the burning throne':{'health': 285, 'damage': 108,'exp': 265, 'desc': 'The throne of the king of this place. The king never left it. Neither did the fire.'},
            },
            'floor_themes': {
                1:  ['ash walker', 'cinder hound', 'soot wraith'],
                2:  ['cinder hound', 'ember knight', 'ash walker'],
                3:  ['ember knight', 'pyro cultist', 'soot wraith'],
                4:  ['pyro cultist', 'cinder mage', 'lava golem'],
                5:  ['fire elemental', 'ashen titan', 'pyre elemental'],
                6:  ['lava golem', 'ashen titan', 'fire elemental'],
                7:  ['smoldering demon', 'infernal knight', 'char beast'],
                8:  ['char beast', 'pyroclast spawn', 'smoldering demon'],
                9:  ['ash titan', 'infernal guardian', 'slag guardian'],
                10: ['infernal guardian', 'the last flame', 'the burning throne'],
            },
            'boss_data': {
                1:  {'name': 'The Cinder King',     'special': 'EMBER STORM',       'base_health': 372,  'health_scaling': 21, 'damage': 54,  'exp_reward': 392,  'special_bonus': 35, 'stat_bonus': 4, 'min_level': 4},
                2:  {'name': 'The Pyre Lord',       'special': 'FUNERAL FIRE',      'base_health': 452,  'health_scaling': 24, 'damage': 62,  'exp_reward': 474,  'special_bonus': 40, 'stat_bonus': 4, 'min_level': 6},
                3:  {'name': 'The Char Warden',     'special': 'ASH TSUNAMI',       'base_health': 532,  'health_scaling': 27, 'damage': 70,  'exp_reward': 554,  'special_bonus': 46, 'stat_bonus': 5, 'min_level': 8},
                4:  {'name': 'The Slag Queen',      'special': 'MAGMA SURGE',       'base_health': 614,  'health_scaling': 30, 'damage': 78,  'exp_reward': 634,  'special_bonus': 52, 'stat_bonus': 5, 'min_level': 10},
                5:  {'name': 'The Infernal Titan',  'special': 'PYROCLASTIC WAVE',  'base_health': 712,  'health_scaling': 33, 'damage': 87,  'exp_reward': 714,  'special_bonus': 58, 'stat_bonus': 6, 'min_level': 12},
                6:  {'name': 'The Ash God',         'special': 'TOTAL INCINERATION','base_health': 812,  'health_scaling': 36, 'damage': 96,  'exp_reward': 814,  'special_bonus': 65, 'stat_bonus': 6, 'min_level': 14},
                7:  {'name': 'The Burning Prince',  'special': 'HELLFIRE CROWN',    'base_health': 932,  'health_scaling': 39, 'damage': 106, 'exp_reward': 934,  'special_bonus': 72, 'stat_bonus': 7, 'min_level': 16},
                8:  {'name': 'The Last Conflagration','special':'WORLD BURN',       'base_health': 1072, 'health_scaling': 43, 'damage': 116, 'exp_reward': 1074, 'special_bonus': 80, 'stat_bonus': 7, 'min_level': 18},
                9:  {'name': 'The Eternal Pyre',    'special': 'UNDYING FLAME',     'base_health': 1232, 'health_scaling': 47, 'damage': 129, 'exp_reward': 1234, 'special_bonus': 90, 'stat_bonus': 8, 'min_level': 20},
                10: {'name': 'The First Fire',      'special': 'ORIGIN BURN',       'base_health': 1492, 'health_scaling': 54, 'damage': 146, 'exp_reward': 1494, 'special_bonus': 105,'stat_bonus': 10,'min_level': 22},
            },
            'boss_rooms': {
                1:  ("The Scorched Gate",   "The entrance has been on fire for so long it forgot how to stop.",     "The Cinder King steps from the flame."),
                2:  ("The Pyre Hall",       "A hall built for burning things. Still fulfilling its purpose.",        "The Pyre Lord emerges from the largest flame."),
                3:  ("The Char Chamber",    "Everything in here has burned. Some of it is burning still.",          "The Char Warden rises from the ash."),
                4:  ("The Magma Throne",    "A throne room with a throne made of cooled lava over old bones.",      "The Slag Queen flows from the cracks in the floor."),
                5:  ("The Pyroclast Field", "The remnants of an eruption that never fully finished.",               "The Infernal Titan solidifies from the ejecta."),
                6:  ("The Ash Cathedral",   "A cathedral dedicated to nothing but heat.",                           "The Ash God condenses from the smoke."),
                7:  ("The Burning Court",   "The court of someone who believed fire was the answer to everything.", "The Burning Prince takes their charred throne."),
                8:  ("The Last City",       "A city burned so completely it transcended destruction.",              "The Last Conflagration ignites."),
                9:  ("The Pyre Core",       "The source of all the fire. Still going.",                            "The Eternal Pyre opens its eyes. They are made of the oldest flame."),
                10: ("The Origin Point",    "This is where fire was invented. It regrets nothing.",                 "The First Fire remembers you."),
            },
        },

        # ── 4. THE MECHANICAL DEPTHS ──────────────────────────────
        'mechanical_depths': {
            'display_name': 'The Mechanical Depths',
            'wake_text': (
                "There is a sound.\n"
                "Not the usual dungeon sounds — not dripping water or distant screams.\n\n"
                "Ticking. Grinding. The sound of gears working against each other.\n"
                "The sound of something that was built.\n\n"
                "The walls here are brass and iron.\n"
                "The torches are gas-jets. The doors open by mechanism.\n"
                "Someone engineered this place. Someone who thought very carefully\n"
                "about what should live here.\n\n"
                "You will not enjoy meeting their creations."
            ),
            'enemies': {
                'clockwork rat':     {'health': 72,  'damage': 31, 'exp':  52, 'desc': 'Built to replace vermin. More dangerous than the original.'},
                'gear spider':       {'health': 88,  'damage': 38, 'exp':  65, 'desc': 'Eight legs of interlocking gears. Runs on something that is not blood.'},
                'brass soldier':     {'health': 142, 'damage': 48, 'exp':  89, 'desc': 'A soldier-automaton that was never given a deactivation command'},
                'iron skeleton':     {'health': 125, 'damage': 53, 'exp':  98, 'desc': 'Skeleton rebuilt in steel. More obedient than when it was alive.'},
                'steam knight':      {'health': 178, 'damage': 63, 'exp': 132, 'desc': 'Knight-automaton powered by pressurised steam. Vents at uncomfortable moments.'},
                'arc wraith':        {'health': 155, 'damage': 70, 'exp': 143, 'desc': 'The ghost of an engineer that became indistinguishable from their invention'},
                'piston mage':       {'health': 132, 'damage': 77, 'exp': 152, 'desc': 'Casts spells through mechanical focii that hit harder than hands ever could'},
                'gear golem':        {'health': 262, 'damage': 64, 'exp': 158, 'desc': 'Eighteen thousand moving parts. Counts them constantly.'},
                'clock demon':       {'health': 215, 'damage': 86, 'exp': 196, 'desc': 'A demon that arrived when someone wound a clock backwards'},
                'automaton hunter':  {'health': 188, 'damage': 82, 'exp': 186, 'desc': 'Designed specifically for hunting humans. Well-designed.'},
                'turbine elemental': {'health': 198, 'damage': 76, 'exp': 176, 'desc': 'Born when a turbine achieved critical mass of motion'},
                'null engineer':     {'health': 192, 'damage': 84, 'exp': 192, 'desc': 'An engineer who decided to improve themselves. Did not stop improving.'},
                'iron titan':        {'health': 305, 'damage': 88, 'exp': 242, 'desc': 'A titan made entirely of iron. Took two hundred years to build. One hour to wake.'},
                'brass celestial':   {'health': 275, 'damage': 104,'exp': 258, 'desc': 'Designed to be divine. Got most of the way there.'},
                'mechanism guardian':{'health': 315, 'damage': 91, 'exp': 252, 'desc': 'Guarding the Grand Mechanism. Has never been successfully breached.'},
                'clockwork beast':   {'health': 235, 'damage': 95, 'exp': 214, 'desc': 'A beast made of parts from other creatures. Disagrees with this arrangement.'},
                'engine spawn':      {'health': 252, 'damage': 100,'exp': 224, 'desc': 'Spawned when the engine ran too hot. Carries that heat with it.'},
                'the overseer':      {'health': 282, 'damage': 106,'exp': 262, 'desc': 'Watches everything. Has been watching since before you arrived.'},
                'prime automaton':   {'health': 325, 'damage': 93, 'exp': 256, 'desc': 'The first. The template. Every other automaton is a pale copy.'},
            },
            'floor_themes': {
                1:  ['clockwork rat', 'gear spider', 'brass soldier'],
                2:  ['brass soldier', 'iron skeleton', 'gear spider'],
                3:  ['iron skeleton', 'steam knight', 'arc wraith'],
                4:  ['arc wraith', 'piston mage', 'steam knight'],
                5:  ['turbine elemental', 'gear golem', 'automaton hunter'],
                6:  ['gear golem', 'turbine elemental', 'clockwork beast'],
                7:  ['clock demon', 'null engineer', 'engine spawn'],
                8:  ['engine spawn', 'automaton hunter', 'clock demon'],
                9:  ['iron titan', 'brass celestial', 'mechanism guardian'],
                10: ['mechanism guardian', 'prime automaton', 'the overseer'],
            },
            'boss_data': {
                1:  {'name': 'The First Foreman',    'special': 'GEAR GRIND',        'base_health': 368,  'health_scaling': 21, 'damage': 53,  'exp_reward': 388,  'special_bonus': 34, 'stat_bonus': 4, 'min_level': 4},
                2:  {'name': 'The Iron Warden',      'special': 'PISTON SLAM',       'base_health': 448,  'health_scaling': 24, 'damage': 61,  'exp_reward': 470,  'special_bonus': 39, 'stat_bonus': 4, 'min_level': 6},
                3:  {'name': 'The Brass Overlord',   'special': 'MECHANISM CRUSH',   'base_health': 528,  'health_scaling': 27, 'damage': 69,  'exp_reward': 550,  'special_bonus': 45, 'stat_bonus': 5, 'min_level': 8},
                4:  {'name': 'The Clock King',       'special': 'TIME STOP',         'base_health': 610,  'health_scaling': 30, 'damage': 77,  'exp_reward': 630,  'special_bonus': 51, 'stat_bonus': 5, 'min_level': 10},
                5:  {'name': 'The Steam Titan',      'special': 'PRESSURE BURST',    'base_health': 708,  'health_scaling': 33, 'damage': 86,  'exp_reward': 710,  'special_bonus': 58, 'stat_bonus': 6, 'min_level': 12},
                6:  {'name': 'The Gear God',         'special': 'TOTAL MECHANISM',   'base_health': 808,  'health_scaling': 36, 'damage': 95,  'exp_reward': 810,  'special_bonus': 65, 'stat_bonus': 6, 'min_level': 14},
                7:  {'name': 'The Iron Prince',      'special': 'IRON DECREE',       'base_health': 928,  'health_scaling': 39, 'damage': 105, 'exp_reward': 930,  'special_bonus': 72, 'stat_bonus': 7, 'min_level': 16},
                8:  {'name': 'The Grand Mechanism',  'special': 'TOTAL AUTOMATION',  'base_health': 1068, 'health_scaling': 43, 'damage': 115, 'exp_reward': 1070, 'special_bonus': 80, 'stat_bonus': 7, 'min_level': 18},
                9:  {'name': 'The Eternal Engine',   'special': 'PERPETUAL FORCE',   'base_health': 1228, 'health_scaling': 47, 'damage': 128, 'exp_reward': 1230, 'special_bonus': 90, 'stat_bonus': 8, 'min_level': 20},
                10: {'name': 'The Prime Constructor','special': 'FINAL BLUEPRINT',   'base_health': 1488, 'health_scaling': 54, 'damage': 145, 'exp_reward': 1490, 'special_bonus': 105,'stat_bonus': 10,'min_level': 22},
            },
            'boss_rooms': {
                1:  ("The Foreman's Floor",  "Blueprints cover every surface. Most are circled in red.",            "The First Foreman boots up for the last time."),
                2:  ("The Iron Works",       "Hammers strike metal in perfect unison. Nothing is making them.",     "The Iron Warden marches from the assembly line."),
                3:  ("The Brass Chamber",    "A room of interlocking brass pieces the size of houses.",             "The Brass Overlord disassembles from the walls."),
                4:  ("The Clocktower Core",  "At the centre of a massive clock, counting down.",                   "The Clock King pauses time for a moment. Just to make a point."),
                5:  ("The Steam Core",       "Heat and pressure at levels that should destroy the room.",           "The Steam Titan vents."),
                6:  ("The Gear Cathedral",   "A place of worship for the principle of motion itself.",              "The Gear God rotates into existence."),
                7:  ("The Iron Court",       "A court where every attendee is bolted to their seat.",               "The Iron Prince gives a command. Everything in the room obeys."),
                8:  ("The Grand Works",      "The central mechanism of all of this. Still running. Perfect.",       "The Grand Mechanism turns its attention to you."),
                9:  ("The Engine Heart",     "The power source for the entire Mechanical Depths. Still going.",     "The Eternal Engine focuses all that power on a single target. You."),
                10: ("The Blueprint Room",   "The original designs for everything. Including, apparently, you.",    "The Prime Constructor reviews your file. Is unimpressed."),
            },
        },

        # ── 5. THE PLAGUE CATHEDRAL ───────────────────────────────
        'plague_cathedral': {
            'display_name': 'The Plague Cathedral',
            'wake_text': (
                "There is incense in the air.\n"
                "But not pleasant incense — incense designed to cover something.\n"
                "It is not covering it well.\n\n"
                "The dungeon has become a cathedral. Or a cathedral has become the dungeon.\n"
                "Stone pews. Stained glass depicting saints who are screaming.\n"
                "Monks moving in the shadows who have not looked up at your arrival.\n\n"
                "The faith here is real. What it worships is worse.\n\n"
                "You are about to walk deeper into a place that prays\n"
                "and believes its prayers are answered."
            ),
            'enemies': {
                'plague rat':        {'health': 75,  'damage': 34, 'exp':  54, 'desc': 'Carries something worse than disease — a belief system'},
                'infected novice':   {'health': 105, 'damage': 42, 'exp':  75, 'desc': 'Newly ordained. Newly infected. Equally committed to both.'},
                'plague monk':       {'health': 138, 'damage': 49, 'exp':  88, 'desc': 'Spreads the faith by touch. The faith is not metaphorical.'},
                'diseased knight':   {'health': 155, 'damage': 57, 'exp': 104, 'desc': 'Still armoured, still disciplined, still knight-shaped. No longer sanitary.'},
                'rot wraith':        {'health': 145, 'damage': 65, 'exp': 135, 'desc': 'The ghost of someone who died of something communicable'},
                'plague inquisitor': {'health': 162, 'damage': 72, 'exp': 148, 'desc': 'Investigates heresy. Considers health heretical.'},
                'pus mage':          {'health': 128, 'damage': 79, 'exp': 154, 'desc': 'Casts spells through a medium that is better not described'},
                'blight golem':      {'health': 258, 'damage': 63, 'exp': 155, 'desc': 'A golem shaped from concentrated disease, held together by faith'},
                'contagion demon':   {'health': 218, 'damage': 87, 'exp': 198, 'desc': 'A demon that crossed over through an infected wound'},
                'blessed plague':    {'health': 175, 'damage': 90, 'exp': 188, 'desc': 'The disease itself, given form, grateful to be worshipped'},
                'fever elemental':   {'health': 195, 'damage': 80, 'exp': 180, 'desc': 'Born from the fever of a thousand dying faithful'},
                'null bishop':       {'health': 192, 'damage': 83, 'exp': 190, 'desc': 'A bishop who achieved communion with something that has no name'},
                'plague titan':      {'health': 298, 'damage': 87, 'exp': 238, 'desc': 'A titan that welcomed the plague and became its avatar'},
                'saint of rot':      {'health': 278, 'damage': 103,'exp': 256, 'desc': 'Canonised after death. The cathedral considers this an improvement.'},
                'rot guardian':      {'health': 312, 'damage': 91, 'exp': 252, 'desc': 'Guarding the high altar. Has never been successfully challenged.'},
                'cathedral spawn':   {'health': 245, 'damage': 97, 'exp': 218, 'desc': 'Born from the cathedral itself — the building is trying to protect itself'},
                'divine plague':     {'health': 268, 'damage': 104,'exp': 260, 'desc': 'The disease that the cathedral worships. It is flattered.'},
                'the high inquisitor':{'health': 288, 'damage': 107,'exp': 264, 'desc': 'Oldest member of the order. Has outlived everyone else by decades. This is suspicious.'},
                'eternal pestilence':{'health': 322, 'damage': 93, 'exp': 257, 'desc': 'The original plague. The one that started all the others. Still spreading.'},
            },
            'floor_themes': {
                1:  ['plague rat', 'infected novice', 'plague monk'],
                2:  ['plague monk', 'diseased knight', 'plague rat'],
                3:  ['diseased knight', 'rot wraith', 'plague inquisitor'],
                4:  ['plague inquisitor', 'pus mage', 'rot wraith'],
                5:  ['fever elemental', 'blight golem', 'cathedral spawn'],
                6:  ['blight golem', 'fever elemental', 'blessed plague'],
                7:  ['contagion demon', 'null bishop', 'divine plague'],
                8:  ['divine plague', 'cathedral spawn', 'contagion demon'],
                9:  ['plague titan', 'saint of rot', 'rot guardian'],
                10: ['rot guardian', 'eternal pestilence', 'the high inquisitor'],
            },
            'boss_data': {
                1:  {'name': 'The First Abbot',     'special': 'BLESSED INFECTION',  'base_health': 375,  'health_scaling': 21, 'damage': 54,  'exp_reward': 394,  'special_bonus': 35, 'stat_bonus': 4, 'min_level': 4},
                2:  {'name': 'The Plague Bishop',   'special': 'COMMUNION OF ROT',   'base_health': 454,  'health_scaling': 24, 'damage': 62,  'exp_reward': 476,  'special_bonus': 40, 'stat_bonus': 4, 'min_level': 6},
                3:  {'name': 'The Blight Cardinal', 'special': 'HOLY CONTAGION',     'base_health': 534,  'health_scaling': 27, 'damage': 70,  'exp_reward': 556,  'special_bonus': 46, 'stat_bonus': 5, 'min_level': 8},
                4:  {'name': 'The Rot Archon',      'special': 'PESTILENCE WAVE',    'base_health': 616,  'health_scaling': 30, 'damage': 78,  'exp_reward': 636,  'special_bonus': 52, 'stat_bonus': 5, 'min_level': 10},
                5:  {'name': 'The Plague Titan',    'special': 'DIVINE PESTILENCE',  'base_health': 714,  'health_scaling': 33, 'damage': 87,  'exp_reward': 716,  'special_bonus': 58, 'stat_bonus': 6, 'min_level': 12},
                6:  {'name': 'The Cathedral God',   'special': 'SERMON OF SUFFERING','base_health': 814,  'health_scaling': 36, 'damage': 96,  'exp_reward': 816,  'special_bonus': 65, 'stat_bonus': 6, 'min_level': 14},
                7:  {'name': 'The Plague Prince',   'special': 'CROWN OF THORNS',    'base_health': 934,  'health_scaling': 39, 'damage': 106, 'exp_reward': 936,  'special_bonus': 72, 'stat_bonus': 7, 'min_level': 16},
                8:  {'name': 'The High Inquisitor', 'special': 'DIVINE JUDGEMENT',   'base_health': 1074, 'health_scaling': 43, 'damage': 116, 'exp_reward': 1076, 'special_bonus': 80, 'stat_bonus': 7, 'min_level': 18},
                9:  {'name': 'The Plague Saint',    'special': 'MARTYRS PLAGUE',     'base_health': 1234, 'health_scaling': 47, 'damage': 129, 'exp_reward': 1236, 'special_bonus': 90, 'stat_bonus': 8, 'min_level': 20},
                10: {'name': 'The Eternal Pestilence','special':'THE LAST SERMON',   'base_health': 1494, 'health_scaling': 54, 'damage': 146, 'exp_reward': 1496, 'special_bonus': 105,'stat_bonus': 10,'min_level': 22},
            },
            'boss_rooms': {
                1:  ("The Novice Chapel",     "Where new members of the order are welcomed. And infected.",          "The First Abbot gives the welcoming sermon."),
                2:  ("The Bishop's Sanctum",  "A sanctum full of relics that are still contagious.",                 "The Plague Bishop rises from prayer."),
                3:  ("The Cardinal's Hall",   "Every surface is carved with the names of the dead. All of them.",    "The Blight Cardinal pronounces a blessing. It does not feel like one."),
                4:  ("The Archon's Throne",   "A throne covered in something that was once velvet.",                 "The Rot Archon ascends."),
                5:  ("The Plague Cathedral",  "The main hall. The ceiling is stained glass depicting a saint dying.", "The Plague Titan walks down the aisle."),
                6:  ("The Nave of Suffering", "Pews full of kneeling figures who have been kneeling for centuries.", "The Cathedral God delivers its homily."),
                7:  ("The Prince's Chapel",   "A private chapel for someone who believed themselves chosen.",         "The Plague Prince takes communion."),
                8:  ("The Inquisition Chamber","Where heretics were brought. The equipment is still maintained.",     "The High Inquisitor opens the case file."),
                9:  ("The Saint's Reliquary", "The saint's remains. Still miraculously spreading plague.",            "The Plague Saint opens its eyes. They are full of faith."),
                10: ("The Eternal Altar",     "The altar at the heart of everything. Still warm with worship.",      "The Eternal Pestilence accepts your offering of continued existence. For now."),
            },
        },

    }

    # Aliases so existing code that references flat dicts still resolves.
    # These point at World 1 (Fractured Labyrinth) as the default.
    NG_PLUS_ENEMIES     = NG_PLUS_WORLDS['fractured_labyrinth']['enemies']
    NG_PLUS_FLOOR_THEMES = NG_PLUS_WORLDS['fractured_labyrinth']['floor_themes']
    NG_PLUS_BOSS_DATA   = NG_PLUS_WORLDS['fractured_labyrinth']['boss_data']

#################################################################################
# DATA-DRIVEN ROOM TEMPLATES
#################################################################################


