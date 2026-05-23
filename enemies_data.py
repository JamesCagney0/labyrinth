"""LABYRINTH — Enemy definitions"""
from __future__ import annotations
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class EnemiesData:
    """All enemy-related constants. Imported into GameConstants."""

    ENEMIES = {
        'sewer rat':        {'health':  20, 'damage':  7, 'exp':  35, 'desc': 'A disease-ridden rat with glowing red eyes'},
        'goblin':           {'health':  34, 'damage': 10, 'exp':  48, 'desc': 'A small, green-skinned creature wielding a crude club'},
        'skeleton':         {'health':  41, 'damage': 13, 'exp':  48, 'desc': 'Animated bones held together by dark magic'},
        'prison guard':     {'health':  54, 'damage': 15, 'exp':  50, 'desc': 'A corrupted guard in tattered armor'},
        'armored skeleton': {'health':  61, 'damage': 18, 'exp':  62, 'desc': 'A skeleton warrior clad in ancient armor'},
        'shadow wraith':    {'health':  68, 'damage': 23, 'exp':  65, 'desc': 'A spectral being that feeds on fear'},
        'corrupted mage':   {'health':  54, 'damage': 25, 'exp':  78, 'desc': 'A once-noble mage consumed by forbidden magic'},
        'ghoul':            {'health':  74, 'damage': 20, 'exp':  76, 'desc': 'A flesh-eating undead creature'},
        'fire elemental':   {'health':  81, 'damage': 28, 'exp':  90, 'desc': 'A being of pure flame and rage'},
        'ice elemental':    {'health':  78, 'damage': 25, 'exp':  90, 'desc': 'A crystalline creature radiating freezing cold'},
        'lightning wisp':   {'health':  68, 'damage': 31, 'exp':  104, 'desc': 'Crackling energy given form'},
        'stone golem':      {'health': 108, 'damage': 23, 'exp':  106, 'desc': 'A massive construct of animated stone'},
        'lesser demon':     {'health':  95, 'damage': 33, 'exp':  118, 'desc': 'A horned creature from the abyss'},
        'dark cultist':     {'health':  88, 'damage': 30, 'exp':  120, 'desc': 'A fanatic devoted to dark powers'},
        'shadow beast':     {'health': 101, 'damage': 35, 'exp':  132, 'desc': 'A monstrous predator born of darkness'},
        'void spawn':       {'health': 108, 'damage': 38, 'exp':  135, 'desc': 'An aberration from beyond reality'},
        'ancient guardian': {'health': 122, 'damage': 40, 'exp': 146, 'desc': 'An eternal sentinel of forgotten secrets'},
        'cosmic horror':    {'health': 115, 'damage': 44, 'exp': 162, 'desc': 'An incomprehensible being from the void'},
        'titan spawn':      {'health': 135, 'damage': 38, 'exp': 160, 'desc': 'Offspring of the primordial titans'},
        'celestial knight': {'health': 128, 'damage': 43, 'exp': 160, 'desc': 'A fallen warrior of the heavens'},
        'treasure guardian':{'health':  81, 'damage': 25, 'exp':  80, 'desc': 'A magical construct protecting valuable treasure'}
    }
    

    FLOOR_THEMES = {
        1: ['sewer rat', 'goblin', 'skeleton', 'prison guard'],
        2: ['goblin', 'skeleton', 'prison guard', 'armored skeleton'],
        3: ['armored skeleton', 'shadow wraith', 'corrupted mage', 'ghoul'],
        4: ['shadow wraith', 'corrupted mage', 'ghoul', 'armored skeleton'],
        5: ['fire elemental', 'ice elemental', 'lightning wisp', 'stone golem'],
        6: ['fire elemental', 'ice elemental', 'stone golem', 'lightning wisp'],
        7: ['lesser demon', 'dark cultist', 'shadow beast', 'void spawn'],
        8: ['lesser demon', 'dark cultist', 'shadow beast', 'void spawn'],
        9: ['ancient guardian', 'cosmic horror', 'titan spawn', 'celestial knight'],
        10: ['ancient guardian', 'cosmic horror', 'titan spawn', 'celestial knight']
    }
    
    # Item definitions

    ENEMY_WEAKNESSES = {
        'sewer rat':        {'venomous': 1.5},
        'goblin':           {'savage': 1.4},
        'skeleton':         {'holy': 1.65, 'savage': 1.3},
        'prison guard':     {'bleeding': 1.5},
        'armored skeleton': {'holy': 1.5},
        'shadow wraith':    {'holy': 1.7, 'elemental_fire': 1.5},
        'corrupted mage':   {'precise': 1.5, 'swift': 1.3},
        'ghoul':            {'holy': 1.5, 'elemental_fire': 1.4},
        'fire elemental':   {'elemental_ice': 1.7},
        'ice elemental':    {'elemental_fire': 1.7},
        'lightning wisp':   {'elemental_ice': 1.5, 'shielded': 1.3},
        'stone golem':      {'savage': 1.6, 'bleeding': 1.0},
        'lesser demon':     {'holy': 1.7},
        'dark cultist':     {'holy': 1.5, 'precise': 1.3},
        'shadow beast':     {'holy': 1.5, 'elemental_fire': 1.4},
        'void spawn':       {'holy': 1.4, 'elemental_fire': 1.3},
        'ancient guardian': {'venomous': 1.5, 'executioner': 1.4},
        'cosmic horror':    {'holy': 1.4, 'berserker': 1.4},
        'titan spawn':      {'executioner': 1.6, 'bleeding': 1.3},
        'celestial knight': {'cursed': 1.6, 'venomous': 1.3},
        'treasure guardian':{'precise': 1.4, 'savage': 1.3},
    }


    # ── NEW GAME+ ─────────────────────────────────────────────────
    # The Fractured Labyrinth — a corruption of the original dungeon.
    # Enemies have independent stat blocks; much tankier and harder hitting.

    # ── NG+ themed title screens ─────────────────────────────────
    # Each matches the original LABYRINTH style but distorted to theme.

    ENEMY_BEHAVIOURS: Dict[str, Dict] = {
        'shadow wraith': {
            'regen': 15, 'regen_cond': 'no_trait:holy,arcane,void',
            'intent': 'The wraith pulses with stolen vitality...',
            'inflict': 'weaken',
        },
        'stone golem': {
            'dmg_reduce': 0.5, 'dmg_cond': 'piercing,heavy,explosive',
            'intent': 'The golem raises its massive stone fists...',
            'special_turn': 3, 'special_dmg_mult': 1.8, 'special_msg': 'GROUND SLAM!',
        },
        'dark cultist': {
            'buff_others': True,
            'intent': 'The cultist chants — something stirs in the room...',
            'special_turn': 2, 'special_dmg_mult': 1.4, 'special_msg': 'DARK RITUAL!',
        },
        'ghoul': {
            'inflict': 'bleed',
            'intent': 'The ghoul lunges with raking claws...',
        },
        'corrupted mage': {
            'inflict': 'poison',
            'intent': 'The mage draws corrupted energy inward...',
            'special_turn': 3, 'special_dmg_mult': 2.0, 'special_msg': 'CORRUPTION BURST!',
        },
        'lesser demon': {
            'dmg_reduce': 0.3, 'dmg_cond': 'holy,silver,arcane',
            'intent': 'The demon grins as your weapon glances off its hide...',
            'inflict': 'weaken',
        },
        'void spawn': {
            'regen': 10, 'regen_cond': 'no_trait:void,arcane',
            'intent': 'The void spawn phases in and out of reality...',
            'special_turn': 3, 'special_dmg_mult': 1.6, 'special_msg': 'VOID SURGE!',
        },
        'ancient guardian': {
            'dmg_reduce': 0.4, 'dmg_cond': 'heavy,explosive,silver',
            'intent': 'The guardian braces itself against your next attack...',
            'special_turn': 2, 'special_dmg_mult': 1.7, 'special_msg': 'ANCIENT WRATH!',
        },
        'cosmic horror': {
            'inflict': 'weaken',
            'intent': 'Reality warps around the horror...',
            'special_turn': 2, 'special_dmg_mult': 1.9, 'special_msg': 'MIND SHATTER!',
        },
        'lightning wisp': {
            'intent': 'The wisp crackles with building static charge...',
            'special_turn': 2, 'special_dmg_mult': 2.2, 'special_msg': 'CHAIN LIGHTNING!',
        },
        'armored skeleton': {
            'dmg_reduce': 0.35, 'dmg_cond': 'heavy,blunt,explosive',
            'intent': 'The skeleton raises its ancient shield...',
        },
        'shadow beast': {
            'inflict': 'bleed',
            'regen': 8, 'regen_cond': 'no_trait:light,holy,fire',
            'intent': 'The beast snarls, shadows coiling around it...',
        },
        'fire elemental': {
            'inflict': 'poison',
            'intent': 'The elemental surges with intensifying flame...',
            'special_turn': 3, 'special_dmg_mult': 1.8, 'special_msg': 'INFERNO!',
        },
        'titan spawn': {
            'dmg_reduce': 0.4, 'dmg_cond': 'piercing,heavy',
            'intent': 'The titan spawn shoulders into a devastating charge...',
            'special_turn': 3, 'special_dmg_mult': 2.0, 'special_msg': 'TITAN CRUSH!',
        },
        'celestial knight': {
            'regen': 12, 'regen_cond': 'no_trait:void,cursed,dark',
            'inflict': 'weaken',
            'intent': 'The knight channels divine power into its blade...',
            'special_turn': 3, 'special_dmg_mult': 1.9, 'special_msg': 'CELESTIAL STRIKE!',
        },
    }

    # ── Player status effects ────────────────────────────────────
    # Inflicted during combat, tick on each enemy turn AND on room movement.
    # Makes healing items necessary — you can't just ignore attrition.

    STATUS_EFFECTS: Dict[str, Dict] = {
        'bleed':  {'dmg_per_turn': 8,  'duration': 3, 'icon': '🩸', 'msg': 'You are bleeding!'},
        'poison': {'dmg_per_turn': 6,  'duration': 4, 'icon': '☠',  'msg': 'You are poisoned!'},
        'weaken': {'dmg_mult': 0.75,   'duration': 2, 'icon': '💀',  'msg': 'You feel weakened — attacks deal less damage!'},
    }

