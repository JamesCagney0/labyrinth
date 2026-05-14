"""
================================================================================
LABYRINTH - A 10-Floor Dungeon RPG
================================================================================
Version: 7.0.2
Author: DEKU
Python: 3.13+

CHANGELOG 7.0.2:
- NEW: Faith stat added as Paladin-exclusive signature stat
  - Paladin: base 14, +2 per level
  - All others: 5 (inert, like arcane for non-mages)
  - Divine Smite now scales off STR + Faith*2 + Faith bonus multiplier
  - Holy Aura passive now scales: 25% base + 1.5% per Faith above 10
  - Stats screen shows live Holy Aura % and Smite damage preview
  - Faith gain displayed on level-up

CHANGELOG 7.0.1:
- NEW: Game titled "LABYRINTH" with ASCII title screen and lore intro
- NEW: 5th character stat — Arcane (mage-exclusive: boosts magic dmg, lowers mana cost)
- NEW: Two new playable classes — Paladin and Berserker
  - Paladin: holy warrior with Divine Smite boss ability and passive holy bonus
  - Berserker: rage fighter with built-in Berserker scaling and Rage boss ability
- NEW: Weapon swap before every regular fight (pre-combat prompt)
- NEW: "5. Swap Weapon" option in boss fight action menu
- NEW: switch_weapon display shows traits alongside damage
- NEW: Labyrinth-themed quit screen with game summary lore

CHANGELOG 6.9.2:
- BALANCE: Each boss now drops from a pool of 10 unique weapons per class
  - 5 GOOD weapons (60% chance): solid upgrades with standard scaling
  - 3 GREAT weapons (30% chance): notably stronger with 1.20-1.30x bonus
  - 2 INSANE weapons (10% chance): game-changing with 1.60-1.70x bonus
  - Weapon tier is displayed on drop (★ GOOD / ★★★ GREAT / ★★★★★ INSANE)
- BALANCE: All enemy base damage increased ~25% to keep combat risky
- BALANCE: Enemy damage now scales with player weapon power
  (stronger weapons = enemies hit harder, making healing items relevant)
- BALANCE: Healing item spawn rates significantly reduced
  - Enemy drop chance lowered (0.35 → 0.22)
  - Drop pool shifted toward exp/utility items
  - Template healing potions skip ~50% of the time during dungeon generation
- FIX: Boss combat now shows HP *and* MP for player each turn
- FIX: Boss combat supports word aliases (attack/a, magic/m/spell, defend/d/block, heal/h)
- FIX: Warriors explicitly blocked from using magic in boss fights
- FIX: Invalid boss action no longer wastes a turn (continue loop guard)
- FIX: CommandRegistry fuzzy matching ignores direction typos and the 'out' command
- FIX: 'out', 'o', 'back', 'b' commands added for exiting secret rooms
- FIX: discard_item now prints a message when item is not found
- FIX: show_room_summary labels the 'out' exit as 'OUT (back to previous room)'
- FIX: Unique item tracking expanded to include rusty key and bone key

CHANGELOG 6.9.0:
- MAJOR: Added 48+ new unique room templates (12 per theme)
- Each floor theme now has diverse, thematic room names and descriptions
- EXPANDED compass map shows up to 3 rooms in each direction
- Depth indicators show how far rooms are from you
- Floor overview section lists ALL rooms with their status

CHANGELOG 6.8.0:
- MAJOR: Boss weapons now scale dynamically with player level and current weapon
- Boss weapons provide appropriate boost (15-50%) based on floor without overpowering
- Early floors (1-4) have damage caps to prevent one-shotting enemies
- Boss rewards remain legendary rarity but with balanced damage scaling
"""

import random
import json
import os
import logging
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from difflib import get_close_matches
from dataclasses import dataclass, field

# Configure comprehensive logging (file only, no console output)
logging.basicConfig(
    filename='game.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d - %(message)s',
    filemode='a'
)
logger = logging.getLogger(__name__)

#################################################################################
# GAME CONSTANTS & CONFIGURATION
#################################################################################
class GameConstants:
    """Central configuration class containing all game constants"""
    VERSION = "7.0.2"
    SAVE_FILE = "savegame.json"
    SAVE_DIRECTORY = "saves"
    MAX_SAVE_SLOTS = 5
    
    # Floor configuration
    NUM_FLOORS = 10
    MIN_ROOMS_PER_FLOOR = 10
    MAX_ROOMS_PER_FLOOR = 15
    
    # Class definitions with enhanced inventory
    CLASSES = {
        'warrior': {
            'base_health': 120, 'base_mana': 0,
            'base_stats': {'strength': 15, 'intelligence': 8, 'agility': 10,
                           'luck': 8, 'vitality': 14, 'arcane': 5, 'faith': 5, 'lust': 5},
            'health_per_level': 15, 'inventory_slots': 5,
            'weapon_types': ['melee'],
            'stat_growth': {'strength': 3, 'intelligence': 1, 'agility': 1,
                            'luck': 0, 'vitality': 2, 'arcane': 0, 'faith': 0, 'lust': 0},
        },
        'mage': {
            'base_health': 80, 'base_mana': 150,
            # Arcane 14 → reduces mana cost, multiplies magic damage
            'base_stats': {'strength': 8, 'intelligence': 15, 'agility': 10,
                           'luck': 12, 'vitality': 6, 'arcane': 14, 'faith': 5, 'lust': 5},
            'health_per_level': 8, 'inventory_slots': 5,
            'weapon_types': ['magic'],
            'stat_growth': {'strength': 1, 'intelligence': 3, 'agility': 1,
                            'luck': 1, 'vitality': 0, 'arcane': 2, 'faith': 0, 'lust': 0},
        },
        'rogue': {
            'base_health': 100, 'base_mana': 0,
            'base_stats': {'strength': 10, 'intelligence': 10, 'agility': 15,
                           'luck': 16, 'vitality': 10, 'arcane': 5, 'faith': 5, 'lust': 5},
            'health_per_level': 12, 'inventory_slots': 5,
            'weapon_types': ['stealth'],
            'stat_growth': {'strength': 1, 'intelligence': 1, 'agility': 3,
                            'luck': 2, 'vitality': 1, 'arcane': 0, 'faith': 0, 'lust': 0},
        },
        'paladin': {
            'base_health': 110, 'base_mana': 60,
            # Holy warrior: moderate strength, great vitality, steady luck
            # Passive: holy weapons deal an extra +25% (stacks with trait bonus)
            # Boss ability: Divine Smite (costs 20 mana, guaranteed holy damage)
            'base_stats': {'strength': 13, 'intelligence': 10, 'agility': 8,
                           'luck': 10, 'vitality': 15, 'arcane': 5, 'faith': 14, 'lust': 5},
            'health_per_level': 13, 'inventory_slots': 5,
            'weapon_types': ['melee'],
            'stat_growth': {'strength': 2, 'intelligence': 1, 'agility': 1,
                            'luck': 1, 'vitality': 2, 'arcane': 0, 'faith': 2, 'lust': 0},
        },
        'berserker': {
            'base_health': 140, 'base_mana': 0,
            # Rage class: highest raw strength and vitality, lowest agility/luck
            # Passive: berserker scaling always applies regardless of weapon trait
            # Boss ability: Rage (free, boosts next attack by 50%, usable once per fight)
            'base_stats': {'strength': 18, 'intelligence': 5, 'agility': 7,
                           'luck': 6, 'vitality': 18, 'arcane': 5, 'faith': 5, 'lust': 5},
            'health_per_level': 18, 'inventory_slots': 5,
            'weapon_types': ['melee'],
            'stat_growth': {'strength': 4, 'intelligence': 0, 'agility': 1,
                            'luck': 0, 'vitality': 3, 'arcane': 0, 'faith': 0, 'lust': 0},
        },
    }

    LUST_ITEMS = {
        'vibrating butt plug': {'stat': 'lust', 'bonus': 8},
    }

    SPECIAL_WEAPONS = {
        'the eternal splooger': {
            'name': "The Eternal Splooger",
            'damage': 68,
            'type': 'melee',
            'rarity': 'mythic',
            'base_name': "The Eternal Splooger",
            'traits': ['splooge', 'vampiric'],
        }
    }

    CLASS_NAMES = {
        1: {'warrior': 'Warrior',       'mage': 'Mage',          'rogue': 'Rogue',
            'paladin': 'Paladin',       'berserker': 'Berserker'},
        2: {'warrior': 'Vanguard',      'mage': 'Sorcerer',      'rogue': 'Assassin',
            'paladin': 'Crusader',      'berserker': 'Bloodrage'},
        3: {'warrior': 'Warlord',       'mage': 'Archmage',      'rogue': 'Shadow Master',
            'paladin': 'Holy Knight',   'berserker': 'War Champion'},
        4: {'warrior': 'Iron Titan',    'mage': 'Spellweaver',   'rogue': 'Phantom',
            'paladin': 'Divine Shield', 'berserker': 'Doom Bringer'},
        5: {'warrior': 'Titan Knight',  'mage': 'Void Sage',     'rogue': 'Death Walker',
            'paladin': 'Avatar of Light','berserker': 'Chaos Titan'},
    }

    # Upgrade thresholds — one per ~2 floors so the final tier lands at floor 9-10
    # Level 4 → Tier 2  (floors 1-2)
    # Level 8 → Tier 3  (floors 3-4)
    # Level 12 → Tier 4 (floors 5-6)
    # Level 16 → Tier 5 (floors 7-8)
    # Level 20 → Tier 5 complete (floor 9-10, no further upgrade)
    CLASS_UPGRADE_LEVELS = [4, 8, 12, 16]
    RARITY_BOOST_PER_TIER = 0.05
    # === ADULT CONTENT SETTINGS ===
    SEX_DUNGEON_FLOORS = (6, 9)
    SEX_DUNGEON_SPAWN_CHANCE = 0.28
    
    # Weapon rarity system
    WEAPON_RARITIES = {
        'common': {'multiplier': 1.0, 'color': 'WHITE', 'base_min': 8, 'base_max': 12},
        'uncommon': {'multiplier': 1.3, 'color': 'GREEN', 'base_min': 10, 'base_max': 14},
        'rare': {'multiplier': 1.6, 'color': 'BLUE', 'base_min': 12, 'base_max': 16},
        'epic': {'multiplier': 2.0, 'color': 'PURPLE', 'base_min': 14, 'base_max': 18},
        'legendary': {'multiplier': 2.5, 'color': 'GOLD', 'base_min': 16, 'base_max': 20},
        'mythic': {'multiplier': 3.0, 'color': 'RED', 'base_min': 18, 'base_max': 22},
        'divine': {'multiplier': 999.0, 'color': 'STAR', 'base_min': 100, 'base_max': 100}
    }
    
    RARITY_ORDER = ['common', 'uncommon', 'rare', 'epic', 'legendary', 'mythic', 'divine']
    BETTER_WEAPON_RARITY_BOOST = 0.15
    
    WEAPON_TYPES = {
        'melee': ['Sword', 'Axe', 'Hammer', 'Spear', 'Blade', 'Greatsword', 'Mace'],
        'magic': ['Staff', 'Wand', 'Orb', 'Tome', 'Crystal', 'Scepter'],
        'stealth': ['Dagger', 'Bow', 'Claws', 'Shiv', 'Needle', 'Rapier']
    }
    
    WEAPON_MATERIALS = {
        'common': ['Iron', 'Steel', 'Bronze', 'Copper', 'Stone'],
        'uncommon': ['Silver', 'Enchanted', 'Sharp', 'Sturdy', 'Fine'],
        'rare': ['Mithril', 'Elven', 'Dwarven', 'Mystic', 'Ancient'],
        'epic': ['Dragon', 'Phoenix', 'Ethereal', 'Celestial', 'Infernal'],
        'legendary': ['Godforged', 'Divine', 'Eternal', 'Primordial', 'Void'],
        'mythic': ['Cosmos', 'Reality', 'Infinity', 'Quantum', 'Supreme']
    }
    
    GOLDEN_GUN_NAMES = [
        "Excalibur's Vengeance", "Dragonslayer Supreme", "Godkiller Mk.VII",
        "The Infinity Decimator", "Cosmos Ender", "Reality Ripper"
    ]
    GOLDEN_GUN_DROP_RATE = 0.0002
    
    # Complete enemy roster (20+ types)
    # Damage values raised ~25% to keep combat risky as players gear up
    ENEMIES = {
        'sewer rat':        {'health': 15, 'damage':  7, 'exp':  15, 'desc': 'A disease-ridden rat with glowing red eyes'},
        'goblin':           {'health': 25, 'damage': 10, 'exp':  25, 'desc': 'A small, green-skinned creature wielding a crude club'},
        'skeleton':         {'health': 30, 'damage': 13, 'exp':  30, 'desc': 'Animated bones held together by dark magic'},
        'prison guard':     {'health': 40, 'damage': 15, 'exp':  35, 'desc': 'A corrupted guard in tattered armor'},
        'armored skeleton': {'health': 45, 'damage': 18, 'exp':  45, 'desc': 'A skeleton warrior clad in ancient armor'},
        'shadow wraith':    {'health': 50, 'damage': 23, 'exp':  55, 'desc': 'A spectral being that feeds on fear'},
        'corrupted mage':   {'health': 40, 'damage': 25, 'exp':  60, 'desc': 'A once-noble mage consumed by forbidden magic'},
        'ghoul':            {'health': 55, 'damage': 20, 'exp':  50, 'desc': 'A flesh-eating undead creature'},
        'fire elemental':   {'health': 60, 'damage': 28, 'exp':  70, 'desc': 'A being of pure flame and rage'},
        'ice elemental':    {'health': 58, 'damage': 25, 'exp':  68, 'desc': 'A crystalline creature radiating freezing cold'},
        'lightning wisp':   {'health': 50, 'damage': 31, 'exp':  75, 'desc': 'Crackling energy given form'},
        'stone golem':      {'health': 80, 'damage': 23, 'exp':  65, 'desc': 'A massive construct of animated stone'},
        'lesser demon':     {'health': 70, 'damage': 33, 'exp':  85, 'desc': 'A horned creature from the abyss'},
        'dark cultist':     {'health': 65, 'damage': 30, 'exp':  80, 'desc': 'A fanatic devoted to dark powers'},
        'shadow beast':     {'health': 75, 'damage': 35, 'exp':  90, 'desc': 'A monstrous predator born of darkness'},
        'void spawn':       {'health': 80, 'damage': 38, 'exp':  95, 'desc': 'An aberration from beyond reality'},
        'ancient guardian': {'health': 90, 'damage': 40, 'exp': 110, 'desc': 'An eternal sentinel of forgotten secrets'},
        'cosmic horror':    {'health': 85, 'damage': 44, 'exp': 120, 'desc': 'An incomprehensible being from the void'},
        'titan spawn':      {'health': 100,'damage': 38, 'exp': 105, 'desc': 'Offspring of the primordial titans'},
        'celestial knight': {'health': 95, 'damage': 43, 'exp': 115, 'desc': 'A fallen warrior of the heavens'},
        'treasure guardian':{'health': 60, 'damage': 25, 'exp':  65, 'desc': 'A magical construct protecting valuable treasure'}
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
    HEALING_ITEMS = {
        'health potion': {'heal': 30, 'type': 'health'},
        'ultimate health potion': {'heal': 'full', 'type': 'health'},
        'magic scroll': {'heal': 25, 'type': 'mana'},
        'ice crystal': {'heal': 50, 'type': 'mana'},
        'energy drink': {'heal': 20, 'type': 'health'},
        'vitality tonic': {'heal': 35, 'type': 'health'},
        'elixir of life': {'heal': 50, 'type': 'health'}
    }
    
    EXPERIENCE_ITEMS = {
        'experience gem': {'amount': 50},
        'victory scroll': {'amount': 75},
        'wisdom gem': {'amount': 100},
        'frozen artifact': {'amount': 100},
        'soul crystal': {'amount': 150}
    }
    
    WEARABLE_ITEMS = {
        'armor piece': {'stat': 'strength', 'bonus': 5},
        'cursed amulet': {'stat': 'intelligence', 'bonus': 3},
        "nature's blessing": {'stat': 'agility', 'bonus': 4},
        'healing herb': {'stat': 'agility', 'bonus': 2},
        'mana flower': {'stat': 'intelligence', 'bonus': 4},
        'power ring': {'stat': 'strength', 'bonus': 4},
        'warrior charm': {'stat': 'strength', 'bonus': 3},
        'swift boots': {'stat': 'agility', 'bonus': 5},
        'leather bracer': {'stat': 'agility', 'bonus': 3},
        'arcane pendant': {'stat': 'intelligence', 'bonus': 6},
        'titan gauntlet': {'stat': 'strength', 'bonus': 7},
        'shadow cloak': {'stat': 'agility', 'bonus': 6}
    }
    
    ACTIONABLE_ITEMS = {
        'rusty key': 'key',
        'bone key': 'bone_key',
        'torch': 'light',
        'old map': 'map',
        'ancient medallion': 'offering',
        'demon seal': 'demon_seal',
        'crystal shard': 'crystal',
        'void essence': 'void',
        'primordial rune': 'rune'
    }
    
    QUEST_ITEMS = ['rusty key', 'old map', 'legendary artifact', 'bone key', 
                   'ancient medallion', 'crystal shard', 'demon seal', 'void essence', 'primordial rune']
    
    SHOP_ITEMS = {
        'health potion': 5, 'magic scroll': 8, 'energy drink': 6,
        'experience gem': 15, 'armor piece': 20, 'power ring': 25,
        'swift boots': 25, 'elixir of life': 30, 'soul crystal': 40
    }
    SHOP_TIERS = {
        (1, 2): {
            'health potion':      (5,  'Restores 30 HP',           None),
            'energy drink':       (6,  'Restores 20 HP',           None),
            'torch':              (7,  'Lights the Hidden Alcove', None),
            'experience gem':     (12, 'Grants 50 XP',             None),
            'armor piece':        (15, '+5 STR wearable',          None),
            'power ring':         (18, '+4 STR wearable',          None),
            'warrior charm':      (14, '+3 STR wearable',          None),
            'magic scroll':       (10, 'Restores 25 MP',           'mage'),
        },
        (3, 4): {
            'health potion':      (8,  'Restores 30 HP',           None),
            'vitality tonic':     (12, 'Restores 35 HP',           None),
            'elixir of life':     (30, 'Restores 50 HP',           None),
            'experience gem':     (18, 'Grants 50 XP',             None),
            'wisdom gem':         (28, 'Grants 100 XP',            None),
            'swift boots':        (22, '+5 AGI wearable',          None),
            'leather bracer':     (20, '+3 AGI wearable',          None),
            'arcane pendant':     (30, '+6 INT wearable',          None),
            'soul crystal':       (32, 'Grants 150 XP',            None),
            'magic scroll':       (14, 'Restores 25 MP',           'mage'),
            'mana flower':        (25, '+4 INT wearable',          'mage'),
        },
        (5, 6): {
            'elixir of life':         (38, 'Restores 50 HP',       None),
            'ultimate health potion': (48, 'Full HP restore',      None),
            'vitality tonic':         (14, 'Restores 35 HP',       None),
            'wisdom gem':             (32, 'Grants 100 XP',        None),
            'soul crystal':           (38, 'Grants 150 XP',        None),
            'titan gauntlet':         (48, '+7 STR wearable',      None),
            'shadow cloak':           (44, '+6 AGI wearable',      None),
            "nature's blessing":      (35, '+4 AGI wearable',      None),
            'arcane pendant':         (35, '+6 INT wearable',      None),
            'cursed amulet':          (30, '+3 INT (cursed)',       None),
            'magic scroll':           (18, 'Restores 25 MP',       'mage'),
            'ice crystal':            (40, 'Restores 50 MP',       'mage'),
        },
        (7, 8): {
            'ultimate health potion': (55, 'Full HP restore',      None),
            'elixir of life':         (45, 'Restores 50 HP',       None),
            'soul crystal':           (44, 'Grants 150 XP',        None),
            'wisdom gem':             (38, 'Grants 100 XP',        None),
            'titan gauntlet':         (55, '+7 STR wearable',      None),
            'shadow cloak':           (52, '+6 AGI wearable',      None),
            'cursed amulet':          (38, '+3 INT (cursed)',       None),
            'mana flower':            (42, '+4 INT wearable',      'mage'),
            'ice crystal':            (45, 'Restores 50 MP',       'mage'),
            'weapon cache':           (70, 'Random weapon — gamble!', None),
        },
        (9, 10): {
            'ultimate health potion': (65, 'Full HP restore',      None),
            'elixir of life':         (55, 'Restores 50 HP',       None),
            'soul crystal':           (52, 'Grants 150 XP',        None),
            'wisdom gem':             (48, 'Grants 100 XP',        None),
            'titan gauntlet':         (65, '+7 STR wearable',      None),
            'shadow cloak':           (62, '+6 AGI wearable',      None),
            'arcane pendant':         (55, '+6 INT wearable',      None),
            'cursed amulet':          (50, '+3 INT (cursed)',       None),
            'ice crystal':            (52, 'Restores 50 MP',       'mage'),
            'weapon cache':           (85, 'Random weapon — gamble!', None),
            'experience gem':         (45, 'Grants 50 XP',         None),
        },
    }
    
    # Drop rates
    WEAPON_DROP_CHANCE = 0.65       # 65% of item drops are weapon caches
    ITEM_DROP_BASE_CHANCE = 0.22    # Reduced from 0.35 to keep inventory lean
    GOLD_DROP_CHANCE = 0.6
    GOLD_DROP_MIN = 2
    GOLD_DROP_MAX = 10
    
    # Progression
    BASE_EXPERIENCE_NEEDED = 80    # Reduced to make early levels feel rewarding
    EXPERIENCE_MULTIPLIER = 1.35   # Gentler curve — level 20 reachable by floor 10
    MANA_PER_LEVEL = 10
    INVENTORY_SLOTS_PER_LEVEL = 1
    INVENTORY_SLOTS_PER_TIER = 3
    
    # Combat
    BOSS_DEFEND_REDUCTION = 2
    BOSS_SPECIAL_TURN_FREQUENCY = 3
    BOSS_SPECIAL_HEALTH_THRESHOLD = 0.5
    MIN_ENEMY_DAMAGE = 1
    MIN_BOSS_DAMAGE = 5
    MAGIC_MANA_COST = 15
    MAGIC_DAMAGE_RANGE = (10, 25)
    
    # Magic scaling — mage only (warrior/rogue cannot cast magic)
    MAGIC_MULTIPLIERS = {
        'mage': 1.5,
    }

    # ── Weapon Traits ────────────────────────────────────────────
    # effect_type tags: crit_boost | on_hit_dot | lifesteal |
    #   type_bonus | cursed | first_hit_double | execute_bonus |
    #   opener_bonus | damage_reduction | berserker | damage_pct
    WEAPON_TRAITS = {
        'bleeding': {
            'name': 'Bleeding', 'rarity_min': 'common',
            'desc': 'Inflicts a wound — deals 3 damage/turn for 2 turns',
            'effect': 'on_hit_dot', 'dot_damage': 3, 'dot_turns': 2,
        },
        'swift': {
            'name': 'Swift', 'rarity_min': 'common',
            'desc': '+15% critical hit chance (crits deal 1.75x damage)',
            'effect': 'crit_boost', 'crit_bonus': 15,
        },
        'vampiric': {
            'name': 'Vampiric', 'rarity_min': 'uncommon',
            'desc': 'Heals 12% of damage dealt on every hit',
            'effect': 'lifesteal', 'lifesteal_pct': 0.12,
        },
        'holy': {
            'name': 'Holy', 'rarity_min': 'common',
            'desc': '+65% damage vs undead and demonic enemies',
            'effect': 'type_bonus',
            'bonus_vs': ['skeleton', 'armored skeleton', 'ghoul', 'shadow wraith',
                         'shadow beast', 'lesser demon', 'dark cultist'],
            'bonus_mult': 1.65,
        },
        'cursed': {
            'name': 'Cursed', 'rarity_min': 'uncommon',
            'desc': '+35% damage, but drains 2 HP per combat turn',
            'effect': 'cursed', 'damage_bonus': 0.35, 'hp_drain': 2,
        },
        'savage': {
            'name': 'Savage', 'rarity_min': 'common',
            'desc': 'First strike in combat deals double damage',
            'effect': 'first_hit_double',
        },
        'executioner': {
            'name': 'Executioner', 'rarity_min': 'uncommon',
            'desc': '+65% damage when enemy is below 25% HP',
            'effect': 'execute_bonus', 'threshold': 0.25, 'bonus_mult': 1.65,
        },
        'precise': {
            'name': 'Precise', 'rarity_min': 'common',
            'desc': '+25% damage when enemy is above 75% HP',
            'effect': 'opener_bonus', 'threshold': 0.75, 'bonus_mult': 1.25,
        },
        'venomous': {
            'name': 'Venomous', 'rarity_min': 'common',
            'desc': 'Poisons enemy on hit — deals 2 damage/turn for 3 turns',
            'effect': 'on_hit_dot', 'dot_damage': 2, 'dot_turns': 3, 'dot_type': 'poison',
        },
        'elemental_fire': {
            'name': 'Elemental: Fire', 'rarity_min': 'uncommon',
            'desc': '+65% damage vs ice and frost enemies',
            'effect': 'type_bonus',
            'bonus_vs': ['ice elemental', 'frost titan'],
            'bonus_mult': 1.65,
        },
        'elemental_ice': {
            'name': 'Elemental: Ice', 'rarity_min': 'uncommon',
            'desc': '+65% damage vs fire and flame enemies',
            'effect': 'type_bonus',
            'bonus_vs': ['fire elemental', 'flame lord'],
            'bonus_mult': 1.65,
        },
        'shielded': {
            'name': 'Shielded', 'rarity_min': 'common',
            'desc': 'Reduces all incoming enemy damage by 3 while equipped',
            'effect': 'damage_reduction', 'reduction': 3,
        },
        'berserker': {
            'name': 'Berserker', 'rarity_min': 'rare',
            'desc': '+5% damage per 20% HP missing — max +25% at near death',
            'effect': 'berserker',
        },
        'splooge': {
            'name': 'Splooge',
            'rarity_min': 'mythic',
            'desc': 'On hits dealing 40+ damage, erupts with thick ropes of cum dealing +25 splash damage and minor lifesteal',
            'effect': 'splooge',
            'threshold': 40,
            'splash': 25,
            'lifesteal': 0.08,
        },
    }

    # ── Enemy Weaknesses ─────────────────────────────────────────
    # trait name → damage multiplier when that trait is on your weapon
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

#################################################################################
# DATA-DRIVEN ROOM TEMPLATES
#################################################################################
@dataclass
class RoomTemplate:
    """Data class for room templates"""
    name: str
    description: str
    atmosphere: str
    items: List[str] = field(default_factory=list)
    enemy_count: int = 2
    special_type: Optional[str] = None

class RoomTemplateConfig:
    """Configuration for themed room templates"""
    
    THEME_CONFIG = {
        'dungeon': {
            'floors': (1, 2),
            'enemies': ['sewer rat', 'goblin', 'skeleton', 'prison guard'],
            'templates': [
                RoomTemplate("Damp Prison Cell", "Rusted bars line the walls of this forgotten cell. Water drips from cracked stone.",
                           "The air is thick with the stench of decay and despair.", ['rusty key', 'health potion']),
                RoomTemplate("Guard Barracks", "Overturned bunks and scattered weapons suggest a hasty retreat.",
                           "Bloodstains on the floor tell a grim tale.", ['weapon cache', 'armor piece']),
                RoomTemplate("Torture Chamber", "Chains hang from the ceiling. Ancient implements of pain line the walls.",
                           "Echoes of past suffering seem to whisper in the darkness.", ['cursed amulet', 'bone key']),
                RoomTemplate("Sewage Tunnel", "Putrid water flows through channels in the floor.",
                           "The stench is overwhelming. Rats scurry in the shadows.", ['energy drink', 'torch']),
                RoomTemplate("Abandoned Mess Hall", "Moldy food still sits on overturned tables.",
                           "The prisoners left in a hurry... or were taken.", ['health potion', 'golden coin']),
                RoomTemplate("Warden's Office", "Dusty ledgers and broken furniture fill this administrative room.",
                           "The warden's skeleton still sits at his desk.", ['rusty key', 'power ring']),
                RoomTemplate("Iron Maiden Chamber", "The spiked coffin stands open, waiting for victims.",
                           "Dried blood stains every surface.", ['weapon cache', 'vitality tonic']),
                RoomTemplate("The Pit", "A deep hole descends into darkness. Screams echo from below.",
                           "Crude rope ladders dangle over the edge.", ['bone key', 'experience gem']),
                RoomTemplate("Rat Warren", "Hundreds of small tunnels honeycomb the walls.",
                           "Glowing eyes watch from every shadow.", ['health potion', 'torch']),
                RoomTemplate("Collapsed Hallway", "Rubble blocks most of this corridor.",
                           "Something glints among the debris.", ['weapon cache', 'armor piece']),
                RoomTemplate("Flooded Dungeon", "Water rises to your knees in this submerged chamber.",
                           "Something moves beneath the murky surface.", ['energy drink', 'rusty key']),
                RoomTemplate("Execution Gallery", "Nooses hang from the ceiling in neat rows.",
                           "The floor creaks ominously beneath you.", ['soul crystal', 'golden coin'])
            ]
        },
        'crypt': {
            'floors': (3, 4),
            'enemies': ['armored skeleton', 'shadow wraith', 'corrupted mage', 'ghoul'],
            'templates': [
                RoomTemplate("Ancient Crypt", "Stone sarcophagi line the walls, their lids cracked and displaced.",
                           "An unnatural chill fills the air as the dead stir restlessly.", ['soul crystal', 'weapon cache']),
                RoomTemplate("Necromancer's Study", "Forbidden tomes and ritual circles cover every surface.",
                           "Dark energy crackles around ancient spell books.", ['magic scroll', 'arcane pendant']),
                RoomTemplate("Burial Chamber", "Rows of burial niches stretch into the darkness.",
                           "The dead do not rest peacefully here.", ['health potion', 'wisdom gem']),
                RoomTemplate("Ossuary", "Bones are stacked floor to ceiling in intricate patterns.",
                           "The bones seem to shift and rearrange when you're not looking.", ['bone key', 'cursed amulet']),
                RoomTemplate("Catacomb Maze", "Endless tunnels branch in all directions.",
                           "Skulls embedded in the walls seem to follow your movements.", ['weapon cache', 'torch']),
                RoomTemplate("Embalming Chamber", "Ancient tools and dried organs line dusty shelves.",
                           "The scent of death is overwhelming.", ['vitality tonic', 'soul crystal']),
                RoomTemplate("Tomb of Nobles", "Ornate crypts bear the names of forgotten lords.",
                           "Their restless spirits still guard their treasures.", ['weapon cache', 'arcane pendant']),
                RoomTemplate("Shadow Gallery", "Darkness seems to move with unnatural purpose here.",
                           "Wraiths drift between the pillars.", ['shadow cloak', 'experience gem']),
                RoomTemplate("Charnel Pit", "A massive pile of bones fills this circular chamber.",
                           "Ghouls have been feeding here recently.", ['bone key', 'health potion']),
                RoomTemplate("Lich's Laboratory", "Arcane experiments in undeath cover every workbench.",
                           "The results shamble about mindlessly.", ['magic scroll', 'wisdom gem']),
                RoomTemplate("Mourning Hall", "Rows of candles still burn with spectral flames.",
                           "The temperature drops as you enter.", ['soul crystal', 'ultimate health potion']),
                RoomTemplate("Grave Keeper's Quarters", "Tools for digging and maintaining graves line the walls.",
                           "The keeper never left his post... even in death.", ['rusty key', 'weapon cache'])
            ]
        },
        'elemental': {
            'floors': (5, 6),
            'enemies': ['fire elemental', 'ice elemental', 'lightning wisp', 'stone golem'],
            'templates': [
                RoomTemplate("Inferno Chamber", "Waves of heat emanate from pools of bubbling lava.",
                           "The very air shimmers with intense heat.", ['weapon cache', 'elixir of life']),
                RoomTemplate("Frozen Cavern", "Icicles the size of spears hang from the ceiling.",
                           "Your breath freezes instantly in the frigid air.", ['ice crystal', 'frozen artifact']),
                RoomTemplate("Storm Hall", "Lightning arcs between metal pillars in this charged chamber.",
                           "Static electricity makes your hair stand on end.", ['magic scroll', 'power ring']),
                RoomTemplate("Elemental Nexus", "All four elements clash in chaotic harmony here.",
                           "Fire, ice, lightning, and stone war for dominance.", ['weapon cache', 'titan gauntlet']),
                RoomTemplate("Magma Flow", "Rivers of molten rock flow through carved channels.",
                           "The stone beneath your feet radiates unbearable heat.", ['elixir of life', 'soul crystal']),
                RoomTemplate("Glacier Heart", "A massive block of eternal ice dominates this room.",
                           "Strange shapes are frozen within it.", ['ice crystal', 'weapon cache']),
                RoomTemplate("Thunder Forge", "Lightning strikes continuously at metal anvils.",
                           "The forge produces weapons of pure energy.", ['weapon cache', 'power ring']),
                RoomTemplate("Earth Shrine", "Stone pillars grow from floor to ceiling like ancient trees.",
                           "The rock itself seems alive here.", ['titan gauntlet', 'armor piece']),
                RoomTemplate("Pyroclastic Chamber", "Volcanic ash fills the air in choking clouds.",
                           "Lava bubbles up through cracks in the floor.", ['elixir of life', 'experience gem']),
                RoomTemplate("Permafrost Vault", "Everything is encased in thick, ancient ice.",
                           "The cold here predates civilization.", ['frozen artifact', 'ultimate health potion']),
                RoomTemplate("Capacitor Core", "Massive crystals crackle with stored lightning.",
                           "The energy here is almost tangible.", ['magic scroll', 'arcane pendant']),
                RoomTemplate("Petrified Garden", "Living creatures turned to stone fill this chamber.",
                           "A stone golem tends them like precious flowers.", ['weapon cache', 'wisdom gem'])
            ]
        },
        'dark_magic': {
            'floors': (7, 8),
            'enemies': ['lesser demon', 'dark cultist', 'shadow beast', 'void spawn'],
            'templates': [
                RoomTemplate("Ritual Chamber", "Blasphemous symbols cover every inch of floor and wall.",
                           "Reality seems to warp and twist at the edges of your vision.", ['demon seal', 'weapon cache']),
                RoomTemplate("Shadow Realm Gate", "A portal to darkness pulses with malevolent energy.",
                           "Whispers from beyond beckon you closer.", ['shadow cloak', 'soul crystal']),
                RoomTemplate("Corrupted Sanctum", "What was once a holy place now serves darker powers.",
                           "Desecrated altars radiate profane energy.", ['weapon cache', 'ultimate health potion']),
                RoomTemplate("Abyssal Pit", "A bottomless chasm yawns before you, bridged by bone.",
                           "Screams echo up from unfathomable depths.", ['demon seal', 'arcane pendant']),
                RoomTemplate("Summoning Circle", "Concentric rings of power glow with hellish light.",
                           "The barrier between worlds is thin here.", ['demon seal', 'soul crystal']),
                RoomTemplate("Blood Altar", "Dried blood covers every surface of this profane shrine.",
                           "The stains never fully dry.", ['weapon cache', 'elixir of life']),
                RoomTemplate("Void Cathedral", "Impossible architecture defies natural law.",
                           "Your mind struggles to comprehend the geometry.", ['void essence', 'wisdom gem']),
                RoomTemplate("Cultist Dormitory", "Fanatical devotees once slept in these rows of beds.",
                           "Their nightmares still linger in the air.", ['shadow cloak', 'health potion']),
                RoomTemplate("Demon Scriptorium", "Unholy texts written in blood line the shelves.",
                           "Reading them risks madness.", ['demon seal', 'arcane pendant']),
                RoomTemplate("Torture Sanctum", "Pain is worship here, suffering is prayer.",
                           "The implements are disturbingly well-maintained.", ['ultimate health potion', 'soul crystal']),
                RoomTemplate("Hellforge", "Demonic weapons are crafted in these infernal flames.",
                           "The fire burns with souls instead of wood.", ['weapon cache', 'weapon cache']),
                RoomTemplate("Void Containment", "Reality fractures are held in stasis by dark magic.",
                           "Something vast moves beyond the tears.", ['void essence', 'legendary artifact'])
            ]
        },
        'cosmic': {
            'floors': (9, 10),
            'enemies': ['ancient guardian', 'cosmic horror', 'titan spawn', 'celestial knight'],
            'templates': [
                RoomTemplate("Primordial Vault", "Ancient stone predating civilization stretches endlessly upward.",
                           "The weight of eons presses down upon you.", ['primordial rune', 'titan gauntlet']),
                RoomTemplate("Cosmic Observatory", "Stars that shouldn't exist shine through impossible windows.",
                           "Your mind struggles to comprehend the geometry of this place.", ['weapon cache', 'wisdom gem']),
                RoomTemplate("Hall of Eternity", "Time flows strangely in this ageless corridor.",
                           "Past, present, and future seem to overlap here.", ['soul crystal', 'legendary artifact']),
                RoomTemplate("Reality Fracture", "The laws of physics break down in this impossible space.",
                           "You see things that cannot be and yet are.", ['void essence', 'ultimate health potion']),
                RoomTemplate("Titan's Tomb", "A being the size of a mountain lies entombed here.",
                           "Its chest still rises and falls with ancient breathing.", ['titan gauntlet', 'weapon cache']),
                RoomTemplate("Stellar Forge", "Stars are born and die in this cosmic furnace.",
                           "The universe itself is shaped here.", ['weapon cache', 'wisdom gem']),
                RoomTemplate("Time Vault", "Clocks of every era tick in different rhythms.",
                           "Some run backwards, others skip forward unpredictably.", ['soul crystal', 'experience gem']),
                RoomTemplate("Celestial Armory", "Weapons forged in the hearts of dying stars line the walls.",
                           "Each blade hums with cosmic power.", ['weapon cache', 'weapon cache']),
                RoomTemplate("Ancient Library", "Books containing the secrets of creation fill endless shelves.",
                           "Some texts predate the universe itself.", ['wisdom gem', 'legendary artifact']),
                RoomTemplate("Guardian Barracks", "Eternal sentinels stand vigil in perfect formation.",
                           "They have not moved in millennia.", ['titan gauntlet', 'ultimate health potion']),
                RoomTemplate("Void Observatory", "Windows look out into absolute nothingness.",
                           "The void gazes back into you.", ['void essence', 'primordial rune']),
                RoomTemplate("Creation Chamber", "Reality itself is malleable in this sacred space.",
                           "Worlds are born and die at a thought.", ['legendary artifact', 'soul crystal'])
            ]
        }
    }
    
    SPECIAL_ROOMS = [
        RoomTemplate("Long Hallway", "A long corridor stretches before you, lit by flickering torches.",
                   "Shadows dance menacingly on the walls.", ['torch', 'weapon cache']),
        RoomTemplate("Treasure Room", "Glittering wealth fills this chamber, but it's well guarded.",
                   "Gold and gems reflect torchlight in dazzling patterns.", 
                   ['golden coin', 'weapon cache', 'experience gem'], 2, 'treasure'),
        RoomTemplate("Forgotten Game Room", "Cobwebs fill this tiny chamber. A single stone pedestal stands in the center.",
                   "Carved into the pedestal: 'FOR THE BOLD. MAY FORTUNE FAVOUR YOU.' A twenty-sided die rests on top.",
                   ["gambler's d20"], 0, 'easter_egg'),
        RoomTemplate("Hidden Alcove", "A dark alcove with a single torch sconce on the wall.",
                   "The sconce looks like it could hold a torch. Something feels hidden here.",
                   ['torch'], 1, 'secret'),
        RoomTemplate("Sacred Shrine", "An ancient shrine with a stone altar in the center.",
                   "The altar has a circular indentation. Strange energy emanates from it.",
                   ['health potion', 'golden coin'], 1, 'altar'),
        RoomTemplate("Locked Vault", "A sealed vault with an ornate chest at its center.",
                   "The chest has an old rusty keyhole. It hasn't been opened in centuries.",
                   ['weapon cache', 'golden coin'], 2, 'vault'),
        RoomTemplate("Bone Crypt", "Ancient bones form intricate patterns on the walls.",
                   "A sealed bone door blocks deeper access. It has a skeletal keyhole.",
                   [], 1, 'bone_vault'),
        RoomTemplate("Demon Gate", "A massive demonic portal pulses with dark energy.",
                   "The gate is sealed with arcane chains. A demon seal indent is visible.",
                   ['demon seal', 'soul crystal'], 2, 'demon_gate'),
        RoomTemplate("Crystal Chamber", "Crystalline formations cover every surface.",
                   "A dormant crystal mechanism awaits activation.",
                   ['crystal shard', 'magic scroll'], 1, 'crystal_room'),
        RoomTemplate("Void Tear", "Reality fractures here, creating a swirling void portal.",
                   "The portal is unstable. Void essence could stabilize it.",
                   ['void essence', 'weapon cache'], 1, 'void_portal'),
        RoomTemplate("Primordial Monument", "An ancient stone monument covered in runic inscriptions.",
                   "The runes glow faintly, waiting for the right key.",
                   ['primordial rune', 'legendary artifact'], 1, 'rune_monument'),
        
        # ====================== NEW: PLEASURE SANCTUM ======================
        RoomTemplate("Pleasure Sanctum", 
                     "A vast circular chamber draped in black and crimson silk. Glowing pink runes pulse across the walls.",
                     "Moans, wet slapping sounds, and ecstatic cries echo from every direction.",
                     ['vibrating butt plug', 'the eternal splooger'], 0, 'sex_dungeon')
    ]
    
    @classmethod
    def get_templates_for_floor(cls, floor: int) -> List[RoomTemplate]:
        """Get room templates for specified floor"""
        templates = []
        for theme_name, config in cls.THEME_CONFIG.items():
            if config['floors'][0] <= floor <= config['floors'][1]:
                templates.extend(config['templates'])
                break
        templates.extend(cls.SPECIAL_ROOMS)
        return templates
    
    @classmethod
    def get_enemies_for_floor(cls, floor: int) -> List[str]:
        """Get enemy pool for floor"""
        return GameConstants.FLOOR_THEMES.get(floor, ['goblin'])

#################################################################################
# BOSS CONFIGURATION GENERATOR
#################################################################################
class BossConfig:
    """Generate boss configurations dynamically"""
    
    BOSS_DATA = {
        1:  {'name': 'Arena Champion',    'special': "CHAMPION'S FURY"},
        2:  {'name': 'Necromancer Lord',  'special': 'DEATH CURSE'},
        3:  {'name': 'Crypt Overlord',    'special': 'SOUL DRAIN'},
        4:  {'name': 'Shadow King',       'special': 'SHADOW STRIKE'},
        5:  {'name': 'Flame Lord',        'special': 'INFERNO'},
        6:  {'name': 'Frost Titan',       'special': 'GLACIAL STORM'},
        7:  {'name': 'Demon Prince',      'special': 'HELLFIRE'},
        8:  {'name': 'Void Archon',       'special': 'VOID RIFT'},
        9:  {'name': 'Primordial Beast',  'special': 'ANCIENT WRATH'},
        10: {'name': 'Reality Breaker',   'special': 'COSMIC ANNIHILATION'},
    }

    # 10 weapons per boss per class, ordered by tier:
    #   indices 0-4  → GOOD   (solid upgrade, weight 12 each = 60% chance)
    #   indices 5-7  → GREAT  (notably powerful, weight 10 each = 30% chance)
    #   indices 8-9  → INSANE (game-changing, weight 5 each = 10% chance)
    BOSS_WEAPON_POOLS = {
        1: {  # Arena Champion
            'warrior': [
                'Gladius of Victory', 'Iron Arena Sword', "Champion's Cleaver",
                'Battle-Worn Blade', "Warrior's Greatsword",
                "Vanguard's Edge", 'Arena Master Sword', "Conqueror's Blade",
                "Champion's Fury", 'Undying Legend',
            ],
            'mage': [
                "Champion's Scepter", 'Arena Orb', 'Battle-Mage Crystal',
                'Combat Staff', "Gladiator's Wand",
                "Conqueror's Staff", "Vanquisher's Tome", 'Master Orb',
                'Fury Scepter', 'Undying Focus',
            ],
            'rogue': [
                'Twin Blades of Honor', 'Arena Knives', "Champion's Shiv",
                'Battle-Worn Rapier', 'Iron Short Bow',
                "Conqueror's Dagger", "Vanquisher's Needle", "Vanguard's Claw",
                "Champion's Twin Fangs", 'Undying Edge',
            ],
        },
        2: {  # Necromancer Lord
            'warrior': [
                'Soul Reaper', 'Bone Cleaver', 'Undead Slayer',
                'Crypt Breaker', 'Death Hammer',
                'Soul Crusher', "Necromancer's Blade", 'Void Sword',
                'Death Bringer', 'Soul Annihilator',
            ],
            'mage': [
                'Death Staff', 'Bone Wand', 'Cursed Tome',
                'Shadow Orb', 'Undead Crystal',
                'Soul Staff', "Lich's Scepter", 'Void Wand',
                "Death's Instrument", 'Soul Obliterator',
            ],
            'rogue': [
                'Shadow Fang', 'Bone Shiv', "Death's Needle",
                'Cursed Rapier', 'Undead Bow',
                'Soul Dagger', "Lich's Claw", 'Void Edge',
                "Death's Kiss", 'Soul Ripper',
            ],
        },
        3: {  # Crypt Overlord
            'warrior': [
                'Bone Crusher', 'Crypt Hammer', 'Tomb Breaker',
                'Ancient Grave Axe', 'Burial Sword',
                "Overlord's Blade", 'Crypt Master Sword', 'Eternal Bone Axe',
                'Soul Cleaver', "Overlord's Reckoning",
            ],
            'mage': [
                'Crypt Scepter', 'Ossuary Wand', 'Tomb Crystal',
                'Ancient Bone Staff', 'Burial Orb',
                "Overlord's Tome", 'Crypt Master Staff', 'Eternal Bone Wand',
                'Soul Scepter', "Overlord's Devastation",
            ],
            'rogue': [
                'Grave Shiv', 'Crypt Needle', 'Tomb Dagger',
                'Ancient Bone Rapier', 'Burial Blade',
                "Overlord's Claw", 'Crypt Master Bow', 'Eternal Bone Shiv',
                "Overlord's Doom", 'Grave of Eternity',
            ],
        },
        4: {  # Shadow King
            'warrior': [
                'Shadowbane', 'Dark Greatsword', 'Umbra Blade',
                'Shade Axe', 'Night Hammer',
                "Shadow King's Edge", 'Umbra Cleaver', 'Darkness Blade',
                "Shadow's Reckoning", "Night's End",
            ],
            'mage': [
                'Dark Orb', 'Shadow Staff', 'Umbra Crystal',
                'Shade Tome', 'Night Wand',
                "Shadow King's Scepter", 'Umbra Staff', 'Darkness Orb',
                "Shadow's Devastation", "Night's Obliteration",
            ],
            'rogue': [
                'Night Piercer', 'Shadow Needle', 'Umbra Dagger',
                'Shade Rapier', 'Dark Bow',
                "Shadow King's Claw", 'Umbra Shiv', 'Darkness Blade',
                "Shadow's Doom", "Night's Annihilation",
            ],
        },
        5: {  # Flame Lord
            'warrior': [
                'Flamebringer', 'Ember Sword', 'Inferno Axe',
                'Magma Hammer', 'Cinder Blade',
                "Flame King's Edge", 'Pyre Cleaver', 'Inferno Greatsword',
                "Solar Reckoning", "Flame's Annihilation",
            ],
            'mage': [
                'Inferno Staff', 'Ember Wand', 'Magma Crystal',
                'Cinder Tome', 'Pyre Orb',
                "Flame King's Scepter", 'Pyroclastic Staff', 'Inferno Wand',
                'Solar Devastation', "Flame's Obliteration",
            ],
            'rogue': [
                'Cinder Bow', 'Ember Shiv', 'Inferno Needle',
                'Magma Dagger', 'Pyre Rapier',
                "Flame King's Claw", 'Pyroclastic Shiv', 'Inferno Dagger',
                'Solar Doom', "Flame's End",
            ],
        },
        6: {  # Frost Titan
            'warrior': [
                'Frostbane Greatsword', 'Glacial Axe', 'Ice Hammer',
                'Frozen Blade', 'Tundra Sword',
                "Frost Giant's Edge", 'Eternal Ice Greatsword', 'Blizzard Axe',
                'Absolute Zero Blade', "Winter's End",
            ],
            'mage': [
                'Staff of Eternal Winter', 'Glacier Wand', 'Frozen Crystal',
                'Blizzard Tome', 'Tundra Orb',
                "Frost Giant's Scepter", 'Eternal Ice Staff', 'Permafrost Wand',
                'Absolute Zero Staff', "Winter's Obliteration",
            ],
            'rogue': [
                'Icicle Piercer', 'Frozen Shiv', 'Glacier Needle',
                'Blizzard Dagger', 'Tundra Bow',
                "Frost Giant's Claw", 'Eternal Ice Rapier', 'Permafrost Shiv',
                'Absolute Zero Edge', "Winter's Doom",
            ],
        },
        7: {  # Demon Prince
            'warrior': [
                "Demon's Edge", 'Hellfire Sword', 'Abyssal Axe',
                'Infernal Hammer', 'Brimstone Blade',
                "Demon Prince's Greatsword", 'Hellgate Cleaver', 'Abyssal Greatsword',
                'Damnation Blade', "Hell's Reckoning",
            ],
            'mage': [
                'Abyssal Staff', 'Hellfire Wand', 'Demon Crystal',
                'Infernal Tome', 'Brimstone Orb',
                "Demon Prince's Scepter", 'Hellgate Staff', 'Abyssal Wand',
                'Damnation Staff', "Hell's Obliteration",
            ],
            'rogue': [
                'Soul Piercer', 'Hellfire Shiv', 'Abyssal Needle',
                'Infernal Dagger', 'Brimstone Bow',
                "Demon Prince's Claw", 'Hellgate Rapier', 'Abyssal Shiv',
                'Damnation Edge', "Hell's Doom",
            ],
        },
        8: {  # Void Archon
            'warrior': [
                'Voidreaver', 'Reality Sword', 'Entropy Axe',
                'Oblivion Hammer', 'Nihilum Blade',
                "Void Archon's Greatsword", 'Reality Render', 'Entropy Cleaver',
                'Universe Ender', 'The Final Void',
            ],
            'mage': [
                'Reality Staff', 'Void Wand', 'Entropy Crystal',
                'Oblivion Tome', 'Nihilum Orb',
                "Void Archon's Scepter", 'Reality Warper', 'Entropy Staff',
                'Universe Obliterator', 'The Final Void Staff',
            ],
            'rogue': [
                'Oblivion Blade', 'Void Shiv', 'Entropy Needle',
                'Reality Dagger', 'Nihilum Bow',
                "Void Archon's Claw", 'Reality Ripper', 'Entropy Rapier',
                'Universe Destroyer', 'The Final Void Edge',
            ],
        },
        9: {  # Primordial Beast
            'warrior': [
                'Titan Slayer', 'Primordial Axe', 'Ancient Fang Sword',
                'Primal Hammer', 'Elder Blade',
                "Beast King's Greatsword", 'Primordial Reckoner', 'Ancient Wrath Axe',
                "Titan's End", 'The Primordial Annihilator',
            ],
            'mage': [
                'Primordial Staff', 'Ancient Wand', 'Titan Crystal',
                'Primal Tome', 'Elder Orb',
                "Beast King's Scepter", 'Primordial Power Staff', 'Ancient Wrath Wand',
                "Titan's Devastation", 'The Primordial Obliterator',
            ],
            'rogue': [
                'Beast Fang', 'Primordial Shiv', 'Ancient Claw Dagger',
                'Primal Bow', 'Elder Rapier',
                "Beast King's Needle", 'Primordial Render', 'Ancient Wrath Shiv',
                "Titan's Doom", 'The Primordial Destroyer',
            ],
        },
        10: {  # Reality Breaker
            'warrior': [
                'Worldender', 'Cosmos Blade', 'Universe Axe',
                'Reality Hammer', 'Eternal Sword',
                "Reality Breaker's Greatsword", 'Cosmos Render', 'Universe Cleaver',
                'The Absolute End', 'Oblivion Incarnate',
            ],
            'mage': [
                'Cosmos Staff', 'Universe Wand', 'Reality Crystal',
                'Eternal Tome', 'Worldend Orb',
                "Reality Breaker's Scepter", 'Cosmos Power Staff', 'Universe Warper',
                'The Absolute Obliteration', "Oblivion's Voice",
            ],
            'rogue': [
                'Reality Ripper', 'Cosmos Edge', 'Universe Shiv',
                'Eternal Bow', 'Worldend Dagger',
                "Reality Breaker's Claw", 'Cosmos Render Blade', 'Universe Destroyer Shiv',
                'The Absolute Doom', "Oblivion's Touch",
            ],
        },
    }

    # Damage multiplier and spawn weight for each pool index (0-9)
    #   Positions 0-4  = GOOD   (1.00-1.05x damage, weight 12 each)
    #   Positions 5-7  = GREAT  (1.20-1.30x damage, weight 10 each)
    #   Positions 8-9  = INSANE (1.60-1.70x damage, weight  5 each)
    WEAPON_TIER_MAP = [
        (1.00, 12), (1.00, 12), (1.00, 12), (1.00, 12), (1.05, 12),  # GOOD   (60%)
        (1.20, 10), (1.25, 10), (1.30, 10),                           # GREAT  (30%)
        (1.60,  5), (1.70,  5),                                        # INSANE (10%)
    ]
    
    BOSS_ROOMS = {
        1: ("Gladiator Arena", "A massive circular arena with sand-covered floors.", 
            "Ghostly cheers echo from unseen crowds. The Arena Champion awaits!"),
        2: ("Necromancer's Sanctum", "Dark energy swirls around an obsidian throne.",
            "Death itself seems to bow before the Necromancer Lord!"),
        3: ("Tomb of the Overlord", "A vast crypt dominated by a massive stone sarcophagus.",
            "Ancient power radiates from the awakening Crypt Overlord!"),
        4: ("Shadow Throne Room", "Darkness coalesces into a throne of pure shadow.",
            "The Shadow King emerges from the void itself!"),
        5: ("Infernal Throne", "Rivers of lava flow around a platform of volcanic rock.",
            "The Flame Lord rises in a pillar of fire!"),
        6: ("Frozen Cavern", "A bone-chilling cavern covered in ancient ice.",
            "The Frost Titan awakens from its eternal slumber!"),
        7: ("Abyssal Gate", "A massive portal to the demonic realm dominates this chamber.",
            "The Demon Prince steps through from the abyss!"),
        8: ("Void Nexus", "Reality fractures and bends around this impossible space.",
            "The Void Archon manifests from nothingness!"),
        9: ("Primordial Chamber", "Ancient stone predating time itself forms this vast arena.",
            "The Primordial Beast, older than the world, awakens!"),
        10: ("Reality's Edge", "The fabric of existence itself unravels in this final chamber.",
             "The Reality Breaker threatens to unmake all creation!")
    }
    
    @classmethod
    def generate(cls, floor: int) -> Dict[str, Any]:
        """Generate complete boss configuration"""
        data = cls.BOSS_DATA[floor]
        return {
            'floor': floor,
            'name': data['name'],
            'base_health': 120 + (floor - 1) * 20,
            'health_scaling': 8 + (floor - 1),
            'damage': 22 + (floor - 1) * 2,
            'exp_reward': 150 + (floor - 1) * 30,
            'special_attack': data['special'],
            'special_bonus': 12 + (floor - 1) * 2,
            'stat_bonus': 2 + (floor - 1) // 2,
            'min_level': floor * 2,
        }
    
    @classmethod
    def generate_boss_weapon(cls, floor: int, player: 'Player') -> Dict:
        """Pick a boss weapon from the tier-weighted pool and scale its damage.

        Pool breakdown per boss per class (10 total):
          Indices 0-4  GOOD   → weight 12 each = 60%  → tier mult 1.00-1.05x
          Indices 5-7  GREAT  → weight 10 each = 30%  → tier mult 1.20-1.30x
          Indices 8-9  INSANE → weight  5 each = 10%  → tier mult 1.60-1.70x
        """
        pool = cls.BOSS_WEAPON_POOLS[floor][player.character_class]
        weights = [cls.WEAPON_TIER_MAP[i][1] for i in range(len(pool))]
        chosen_idx = random.choices(range(len(pool)), weights=weights, k=1)[0]
        weapon_name = pool[chosen_idx]
        tier_mult, _ = cls.WEAPON_TIER_MAP[chosen_idx]

        # Tier label for display
        if chosen_idx < 5:
            tier_label, rarity = 'GOOD', 'legendary'
        elif chosen_idx < 8:
            tier_label, rarity = 'GREAT', 'legendary'
        else:
            tier_label, rarity = 'INSANE', 'mythic'

        weapon_type = GameConstants.CLASSES[player.character_class]['weapon_types'][0]

        # Base damage: floor-scaled boost over the player's current weapon
        if floor <= 4:
            boost_percent = random.uniform(0.15, 0.25)
        elif floor <= 7:
            boost_percent = random.uniform(0.25, 0.35)
        else:
            boost_percent = random.uniform(0.35, 0.50)

        rarity_data = GameConstants.WEAPON_RARITIES['legendary']
        base_damage = random.randint(rarity_data['base_min'], rarity_data['base_max']) + (player.level * 2)
        base_weapon_damage = int(base_damage * rarity_data['multiplier'])

        if player.weapon:
            boosted_damage = int(player.weapon['damage'] * (1 + boost_percent))
            final_damage = max(base_weapon_damage, boosted_damage)
            # Early-floor damage caps prevent one-shotting
            if floor <= 2:
                final_damage = min(final_damage, 45 + player.level * 3)
            elif floor <= 4:
                final_damage = min(final_damage, 60 + player.level * 4)
            elif floor <= 6:
                final_damage = min(final_damage, 80 + player.level * 5)
        else:
            final_damage = base_weapon_damage

        # Apply tier multiplier on top of base scaling
        final_damage = int(final_damage * tier_mult)

        boss_weapon = {
            'name': weapon_name,
            'damage': final_damage,
            'type': weapon_type,
            'rarity': rarity,
            'base_name': weapon_name,
            'tier_label': tier_label,
        }
        return boss_weapon
    
    @classmethod
    def get_boss_room_template(cls, floor: int) -> RoomTemplate:
        """Get boss room template"""
        room_data = cls.BOSS_ROOMS[floor]
        return RoomTemplate(
            room_data[0], room_data[1], room_data[2],
            ["champion's prize", 'ultimate health potion'],
            enemy_count=0, special_type='boss'
        )

#################################################################################
# UNIFIED ITEM HANDLER
#################################################################################
class ItemHandler:
    """Centralized item management system"""
    
    @staticmethod
    def use_item(player: 'Player', category: str, item_name: Optional[str] = None) -> bool:
        """Generic item usage"""
        item_dict = ItemHandler._get_item_dict(category)
        
        if not item_name:
            available = [i for i in player.inventory if i in item_dict]
            if not available:
                print(f"No {category} items!")
                return False
            item_name = ItemHandler._show_menu(available, item_dict, category)
            if not item_name:
                return False
        
        if item_name in player.inventory and item_name in item_dict:
            player.inventory.remove(item_name)
            return ItemHandler._apply_effect(player, item_name, item_dict[item_name], category)
        
        print(f"You don't have '{item_name}' or it's not a {category} item.")
        return False
    
    @staticmethod
    def _get_item_dict(category: str) -> Dict:
        """Get item dictionary by category"""
        return {
            'healing': GameConstants.HEALING_ITEMS,
            'experience': GameConstants.EXPERIENCE_ITEMS,
            'wearable': GameConstants.WEARABLE_ITEMS
        }.get(category, {})
    
    @staticmethod
    def _show_menu(items: List[str], item_dict: Dict, category: str) -> Optional[str]:
        """Show item selection menu"""
        print(f"Available {category} items:")
        for i, item in enumerate(items, 1):
            effect = item_dict[item]
            desc = ItemHandler._format_effect(effect)
            print(f"{i}. {item} - {desc}")
        
        try:
            choice = int(input(f"Choose (1-{len(items)}): ")) - 1
            return items[choice] if 0 <= choice < len(items) else None
        except (ValueError, KeyboardInterrupt):
            print("Cancelled.")
            return None
    
    @staticmethod
    def _format_effect(effect: Dict) -> str:
        """Format effect description"""
        if 'heal' in effect:
            heal_text = "full heal" if effect['heal'] == 'full' else f"+{effect['heal']}"
            return f"{heal_text} {effect['type']}"
        elif 'amount' in effect:
            return f"+{effect['amount']} exp"
        elif 'bonus' in effect:
            return f"+{effect['bonus']} {effect['stat']}"
        return "special"
    
    @staticmethod
    def _apply_effect(player: 'Player', item_name: str, effect: Dict, category: str) -> bool:
        """Apply item effect"""
        if category == 'healing':
            if effect['type'] == 'health':
                if effect['heal'] == 'full':
                    heal = player.max_health - player.health
                    player.health = player.max_health
                else:
                    heal = min(effect['heal'], player.max_health - player.health)
                    player.health += heal
                print(f"+ Restored {heal} health!")
            else:  # mana
                mana = min(effect['heal'], player.max_mana - player.mana)
                player.mana += mana
                print(f"+ Restored {mana} mana!")
        
        elif category == 'experience':
            player.gain_experience(effect['amount'])
        
        elif category == 'wearable':
            player.stats[effect['stat']] += effect['bonus']
            player.wearables.append({'item': item_name, 'stat': effect['stat'], 'bonus': effect['bonus']})
            print(f"*** Equipped {item_name}! +{effect['bonus']} {effect['stat']}")
        
        return True

#################################################################################
# CENTRALIZED DAMAGE CALCULATOR
#################################################################################
class DamageCalculator:
    """Unified damage calculation system"""
    
    @staticmethod
    def calculate_player_damage(
        player: 'Player',
        enemy_name: str = None,
        enemy_hp: int = None,
        enemy_max_hp: int = None,
        first_hit: bool = False,
    ) -> int:
        """Calculate player damage including traits, crits, and enemy weaknesses."""
        # Golden Gun instant kill
        if player.weapon and player.weapon.get('special') == 'instant_kill':
            if player.weapon.get('uses_remaining', 0) > 0:
                player.weapon['uses_remaining'] -= 1
                remaining = player.weapon['uses_remaining']
                print(f"*** THE {player.weapon['base_name'].upper()} FIRES!")
                print(f"*** INSTANT OBLITERATION! ({remaining}/6 remaining)")
                if remaining <= 0:
                    print(f"The {player.weapon['base_name']} crumbles to dust...")
                    player.weapon = None
                return 99999

        if not player.weapon:
            return random.randint(1, 5)

        base = player.weapon['damage']
        strength_bonus = random.randint(1, max(1, player.stats['strength'] // 3))
        rarity = player.weapon.get('rarity', 'common')
        multiplier = GameConstants.WEAPON_RARITIES[rarity]['multiplier']
        damage = (base + strength_bonus) * multiplier

        traits = player.weapon.get('traits', [])
        trait_notes = []

        # ── Passive damage-modifying traits ──────────────────────
        for trait_key in traits:
            td = GameConstants.WEAPON_TRAITS.get(trait_key, {})
            effect = td.get('effect')

            if effect == 'cursed':
                damage *= (1 + td['damage_bonus'])
                # HP drain is applied in fight_enemy per turn, not here

            elif effect == 'first_hit_double' and first_hit:
                damage *= 2
                trait_notes.append("SAVAGE first strike!")

            elif effect == 'execute_bonus' and enemy_hp is not None and enemy_max_hp:
                if enemy_hp / enemy_max_hp < td['threshold']:
                    damage *= td['bonus_mult']
                    trait_notes.append("EXECUTIONER bonus!")

            elif effect == 'opener_bonus' and enemy_hp is not None and enemy_max_hp:
                if enemy_hp / enemy_max_hp > td['threshold']:
                    damage *= td['bonus_mult']
                    trait_notes.append("PRECISE opener bonus!")

            elif effect == 'berserker':
                hp_ratio = player.health / max(1, player.max_health)
                missing = max(0, 1.0 - hp_ratio)
                berserker_mult = 1 + min(0.25, (missing // 0.20) * 0.05)
                if berserker_mult > 1.0:
                    damage *= berserker_mult
                    trait_notes.append(f"BERSERKER +{int((berserker_mult - 1) * 100)}%!")

        # ── Critical hit (Luck + Swift trait) ────────────────────
        base_crit = 5 + max(0, player.stats.get('luck', 10) - 10) * 0.5
        swift_bonus = sum(
            GameConstants.WEAPON_TRAITS['swift']['crit_bonus']
            for t in traits if t == 'swift'
        )
        crit_chance = min(60, base_crit + swift_bonus)  # cap at 60%
        is_crit = random.random() < crit_chance / 100
        if is_crit:
            damage *= 1.75
            trait_notes.append("CRITICAL HIT!")

        # ── Enemy weakness multiplier ─────────────────────────────
        if enemy_name:
            en = enemy_name.lower()
            weaknesses = GameConstants.ENEMY_WEAKNESSES.get(en, {})
            for trait_key in traits:
                if trait_key in weaknesses:
                    w_mult = weaknesses[trait_key]
                    if w_mult > 1.0:
                        damage *= w_mult
                        td_name = GameConstants.WEAPON_TRAITS.get(trait_key, {}).get('name', trait_key)
                        trait_notes.append(f"{td_name} WEAKNESS! x{w_mult}")

        # ── Paladin passive: Faith-scaled holy aura ──────────────
        if player.character_class == 'paladin' and 'holy' in traits:
            faith = player.stats.get('faith', 5)
            aura_bonus = 1.0 + 0.25 + max(0, (faith - 10) * 0.015)
            damage *= aura_bonus
            trait_notes.append(f"Holy Aura! ({int((aura_bonus-1)*100)}% bonus)")

        # ── Berserker passive: built-in rage scaling ──────────────
        if player.character_class == 'berserker':
            hp_ratio = player.health / max(1, player.max_health)
            missing = max(0, 1.0 - hp_ratio)
            built_in_berserk = 1 + min(0.30, (missing // 0.20) * 0.06)
            if built_in_berserk > 1.0:
                damage *= built_in_berserk
                trait_notes.append(f"BERSERKER RAGE +{int((built_in_berserk-1)*100)}%!")
    # Lust aura
        lust = player.stats.get('lust', 5)
        if lust > 5:
            damage = int(damage * (1 + (lust - 5) * 0.035))
            trait_notes.append(f"LUST AURA (+{int((lust-5)*3.5)}% dmg)")

        # Splooge trait
        for trait_key in traits:
            if trait_key == 'splooge' and damage >= GameConstants.WEAPON_TRAITS['splooge']['threshold']:
                td = GameConstants.WEAPON_TRAITS['splooge']
                trait_notes.append(f"*** SPL00GE! +{td['splash']} splash damage ***")

        # Print any trait proc messages
        for note in trait_notes:
            print(f"  ✦ {note}")

        return max(1, int(damage))
    
    @staticmethod
    def calculate_enemy_damage(base_damage: int, player: 'Player', is_boss: bool = False) -> int:
        """Calculate enemy damage scaling with agility defense and player weapon power.
        
        Regular enemies apply weapon-aware pressure: the harder the player hits,
        the harder enemies fight back, keeping healing items relevant throughout.
        Bosses use their own scaling and are not affected by weapon pressure.
        """
        agility_defense = random.randint(1, player.stats['agility'] // (2 if is_boss else 3))

        # Weapon-aware pressure (regular enemies only)
        weapon_pressure = 0
        if not is_boss and player.weapon:
            weapon_dmg = player.weapon['damage']
            pressure_steps = weapon_dmg // 20
            if pressure_steps > 0:
                weapon_pressure = random.randint(pressure_steps, max(pressure_steps, weapon_dmg // 8))

        # Vitality damage reduction: 1 point per 15 vitality above 10
        vitality = player.stats.get('vitality', 10)
        vitality_reduction = max(0, (vitality - 10) // 15)

        # Shielded trait: flat -3 incoming damage
        shield_reduction = 0
        if player.weapon:
            for trait_key in player.weapon.get('traits', []):
                if GameConstants.WEAPON_TRAITS.get(trait_key, {}).get('effect') == 'damage_reduction':
                    shield_reduction += GameConstants.WEAPON_TRAITS[trait_key]['reduction']

        final = base_damage + weapon_pressure - agility_defense - vitality_reduction - shield_reduction
        min_damage = GameConstants.MIN_BOSS_DAMAGE if is_boss else GameConstants.MIN_ENEMY_DAMAGE
        return max(min_damage, final)

#################################################################################
# WEAPON COMPARISON SYSTEM
#################################################################################
class WeaponComparison:
    """Compare weapons and show detailed stats"""
    
    @staticmethod
    def compare_weapons(new_weapon: Dict, current_weapon: Optional[Dict], player: 'Player') -> str:
        """Generate detailed weapon comparison"""
        lines = []
        lines.append("\n" + "="*50)
        lines.append("WEAPON COMPARISON")
        lines.append("="*50)
        
        # New weapon stats
        new_dmg = new_weapon['damage']
        new_rarity = new_weapon.get('rarity', 'common')
        new_mult = GameConstants.WEAPON_RARITIES[new_rarity]['multiplier']
        
        # Calculate effective damage with strength bonus
        str_bonus_avg = player.stats['strength'] // 3
        new_effective = int((new_dmg + str_bonus_avg) * new_mult)
        
        def fmt_traits(weapon):
            traits = weapon.get('traits', [])
            if not traits:
                return "  Traits: none"
            parts = []
            for t in traits:
                td = GameConstants.WEAPON_TRAITS.get(t, {})
                parts.append(f"    ◈ {td.get('name', t)}: {td.get('desc', '')}")
            return "  Traits:\n" + "\n".join(parts)

        lines.append(f"\nNEW: {new_weapon['name']}")
        lines.append(f"  Rarity: {new_rarity.upper()}")
        lines.append(f"  Base Damage: {new_dmg}  |  Multiplier: {new_mult}x")
        lines.append(f"  Avg Effective Damage: ~{new_effective}")
        lines.append(fmt_traits(new_weapon))

        if current_weapon:
            curr_dmg = current_weapon['damage']
            curr_rarity = current_weapon.get('rarity', 'common')
            curr_mult = GameConstants.WEAPON_RARITIES[curr_rarity]['multiplier']
            curr_effective = int((curr_dmg + str_bonus_avg) * curr_mult)

            lines.append(f"\nCURRENT: {current_weapon['name']}")
            lines.append(f"  Rarity: {curr_rarity.upper()}")
            lines.append(f"  Base Damage: {curr_dmg}  |  Multiplier: {curr_mult}x")
            lines.append(f"  Avg Effective Damage: ~{curr_effective}")
            lines.append(fmt_traits(current_weapon))

            diff = new_effective - curr_effective
            if diff > 0:
                lines.append(f"\n>>> UPGRADE: +{diff} damage ({int((diff/max(1,curr_effective))*100)}% more)")
            elif diff < 0:
                lines.append(f"\n>>> DOWNGRADE: {diff} damage ({int((diff/max(1,curr_effective))*100)}%)")
            else:
                lines.append(f"\n>>> SIMILAR DAMAGE — compare traits to decide!")
        else:
            lines.append(f"\nCURRENT: None (unarmed)")
            lines.append(f">>> HUGE UPGRADE!")

        lines.append("="*50)
        return '\n'.join(lines)

#################################################################################
# VISUAL MAP GENERATOR (COMPASS STYLE)
#################################################################################
class MapGenerator:
    """Generate ASCII visual map of explored rooms"""
    
    @staticmethod
    def generate_visual_map(floors: Dict[int, Dict[str, 'Room']], 
                           current_floor: int, 
                           current_room: str,
                           visited_rooms: Set[str]) -> str:
        """Generate expanded compass-style ASCII map for current floor"""
        floor_rooms = floors[current_floor]
        visited_floor = [r for r in visited_rooms if r in floor_rooms]
        
        if not visited_floor:
            return "No rooms explored on this floor yet!"
        
        current = floor_rooms[current_room]
        
        lines = []
        lines.append("╔" + "═" * 78 + "╗")
        lines.append(f"║ FLOOR {current_floor} COMPASS MAP - EXPANDED VIEW{' ' * (78 - len(f' FLOOR {current_floor} COMPASS MAP - EXPANDED VIEW'))}║")
        lines.append("╠" + "═" * 78 + "╣")
        
        # Get rooms in each direction from current room (with depth)
        def get_room_chain(direction, max_depth=3):
            """Get chain of rooms in a direction"""
            chain = []
            current_id = current_room
            
            for depth in range(max_depth):
                if current_id not in floor_rooms:
                    break
                    
                room = floor_rooms[current_id]
                if direction not in room.exits:
                    break
                
                target_id = room.exits[direction]
                if target_id not in floor_rooms:
                    break
                
                target_room = floor_rooms[target_id]
                is_visited = target_id in visited_rooms
                
                name = target_room.name[:18] if is_visited else "Unexplored"
                markers = []
                
                if is_visited:
                    if target_room.enemies:
                        markers.append("⚔")
                    if target_room.items:
                        markers.append("◆")
                else:
                    markers.append("?")
                
                chain.append({
                    'name': name,
                    'markers': " ".join(markers),
                    'visited': is_visited,
                    'depth': depth + 1
                })
                
                current_id = target_id
            
            return chain
        
        # Get room chains in all directions
        north_chain = get_room_chain('north')
        south_chain = get_room_chain('south')
        east_chain = get_room_chain('east')
        west_chain = get_room_chain('west')
        
        # Get special exits
        def get_special_info(direction):
            if direction in current.exits:
                target_id = current.exits[direction]
                target_room = floor_rooms.get(target_id)
                if target_room:
                    is_visited = target_id in visited_rooms
                    name = target_room.name[:18] if is_visited else "Unexplored"
                    markers = []
                    if is_visited:
                        if target_room.enemies:
                            markers.append("⚔")
                        if target_room.items:
                            markers.append("◆")
                    else:
                        markers.append("?")
                    return name, " ".join(markers), is_visited
            return None, None, False
        
        up_info = get_special_info('up')
        down_info = get_special_info('down')
        # secret_info intentionally not fetched — secret exits are hidden from the map
        
        # Build expanded compass display
        lines.append("║" + " " * 78 + "║")
        
        # NORTH CHAIN (show up to 3 rooms)
        if north_chain:
            lines.append("║" + " " * 33 + "[NORTH]" + " " * 38 + "║")
            for i, room_info in enumerate(reversed(north_chain)):
                depth_marker = "↑" * room_info['depth']
                room_line = f"║{' ' * 18}{depth_marker} {room_info['name']:<18}"
                if room_info['markers']:
                    room_line += f" {room_info['markers']:>4}"
                room_line += " " * (78 - len(room_line) + 1) + "║"
                lines.append(room_line)
            lines.append("║" + " " * 35 + "│" + " " * 42 + "║")
        
        # WEST-CENTER-EAST ROW
        west_display = ""
        east_display = ""
        
        # WEST CHAIN
        if west_chain:
            west_rooms = []
            for room_info in reversed(west_chain):
                depth_marker = "←" * room_info['depth']
                room_str = f"{room_info['name'][:12]:<12}"
                if room_info['markers']:
                    room_str += f" {room_info['markers']}"
                west_rooms.append(f"{room_str} {depth_marker}")
            west_display = " ".join(west_rooms)
        
        # CENTER (Current Room)
        current_name = current.name[:16]
        current_markers = []
        if current.enemies:
            current_markers.append("⚔")
        if current.items:
            current_markers.append("◆")
        marker_str = " ".join(current_markers) if current_markers else ""
        
        center_display = f"[ ►{current_name:<16}]"
        if marker_str:
            center_display += f" {marker_str}"
        
        # EAST CHAIN
        if east_chain:
            east_rooms = []
            for room_info in east_chain:
                depth_marker = "→" * room_info['depth']
                room_str = f"{room_info['name'][:12]:<12}"
                if room_info['markers']:
                    room_str += f" {room_info['markers']}"
                east_rooms.append(f"{depth_marker} {room_str}")
            east_display = " ".join(east_rooms)
        
        # Build center line
        center_line = "║"
        
        if west_display:
            center_line += f" {west_display}"
        else:
            center_line += " " * 2
        
        center_line += f" {center_display} "
        
        if east_display:
            center_line += f"{east_display}"
        
        # Pad to width
        padding = 78 - len(center_line) + 1
        if padding > 0:
            center_line += " " * padding
        center_line += "║"
        lines.append(center_line)
        
        # Direction labels
        label_line = "║"
        if west_chain:
            label_line += f"{' ' * 5}[WEST]"
        else:
            label_line += " " * 11
        
        label_line += " " * 30
        
        if east_chain:
            label_line += f"[EAST]"
        
        padding = 78 - len(label_line) + 1
        if padding > 0:
            label_line += " " * padding
        label_line += "║"
        lines.append(label_line)
        
        # SOUTH CHAIN
        if south_chain:
            lines.append("║" + " " * 35 + "│" + " " * 42 + "║")
            for room_info in south_chain:
                depth_marker = "↓" * room_info['depth']
                room_line = f"║{' ' * 18}{depth_marker} {room_info['name']:<18}"
                if room_info['markers']:
                    room_line += f" {room_info['markers']:>4}"
                room_line += " " * (78 - len(room_line) + 1) + "║"
                lines.append(room_line)
            lines.append("║" + " " * 33 + "[SOUTH]" + " " * 38 + "║")
        
        lines.append("║" + " " * 78 + "║")
        
        # Special exits at bottom
        special_dirs = []
        if up_info[0]:
            special_dirs.append(f"↑UP: {up_info[0][:20]} {up_info[1] or ''}")
        if down_info[0]:
            special_dirs.append(f"↓DOWN: {down_info[0][:20]} {down_info[1] or ''}")
        
        if special_dirs:
            lines.append("║ Special Exits:" + " " * 63 + "║")
            for spec in special_dirs:
                line = f"║   {spec}"
                padding = 78 - len(line) + 1
                line += " " * padding + "║"
                lines.append(line)
            lines.append("║" + " " * 78 + "║")
        
        # Floor overview of ALL rooms
        lines.append("╠" + "═" * 78 + "╣")
        lines.append("║ FLOOR OVERVIEW - All Rooms:" + " " * 49 + "║")
        lines.append("║" + " " * 78 + "║")
        
        # List all rooms with status
        all_rooms = []
        for room_id, room in floor_rooms.items():
            is_current = (room_id == current_room)
            is_visited = room_id in visited_rooms
            
            marker = "►" if is_current else ("○" if is_visited else "·")
            
            room_type = ""
            if 'boss' in room_id:
                room_type = "⚔BOSS"
            elif 'stairs' in room_id:
                room_type = "⬇STAIRS"
            elif room_id == 'start' or 'start' in room_id:
                room_type = "⬆START"
            elif 'secret' in room_id:
                room_type = ""  # No hint on map
            
            all_rooms.append({
                'marker': marker,
                'name': room.name[:20],
                'type': room_type,
                'visited': is_visited
            })
        
        # Sort: Start, Regular, Boss, Stairs, Secret
        def sort_key(r):
            if 'START' in r['type']:
                return (0, r['name'])
            elif 'BOSS' in r['type']:
                return (2, r['name'])
            elif 'STAIRS' in r['type']:
                return (3, r['name'])
            elif 'SECRET' in r['type']:
                return (4, r['name'])
            else:
                return (1, r['name'])
        
        all_rooms.sort(key=sort_key)
        
        # Display in two columns
        for i in range(0, len(all_rooms), 2):
            room1 = all_rooms[i]
            line = f"║ {room1['marker']} {room1['name']:<20}"
            if room1['type']:
                line += f" [{room1['type']}]"
            
            if i + 1 < len(all_rooms):
                room2 = all_rooms[i + 1]
                # Pad first column
                current_len = len(line) - 1  # Subtract the ║
                padding_needed = 40 - current_len
                if padding_needed > 0:
                    line += " " * padding_needed
                line += f"{room2['marker']} {room2['name']:<20}"
                if room2['type']:
                    line += f" [{room2['type']}]"
            
            # Final padding
            padding = 78 - len(line) + 1
            if padding > 0:
                line += " " * padding
            line += "║"
            lines.append(line)
        
        lines.append("║" + " " * 78 + "║")
        lines.append("╠" + "═" * 78 + "╣")
        
        # Stats and legend
        stats_line = f"║ Progress: {len(visited_floor)}/{len(floor_rooms)} rooms  |  Current Floor: {current_floor}"
        padding = 78 - len(stats_line) + 1
        lines.append(stats_line + " " * padding + "║")
        lines.append("║ ► = You  ○ = Visited  · = Undiscovered  ⚔ = Enemies  ◆ = Items            ║")
        lines.append("║ Depth arrows: → (1 room away)  →→ (2 rooms away)  →→→ (3 rooms away)         ║")
        lines.append("╚" + "═" * 78 + "╝")
        
        return '\n'.join(lines)

#################################################################################
# PLAYER CLASS
#################################################################################
class Player:
    """Player character with stats and inventory"""
    
    def __init__(self, name: str, character_class: str = "warrior"):
        self.name = name
        self.character_class = character_class
        self.class_tier = 1
        self.level = 1
        self.experience = 0
        self.experience_to_next = GameConstants.BASE_EXPERIENCE_NEEDED
        
        config = GameConstants.CLASSES[character_class]
        self.stats = config['base_stats'].copy()
        self.rarity_boost = 0.0
        
        self.health = config['base_health']
        self.max_health = self.health
        self.mana = config['base_mana']
        self.max_mana = self.mana
        
        self.inventory: List[str] = []
        self.inventory_weapons: List[Dict] = []
        self.weapon: Optional[Dict] = None
        self.wearables: List[Dict] = []
        self.max_inventory = config['inventory_slots']
        
        self.special_items: List[str] = []
        
        self.current_floor = 1
        self.current_room = "start"
        self.visited_rooms: Set[str] = set()
        
        self.bosses_defeated: List[str] = []
        self.gold_coins = 0
        self.secret_room_unlocked = False
        self.unique_items_spawned: Set[str] = set()  # Track unique items spawned
    
    def gain_experience(self, amount: int) -> None:
        """Add experience and handle level ups"""
        self.experience += amount
        print(f"+ {amount} experience!")
        logger.info(f"Player gained {amount} XP. Total: {self.experience}/{self.experience_to_next}")
        
        while self.experience >= self.experience_to_next:
            self._level_up()
    
    def _level_up(self) -> None:
        """Handle level up"""
        self.experience -= self.experience_to_next
        self.level += 1
        self.experience_to_next = int(self.experience_to_next * GameConstants.EXPERIENCE_MULTIPLIER)
        
        config = GameConstants.CLASSES[self.character_class]
        old_max_inv = self.max_inventory
        
        self.max_inventory = config['inventory_slots'] + (self.level - 1) * GameConstants.INVENTORY_SLOTS_PER_LEVEL + (self.class_tier - 1) * GameConstants.INVENTORY_SLOTS_PER_TIER
        
        growth = config['stat_growth']
        for stat, bonus in growth.items():
            self.stats[stat] += bonus
        
        health_gain = config['health_per_level']
        self.max_health += health_gain
        self.health = self.max_health

        is_mage = self.character_class == 'mage'
        if is_mage:
            self.max_mana += GameConstants.MANA_PER_LEVEL
            self.mana = self.max_mana

        logger.info(f"LEVEL UP: {self.name} reached level {self.level}. HP: {self.max_health}" + (f", MP: {self.max_mana}" if is_mage else ""))

        luck_gain  = config['stat_growth'].get('luck', 0)
        vit_gain   = config['stat_growth'].get('vitality', 0)
        faith_gain = config['stat_growth'].get('faith', 0)

        print(f"\n*** LEVEL UP! Now level {self.level}!")
        mana_str = f" | Mana +{GameConstants.MANA_PER_LEVEL} (now {self.max_mana})" if is_mage else ""
        print(f"Health +{health_gain} (now {self.max_health}){mana_str}")
        # Show every stat that actually grew this level
        stat_labels = {
            'strength': 'STR', 'intelligence': 'INT', 'agility': 'AGI',
            'luck': 'LCK', 'vitality': 'VIT', 'faith': 'FTH', 'arcane': 'ARC',
        }
        gained = []
        for stat, bonus in growth.items():
            if bonus > 0:
                label = stat_labels.get(stat, stat.upper()[:3])
                gained.append(f"{label} +{bonus} (→{self.stats[stat]})")
        if gained:
            print("  Stats: " + "  |  ".join(gained))
        if self.max_inventory > old_max_inv:
            print(f"Inventory: {old_max_inv} → {self.max_inventory} slots")
        print("Fully healed!")
    
    def can_upgrade_class(self) -> bool:
        """Check if class upgrade available"""
        if self.class_tier >= 5:
            return False
        return self.level >= GameConstants.CLASS_UPGRADE_LEVELS[self.class_tier - 1]
    
    def get_class_title(self) -> str:
        """Get current class title"""
        return GameConstants.CLASS_NAMES[self.class_tier][self.character_class]
    
    def upgrade_class(self) -> bool:
        """Upgrade class tier"""
        if not self.can_upgrade_class():
            return False
        
        old_tier = self.class_tier
        self.class_tier += 1
        self.rarity_boost += GameConstants.RARITY_BOOST_PER_TIER
        
        config = GameConstants.CLASSES[self.character_class]
        tier_bonus = (self.class_tier - 1) * 5

        # Rebuild all stats from scratch including luck/vitality
        self.stats = {k: v + tier_bonus for k, v in config['base_stats'].items()}

        growth = config['stat_growth']
        for stat, bonus in growth.items():
            self.stats[stat] += bonus * (self.level - 1)
        
        old_health = self.max_health
        old_mana = self.max_mana

        self.max_health = config['base_health'] + (self.class_tier - 1) * 30 + (self.level - 1) * config['health_per_level']
        self.health = self.max_health

        is_mage = self.character_class == 'mage'
        if is_mage:
            self.max_mana = config['base_mana'] + (self.class_tier - 1) * 25 + (self.level - 1) * GameConstants.MANA_PER_LEVEL
            self.mana = self.max_mana

        logger.info(f"CLASS UPGRADE: {self.name} advanced from tier {old_tier} to {self.class_tier} ({self.get_class_title()})")

        print(f"\n*** CLASS UPGRADE! Now a {self.get_class_title()}! (Tier {self.class_tier}/5)")
        hp_gain = self.max_health - old_health
        if is_mage:
            mana_gain = self.max_mana - old_mana
            print(f"All stats +5 | Health +{hp_gain} | Mana +{mana_gain}")
        else:
            print(f"All stats +5 | Health +{hp_gain}")
        print(f"Loot drop boost: +{self.rarity_boost * 100:.0f}%")
        print("Fully healed!")
        return True
    
    def add_item(self, item: str) -> bool:
        """Add item to inventory"""
        if item == 'old map':
            if 'old map' not in self.special_items:
                self.special_items.append('old map')
                print(f"+ {item} (★ doesn't use inventory space)")
                print("  Use 'use old map' to view the dungeon, or 'map' as shortcut")
                logger.debug(f"Player picked up map (special item)")
                return True
            else:
                print("You already have a map!")
                return False
        
        if len(self.inventory) >= self.max_inventory:
            print(f"X Inventory full! ({self.max_inventory} slots)")
            return False
        self.inventory.append(item)
        print(f"+ {item}")
        return True
    
    def add_weapon_to_inventory(self, weapon: Dict) -> bool:
        """Store weapon in inventory"""
        if len(self.inventory) >= self.max_inventory:
            print(f"X Inventory full!")
            return False
        self.inventory_weapons.append(weapon)
        self.inventory.append(f"WEAPON: {weapon['name']}")
        print(f"Stored: {weapon['name']}")
        return True
    
    def equip_weapon(self, weapon: Dict) -> None:
        """Equip weapon"""
        self.weapon = weapon
        print(f"Equipped: {weapon['name']}")
    
    def switch_weapon(self, identifier: Optional[str] = None) -> bool:
        """Switch to different weapon"""
        if not self.inventory_weapons:
            print("No spare weapons!")
            return False
        
        target = None
        if identifier:
            for w in self.inventory_weapons:
                if identifier.lower() in w['name'].lower():
                    target = w
                    break
            if not target:
                print(f"No weapon matching '{identifier}'")
                return False
        else:
            def _fmt_w(w, prefix=""):
                t_names = [GameConstants.WEAPON_TRAITS.get(t, {}).get('name', t) for t in w.get('traits', [])]
                traits = "/".join(t_names) if t_names else "—"
                return f"{prefix}{w['name']:<26} {w['damage']:>3}dmg  {w.get('rarity','common').upper():<10}  [{traits}]"

            print("\n  #  Name                       Dmg  Rarity      Traits")
            print("  " + "-"*65)
            equipped_line = _fmt_w(self.weapon, "  ► ") if self.weapon else "  ► (unarmed)"
            print(equipped_line)
            print("  " + "-"*65)
            for i, w in enumerate(self.inventory_weapons, 1):
                print(_fmt_w(w, f"  {i}. "))
            print("  0. Cancel")
            try:
                choice = int(input("\nSwap to: ")) - 1
                if choice == -1:
                    print("Cancelled")
                    return False
                target = self.inventory_weapons[choice] if 0 <= choice < len(self.inventory_weapons) else None
            except (ValueError, KeyboardInterrupt):
                print("Cancelled")
                return False
        
        if target:
            if self.weapon:
                self.inventory_weapons.append(self.weapon)
                self.inventory.append(f"WEAPON: {self.weapon['name']}")
            self.inventory_weapons.remove(target)
            self.inventory.remove(f"WEAPON: {target['name']}")
            self.weapon = target
            print(f"Equipped: {target['name']} ({target['damage']} dmg)")
            return True
        return False
    
    def can_add_item(self) -> bool:
        """Check if there's space in inventory"""
        return len(self.inventory) < self.max_inventory
    
    def get_inventory_count(self) -> int:
        """Get current number of items in inventory"""
        return len(self.inventory)
    
    def has_map(self) -> bool:
        """Check if player has a map"""
        return 'old map' in self.special_items
    
    def discard_special_item(self, item_name: str) -> bool:
        """Discard a special item"""
        if item_name in self.special_items:
            self.special_items.remove(item_name)
            logger.info(f"Player discarded special item: {item_name} on floor {self.current_floor}")
            return True
        return False
    
    def show_stats(self) -> None:
        """Display character sheet"""
        weapon = self.weapon['name'] if self.weapon else "None"
        print(f"\n=== {self.name} the {self.get_class_title()} ===")
        print(f"Level {self.level} (Tier {self.class_tier}/5) | XP: {self.experience}/{self.experience_to_next}")
        if self.character_class == 'mage':
            print(f"Health: {self.health}/{self.max_health} | Mana: {self.mana}/{self.max_mana}")
        else:
            print(f"Health: {self.health}/{self.max_health}")
        print(f"Gold: {self.gold_coins}")

        # ── Character Stats ───────────────────────────────────────
        print("\n--- STATS " + "-"*38)
        print(f"  STR: {self.stats['strength']:<4}  INT: {self.stats['intelligence']:<4}  AGI: {self.stats['agility']}")
        luck = self.stats.get('luck', 0)
        vit  = self.stats.get('vitality', 0)
        crit_pct = min(60, 5 + max(0, luck - 10) * 0.5)
        vit_red  = max(0, (vit - 10) // 15)
        print(f"  LCK: {luck:<4} (crit {crit_pct:.0f}%)  VIT: {vit:<4} (dmg -{vit_red})")
        if self.character_class == 'mage':
            arcane = self.stats.get('arcane', 5)
            arc_dmg = max(0, (arcane - 10) * 1.5)
            arc_cost_red = max(0, int((arcane - 10) * 0.2))
            print(f"  ARC: {arcane:<4} (+{arc_dmg:.0f}% magic dmg | -{arc_cost_red} mana cost)")
        if self.character_class == 'paladin':
            faith = self.stats.get('faith', 5)
            aura_pct = int(25 + max(0, (faith - 10) * 1.5))
            smite_preview = int((self.stats['strength'] + faith * 2 + 22) * (1.0 + max(0, (faith - 10) * 0.02)))
            print(f"  FTH: {faith:<4} (Holy Aura +{aura_pct}% | Smite ~{smite_preview} dmg)")
        if self.character_class == 'berserker':
            hp_ratio = self.health / max(1, self.max_health)
            berserk_bonus = int(min(30, ((1.0 - hp_ratio) // 0.2) * 6))
            print(f"  PASSIVE: Built-in Berserker — currently +{berserk_bonus}% damage")
        lust = self.stats.get('lust', 5)
        if lust > 5:
            print(f"  LUST: {lust:<4} (enemies distracted & weakened by your sexual aura)")
        # ── Equipped Weapon ───────────────────────────────────────
        print("\n--- WEAPON " + "-"*37)
        if self.weapon:
            w = self.weapon
            rarity     = w.get('rarity', 'common')
            rarity_dat = GameConstants.WEAPON_RARITIES.get(rarity, {})
            mult       = rarity_dat.get('multiplier', 1.0)
            str_avg    = max(1, self.stats['strength'] // 3) // 2 + 1
            base_eff   = int((w['damage'] + str_avg) * mult)

            # Trait bonus preview (additive estimate)
            trait_mults = []
            trait_lines = []
            for t in w.get('traits', []):
                td = GameConstants.WEAPON_TRAITS.get(t, {})
                effect = td.get('effect', '')
                name   = td.get('name', t)
                desc   = td.get('desc', '')
                if effect == 'cursed':
                    trait_mults.append(1 + td.get('damage_bonus', 0))
                    trait_lines.append(f"  ✦ {name}: {desc}")
                elif effect in ('first_hit_double',):
                    trait_lines.append(f"  ✦ {name}: {desc}")
                elif effect == 'berserker':
                    trait_lines.append(f"  ✦ {name}: {desc}")
                elif effect in ('on_hit_dot',):
                    trait_lines.append(f"  ✦ {name}: {desc}")
                elif effect == 'lifesteal':
                    trait_lines.append(f"  ✦ {name}: {desc}")
                elif effect == 'crit_boost':
                    trait_lines.append(f"  ✦ {name}: {desc}")
                elif effect == 'type_bonus':
                    trait_lines.append(f"  ✦ {name}: {desc}")
                elif effect == 'execute_bonus':
                    trait_lines.append(f"  ✦ {name}: {desc}")
                elif effect == 'opener_bonus':
                    trait_lines.append(f"  ✦ {name}: {desc}")
                elif effect == 'damage_reduction':
                    trait_lines.append(f"  ✦ {name}: {desc}")
                else:
                    trait_lines.append(f"  ✦ {name}: {desc}")

            total_mult = mult
            for tm in trait_mults:
                total_mult *= tm

            print(f"  {w['name']}")
            print(f"  Rarity  : {rarity.upper()}  (x{mult} dmg multiplier)")
            print(f"  Type    : {w.get('type','?').capitalize()}")
            print(f"  Base dmg: {w['damage']}")
            print(f"  Avg hit : ~{base_eff}  (base + STR bonus × rarity mult)")
            if trait_mults:
                boosted = int(base_eff * (total_mult / mult))
                print(f"  w/Traits: ~{boosted}  (includes passive damage bonuses)")
            if trait_lines:
                print(f"  Traits:")
                for tl in trait_lines:
                    print(f"  {tl}")
        else:
            print("  No weapon equipped  (unarmed: 1–5 damage)")

        print(f"\n  Inventory: {len(self.inventory)}/{self.max_inventory} | Floor: {self.current_floor}/{GameConstants.NUM_FLOORS}")
        print(f"Bosses: {len(self.bosses_defeated)}/{GameConstants.NUM_FLOORS}")
        
        if self.wearables:
            from collections import Counter
            stat_labels = {'strength':'STR','intelligence':'INT','agility':'AGI','luck':'LCK','vitality':'VIT','faith':'FTH','arcane':'ARC'}
            counts = Counter(w['item'] for w in self.wearables)
            seen = set()
            entries = []
            for w in self.wearables:
                if w['item'] not in seen:
                    seen.add(w['item'])
                    lbl = stat_labels.get(w['stat'], w['stat'].upper()[:3])
                    prefix = f"[{counts[w['item']]}]" if counts[w['item']] > 1 else ""
                    entries.append(f"{prefix}{w['item']} (+{w['bonus']} {lbl})")
            print("\nWearables:")
            for i in range(0, len(entries), 2):
                left = entries[i]
                right = entries[i+1] if i+1 < len(entries) else ""
                print(f"  {left:<32}  {right}")
        
        if self.can_upgrade_class():
            next_title = GameConstants.CLASS_NAMES[self.class_tier + 1][self.character_class]
            print(f"\n*** CLASS UPGRADE AVAILABLE! → {next_title} (Tier {self.class_tier + 1}/5)")
    
    def show_status_summary(self) -> None:
        """Quick status"""
        weapon = self.weapon['name'] if self.weapon else "None"
        if self.character_class == 'mage':
            print(f"\n[F{self.current_floor}] HP:{self.health}/{self.max_health} MP:{self.mana}/{self.max_mana} W:{weapon}")
        else:
            print(f"\n[F{self.current_floor}] HP:{self.health}/{self.max_health} W:{weapon}")
    
    def to_dict(self) -> Dict:
        """Serialize for saving"""
        return {
            'name': self.name, 'character_class': self.character_class, 'class_tier': self.class_tier,
            'level': self.level, 'experience': self.experience, 'experience_to_next': self.experience_to_next,
            'stats': self.stats, 'health': self.health, 'max_health': self.max_health,
            'mana': self.mana, 'max_mana': self.max_mana, 'inventory': self.inventory,
            'inventory_weapons': self.inventory_weapons, 'weapon': self.weapon, 'wearables': self.wearables,
            'max_inventory': self.max_inventory, 'current_floor': self.current_floor,
            'current_room': self.current_room, 'visited_rooms': list(self.visited_rooms),
            'bosses_defeated': self.bosses_defeated, 'rarity_boost': self.rarity_boost,
            'gold_coins': self.gold_coins, 'secret_room_unlocked': self.secret_room_unlocked,
            'special_items': self.special_items, 'unique_items_spawned': list(self.unique_items_spawned)
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Player':
        """Deserialize from save, migrating old saves to current version."""
        player = cls(data['name'], data['character_class'])
        for key, value in data.items():
            if key == 'visited_rooms':
                setattr(player, key, set(value))
            elif key == 'special_items':
                setattr(player, key, value if value else [])
            elif key == 'unique_items_spawned':
                setattr(player, key, set(value) if value else set())
            else:
                setattr(player, key, value)

        if not hasattr(player, 'unique_items_spawned'):
            player.unique_items_spawned = set()

        player._migrate_save()
        return player

    def _migrate_save(self) -> None:
        """Backfill stats and weapon traits added after a save was created."""
        config  = GameConstants.CLASSES.get(self.character_class, {})
        base    = config.get('base_stats', {})
        growth  = config.get('stat_growth', {})
        levels  = max(0, self.level - 1)
        migrated = []

        # ── Backfill any missing stat ────────────────────────────
        for stat, base_val in base.items():
            if stat not in self.stats:
                earned = base_val + growth.get(stat, 0) * levels
                self.stats[stat] = earned
                label = stat.capitalize()
                migrated.append(f"{label} → {earned}")

        # ── Add trait to equipped weapon if it has none ──────────
        def _assign_trait(weapon):
            if weapon and not weapon.get('traits'):
                wtype = weapon.get('type', 'melee')
                # Pick a sensible default trait per weapon type
                defaults = {
                    'melee':   ['bleeding', 'savage', 'shielded'],
                    'magic':   ['precise', 'elemental_fire', 'venomous'],
                    'stealth': ['bleeding', 'swift', 'venomous'],
                }
                pool = defaults.get(wtype, ['swift'])
                weapon['traits'] = [random.choice(pool)]
                return weapon['name']
            return None

        if self.weapon:
            name = _assign_trait(self.weapon)
            if name:
                migrated.append(f"Trait added to {name}")

        for w in getattr(self, 'inventory_weapons', []):
            name = _assign_trait(w)
            if name:
                migrated.append(f"Trait added to {name}")

        if migrated:
            print("\n[Save migrated to v7.0.2]")
            for m in migrated:
                print(f"  + {m}")

#################################################################################
# ROOM CLASS
#################################################################################
class Room:
    """Dungeon room"""
    def __init__(self, name: str, description: str, floor: int,
                 items: List[str] = None, exits: Dict[str, str] = None,
                 enemies: List[str] = None, atmosphere: str = ""):
        self.name = name
        self.description = description
        self.floor = floor
        self.items = items or []
        self.exits = exits or {}
        self.enemies = enemies or []
        self.visited = False
        self.atmosphere = atmosphere
    
    def describe(self) -> None:
        """Show room description"""
        if not self.visited:
            print(f"\n{self.description}")
            if self.atmosphere:
                print(f"{self.atmosphere}")
            self.visited = True
        else:
            print(f"\nYou are in {self.name}")
            if 'adamus' in self.atmosphere.lower() or 'merchant' in self.atmosphere.lower():
                print("A merchant is here. Use 'shop' to trade.")
        
        if self.enemies:
            print(f"\n*** ENEMIES:")
            for enemy in self.enemies:
                info = GameConstants.ENEMIES.get(enemy.lower())
                if info:
                    print(f"  - {enemy}: {info['desc']}")
        
        if self.items:
            print(f"\nItems: {', '.join(self.items)}")
        if self.exits:
            formatted = []
            for d in self.exits.keys():
                if d == 'secret':
                    pass  # Never reveal secret exits in room description
                elif d == 'out':
                    formatted.append('OUT (back)')
                else:
                    formatted.append(d)
            print(f"Exits: {', '.join(formatted)}")

#################################################################################
# WEAPON SYSTEM
#################################################################################
class WeaponSystem:
    """Weapon generation and management"""
    
    @classmethod
    def generate_weapon(cls, player: Player, force_rarity: Optional[str] = None) -> Dict:
        """Generate random weapon"""
        if not force_rarity and random.random() < GameConstants.GOLDEN_GUN_DROP_RATE:
            logger.warning(f"GOLDEN GUN GENERATED for {player.name} at level {player.level}!")
            return cls._create_golden_gun()
        
        equipped_rarity = None
        if player.weapon and not force_rarity:
            equipped_rarity = player.weapon.get('rarity', 'common')
        
        rarity = force_rarity or cls._calculate_rarity(player.level, player.rarity_boost, equipped_rarity)
        weapon_type = random.choice(GameConstants.CLASSES[player.character_class]['weapon_types'])
        
        material = random.choice(GameConstants.WEAPON_MATERIALS[rarity])
        weapon_name = random.choice(GameConstants.WEAPON_TYPES[weapon_type])
        
        # Use rarity-specific base damage range
        rarity_data = GameConstants.WEAPON_RARITIES[rarity]
        base_damage = random.randint(rarity_data['base_min'], rarity_data['base_max']) + (player.level * 2)
        multiplier = rarity_data['multiplier']
        final_damage = int(base_damage * multiplier)
        
        # Assign traits: 1 always, 2nd for epic+, 3rd for mythic+
        eligible_traits = [
            k for k, td in GameConstants.WEAPON_TRAITS.items()
            if GameConstants.RARITY_ORDER.index(rarity) >=
               GameConstants.RARITY_ORDER.index(td.get('rarity_min', 'common'))
        ]
        num_traits = 1
        if rarity in ('epic', 'legendary'):
            num_traits = 2 if random.random() < 0.5 else 1
        elif rarity == 'mythic':
            num_traits = random.choice([2, 2, 3])
        traits = random.sample(eligible_traits, min(num_traits, len(eligible_traits)))

        weapon = {
            'name': f"{material} {weapon_name}",
            'damage': final_damage,
            'type': weapon_type,
            'rarity': rarity,
            'base_name': f"{material} {weapon_name}",
            'traits': traits,
        }

        logger.debug(f"Generated {rarity} weapon: {weapon['name']} ({final_damage} dmg) traits={traits}")
        return weapon
    
    @classmethod
    def _calculate_rarity(cls, level: int, boost: float, equipped_rarity: Optional[str] = None) -> str:
        """Calculate weapon rarity with boost for better than equipped - BALANCED"""
        boost_val = int(boost * 100)
        
        # More conservative legendary/mythic chances - scale with level more
        chances = {
            'common': max(55 - (level * 2) - boost_val, 15),
            'uncommon': min(25 + level, 30),
            'rare': min(12 + level // 2 + boost_val // 4, 20),
            'epic': min(6 + level // 4 + boost_val // 4, 12),
            'legendary': min(1 + level // 8 + boost_val // 5, 5) if level >= 10 else 0,  # Only after level 10
            'mythic': min(1 + level // 12 + boost_val // 6, 2) if level >= 15 else 0  # Only after level 15
        }
        
        if equipped_rarity and equipped_rarity in GameConstants.RARITY_ORDER:
            equipped_idx = GameConstants.RARITY_ORDER.index(equipped_rarity)
            boost_amount = int(GameConstants.BETTER_WEAPON_RARITY_BOOST * 100)
            
            for rarity in GameConstants.RARITY_ORDER:
                if rarity == 'divine':
                    continue
                rarity_idx = GameConstants.RARITY_ORDER.index(rarity)
                
                # FIXED: Don't boost level-locked rarities
                if rarity == 'legendary' and level < 10:
                    continue
                if rarity == 'mythic' and level < 15:
                    continue
                
                if rarity_idx > equipped_idx:
                    chances[rarity] = min(chances[rarity] + boost_amount // (rarity_idx - equipped_idx), 40)
                elif rarity_idx < equipped_idx:
                    chances[rarity] = max(chances[rarity] - boost_amount // 2, 5)
        
        total = sum(chances.values())
        if total != 100:
            adjustment = 100 - total
            chances['common'] += adjustment
        
        rand = random.randint(1, 100)
        cumulative = 0
        for rarity, chance in chances.items():
            cumulative += chance
            if rand <= cumulative:
                return rarity
        
        return 'common'
    
    @classmethod
    def _create_golden_gun(cls) -> Dict:
        """Create Golden Gun"""
        name = random.choice(GameConstants.GOLDEN_GUN_NAMES)
        return {
            'name': f"*** {name}",
            'damage': 99999,
            'type': 'divine',
            'rarity': 'divine',
            'base_name': name,
            'uses_remaining': 6,
            'max_uses': 6,
            'special': 'instant_kill'
        }
    
    @classmethod
    def create_starting_weapons(cls) -> Dict[str, List[Dict]]:
        """Create starting weapon choices (8 per class, randomised from a larger pool)"""
        def w(name, dmg, wtype, trait):
            return {'name': name, 'damage': dmg, 'type': wtype,
                    'rarity': 'common', 'base_name': name, 'traits': [trait]}

        warrior_pool = [
            w('Iron Sword',        18, 'melee',   'swift'),
            w('Steel Axe',         20, 'melee',   'savage'),
            w('Bronze Hammer',     22, 'melee',   'shielded'),
            w('War Spear',         19, 'melee',   'precise'),
            w('Rusted Greatsword', 24, 'melee',   'cursed'),
            w('Spiked Mace',       21, 'melee',   'bleeding'),
            w('Bone Club',         17, 'melee',   'venomous'),
            w('Halberd',           23, 'melee',   'executioner'),
            w('Serrated Blade',    20, 'melee',   'bleeding'),
            w("Guard's Sword",     18, 'melee',   'shielded'),
            w('Cleaver',           21, 'melee',   'savage'),
            w('Flail',             22, 'melee',   'berserker'),
        ]
        mage_pool = [
            w('Wooden Staff',      14, 'magic',   'venomous'),
            w('Apprentice Wand',   13, 'magic',   'precise'),
            w('Crystal Orb',       16, 'magic',   'elemental_ice'),
            w('Tome of Sparks',    15, 'magic',   'elemental_fire'),
            w('Bone Scepter',      14, 'magic',   'vampiric'),
            w('Twisted Branch',    12, 'magic',   'cursed'),
            w('Cracked Focus',     17, 'magic',   'swift'),
            w('Rune Stone',        15, 'magic',   'holy'),
            w('Shadow Catalyst',   16, 'magic',   'bleeding'),
            w('Obsidian Wand',     13, 'magic',   'executioner'),
            w('Petrified Staff',   15, 'magic',   'shielded'),
            w('Arcane Sliver',     14, 'magic',   'savage'),
        ]
        rogue_pool = [
            w('Steel Dagger',      16, 'stealth', 'bleeding'),
            w('Short Bow',         17, 'stealth', 'precise'),
            w('Assassin Blade',    18, 'stealth', 'executioner'),
            w('Throwing Knives',   15, 'stealth', 'swift'),
            w('Shiv',              14, 'stealth', 'venomous'),
            w('Serrated Rapier',   19, 'stealth', 'bleeding'),
            w('Hook Blade',        17, 'stealth', 'savage'),
            w('Bone Needles',      16, 'stealth', 'venomous'),
            w('Crossbow',          20, 'stealth', 'executioner'),
            w('Shadow Claw',       15, 'stealth', 'vampiric'),
            w('Notched Sword',     17, 'stealth', 'cursed'),
            w('Barbed Dart',       14, 'stealth', 'bleeding'),
        ]
        # Shuffle each pool and offer 8 choices so every run looks different
        random.shuffle(warrior_pool)
        random.shuffle(mage_pool)
        random.shuffle(rogue_pool)
        return {
            'warrior': warrior_pool[:8],
            'mage':    mage_pool[:8],
            'rogue':   rogue_pool[:8],
        }

#################################################################################
# COMBAT SYSTEM
#################################################################################
class CombatSystem:
    """Combat handler"""
    def __init__(self, game: 'Game'):
        self.game = game
    
    def fight_enemy(self, enemy_name: str, player: Player, room: Room) -> bool:
        """Regular enemy combat with trait effects"""
        enemy = GameConstants.ENEMIES.get(enemy_name.lower())
        if not enemy:
            logger.warning(f"Unknown enemy attempted: {enemy_name}")
            print(f"Unknown enemy: {enemy_name}")
            return True

        hp = enemy['health']
        max_hp = hp
        dmg = enemy['damage']

        # Show enemy weakness hint if player's weapon has a matching trait
        if player.weapon:
            en_lower = enemy_name.lower()
            weaknesses = GameConstants.ENEMY_WEAKNESSES.get(en_lower, {})
            for trait_key in player.weapon.get('traits', []):
                if trait_key in weaknesses and weaknesses[trait_key] > 1.0:
                    td_name = GameConstants.WEAPON_TRAITS.get(trait_key, {}).get('name', trait_key)
                    print(f"  ◈ {enemy_name} is WEAK to {td_name}!")

        logger.info(f"Combat: {player.name} vs {enemy_name} (HP {hp})")
        print(f"\n*** Combat: {enemy_name}!")
        print(f"{enemy['desc']}")

        # Per-fight DoT state (applied TO enemy)
        dot_stack: list = []   # [{'damage': int, 'turns': int, 'type': str}]

        turn = 0
        first_hit = True
        while hp > 0 and player.health > 0:
            turn += 1

            # ── Apply active enemy DoTs ───────────────────────────
            new_stack = []
            for dot in dot_stack:
                hp -= dot['damage']
                dtype = dot.get('dot_type', 'bleed')
                print(f"  {dtype.capitalize()} deals {dot['damage']} to {enemy_name}! ({dot['turns'] - 1} turns left)")
                if dot['turns'] - 1 > 0:
                    new_stack.append({**dot, 'turns': dot['turns'] - 1})
            dot_stack = new_stack
            if hp <= 0:
                print(f"*** {enemy_name} succumbs to {dtype}!")
                room.enemies.remove(enemy_name)
                player.gain_experience(enemy['exp'])
                self._handle_drops(enemy_name, room, player)
                return True

            # ── Cursed weapon HP drain ────────────────────────────
            if player.weapon:
                for trait_key in player.weapon.get('traits', []):
                    td = GameConstants.WEAPON_TRAITS.get(trait_key, {})
                    if td.get('effect') == 'cursed':
                        drain = td['hp_drain']
                        player.health -= drain
                        print(f"  ✦ Cursed drain: -{drain} HP")
                        if player.health <= 0:
                            print("*** The curse claims you! GAME OVER!")
                            return False

            # ── Player attacks ────────────────────────────────────
            damage = DamageCalculator.calculate_player_damage(
                player,
                enemy_name=enemy_name,
                enemy_hp=hp,
                enemy_max_hp=max_hp,
                first_hit=first_hit,
            )
            first_hit = False
            hp -= damage
            weapon = player.weapon.get('base_name', player.weapon['name']) if player.weapon else 'fists'
            print(f"You strike with {weapon} for {damage} damage! [{enemy_name} HP: {max(0, hp)}/{max_hp}]")

            # ── On-hit trait procs ────────────────────────────────
            if player.weapon:
                for trait_key in player.weapon.get('traits', []):
                    td = GameConstants.WEAPON_TRAITS.get(trait_key, {})
                    if td.get('effect') == 'on_hit_dot' and hp > 0:
                        dtype = td.get('dot_type', 'bleed')
                        # Refresh/add dot
                        dot_stack = [d for d in dot_stack if d.get('dot_type') != dtype]
                        dot_stack.append({'damage': td['dot_damage'], 'turns': td['dot_turns'], 'dot_type': dtype})
                        print(f"  ✦ {td['name']}! {dtype.capitalize()} applied.")
                    elif td.get('effect') == 'lifesteal' and damage > 0:
                        heal = max(1, int(damage * td['lifesteal_pct']))
                        player.health = min(player.max_health, player.health + heal)
                        print(f"  ✦ Vampiric: +{heal} HP drained!")

            if hp <= 0:
                logger.info(f"Victory: {player.name} defeated {enemy_name} in {turn} turns")
                print(f"*** Defeated {enemy_name}!")
                room.enemies.remove(enemy_name)
                player.gain_experience(enemy['exp'])
                self._handle_drops(enemy_name, room, player)
                return True

            # ── Enemy attacks ─────────────────────────────────────
            hit = DamageCalculator.calculate_enemy_damage(dmg, player)
            player.health -= hit
            print(f"{enemy_name} hits for {hit} damage! [Your HP: {player.health}/{player.max_health}]")

            if player.health <= 0:
                logger.error(f"PLAYER DEATH: {player.name} killed by {enemy_name}")
                print("*** DEFEATED! GAME OVER!")
                return False

        return True
    
    def _handle_drops(self, enemy_name: str, room: Room, player: Player) -> None:
        """Handle enemy drops"""
        rarity = player.weapon.get('rarity', 'common') if player.weapon else 'common'
        multiplier = GameConstants.WEAPON_RARITIES[rarity]['multiplier']
        drop_chance = GameConstants.ITEM_DROP_BASE_CHANCE + (multiplier * 0.1)
        
        if random.random() < GameConstants.GOLD_DROP_CHANCE:
            coins = random.randint(GameConstants.GOLD_DROP_MIN, GameConstants.GOLD_DROP_MAX)
            player.gold_coins += coins
            print(f"+ {coins} gold coins!")
        
        if random.random() < drop_chance:
            if random.random() < GameConstants.WEAPON_DROP_CHANCE:
                print(f"+ Weapon cache dropped!")
                room.items.append("weapon cache")
            else:
                if player.character_class == 'mage':
                    # Mages: 1/3 healing, 2/3 utility/exp
                    drops = ["health potion", "magic scroll", "ice crystal",
                             "experience gem", "arcane pendant", "magic scroll"]
                else:
                    # Others: healing items are now a minority of drops
                    drops = ["health potion", "energy drink",
                             "power ring", "swift boots", "experience gem",
                             "armor piece", "swift boots", "experience gem"]
                item = random.choice(drops)
                room.items.append(item)
                print(f"+ {item}")
    
    def fight_boss(self, boss_name: str, player: Player, room: Room) -> bool:
        """Boss combat"""
        floor = player.current_floor
        boss_config = BossConfig.generate(floor)
        
        logger.info(f"BOSS FIGHT: {player.name} (Lvl {player.level}, HP {player.health}) vs {boss_name} on floor {floor}")
        
        print("\n" + "="*60)
        print(f"*** BOSS FIGHT: {boss_name.upper()}!")
        print("="*60)
        
        if player.level < boss_config['min_level']:
            logger.warning(f"Player {player.name} (Lvl {player.level}) attempting {boss_name} (recommended Lvl {boss_config['min_level']})")
            print(f"! WARNING: Recommended level {boss_config['min_level']}+!")
            try:
                if input("Continue? (y/n): ").strip().lower() not in ['y', 'yes']:
                    return True
            except KeyboardInterrupt:
                return True
        
        hp = boss_config['base_health'] + (player.level * boss_config['health_scaling'])
        max_hp = hp
        dmg = boss_config['damage']
        
        print(f"\n{boss_name}: {hp} HP")
        
        # ── Gambler's d20 — nat 20 instant kill ──────────────────
        if "gambler's d20" in player.inventory:
            roll = random.randint(1, 20)
            print(f"\n  ⚄ You pull out the Gambler's d20 and roll... {roll}!")
            if roll == 20:
                print(f"  ★ NATURAL 20! The universe itself conspires against {boss_name}!")
                print(f"  ★ {boss_name} is annihilated by sheer cosmic fortune!")
                print(f"  ★ INSTANT KILL! (The d20 shatters — it had one great moment in it.)")
                player.inventory.remove("gambler's d20")
                player.gain_experience(boss_config['exp_reward'])
                room.enemies.clear()
                room.items.append("champion's prize")
                return True
            elif roll == 1:
                print(f"  ✗ Critical failure. You fumbled and dropped the d20.")
                print(f"  ✗ It bounces under a rock. Gone forever.")
                player.inventory.remove("gambler's d20")
            else:
                print(f"  Not a 20. The d20 stays in your pocket for next time.")

        turn = 1
        rage_used = False
        rage_active = False
        while hp > 0 and player.health > 0:
            print(f"\n--- Turn {turn} ---")
            # Cursed drain in boss fights
            if player.weapon:
                for tk in player.weapon.get('traits', []):
                    td = GameConstants.WEAPON_TRAITS.get(tk, {})
                    if td.get('effect') == 'cursed':
                        drain = td['hp_drain']
                        player.health -= drain
                        print(f"  ✦ Cursed drain: -{drain} HP")
                        if player.health <= 0:
                            print("*** The curse claims you! GAME OVER!")
                            return False
            if player.character_class in ('mage', 'paladin'):
                print(f"You: {player.health}/{player.max_health} HP | {player.mana}/{player.max_mana} MP")
            else:
                print(f"You: {player.health}/{player.max_health} HP")
            print(f"{boss_name}: {hp}/{max_hp} HP")
            
            actions = ["1. Attack"]
            if player.character_class == 'mage':
                actions.append("2. Magic")
            actions.append("3. Defend")
            if any(i in GameConstants.HEALING_ITEMS for i in player.inventory):
                actions.append("4. Heal")
            print(" | ".join(actions))
            print("(You can type the number or the word, e.g. 'attack' or 'magic')")
            
            try:
                action = input("\nAction: ").strip().lower()
            except KeyboardInterrupt:
                action = "1"
            
            player_dmg = 0
            defend = False
            
            if action in ["1", "attack", "a", "strike"]:
                player_dmg = DamageCalculator.calculate_player_damage(
                    player, enemy_name=boss_name,
                    enemy_hp=hp, enemy_max_hp=max_hp,
                    first_hit=(turn == 1),
                )
                if rage_active:
                    player_dmg = int(player_dmg * 1.5)
                    rage_active = False
                    print(f"*** RAGE STRIKE! {player_dmg} damage!")
                else:
                    print(f"*** You strike for {player_dmg} damage!")
                # Lifesteal in boss fights
                if player.weapon:
                    for tk in player.weapon.get('traits', []):
                        td = GameConstants.WEAPON_TRAITS.get(tk, {})
                        if td.get('effect') == 'lifesteal':
                            heal = max(1, int(player_dmg * td['lifesteal_pct']))
                            player.health = min(player.max_health, player.health + heal)
                            print(f"  ✦ Vampiric: +{heal} HP!")
            elif action in ["2", "magic", "m", "spell"]:
                if player.character_class != 'mage':
                    print(f"{player.get_class_title()}s cannot use magic!")
                    continue
                arcane = player.stats.get('arcane', 5)
                arcane_cost_reduction = max(0, int((arcane - 10) * 0.2))
                mana_cost = max(5, GameConstants.MAGIC_MANA_COST - arcane_cost_reduction)
                if player.mana >= mana_cost:
                    player.mana -= mana_cost
                    base_magic_dmg = player.stats['intelligence'] + random.randint(*GameConstants.MAGIC_DAMAGE_RANGE)
                    class_multiplier = GameConstants.MAGIC_MULTIPLIERS.get(player.character_class, 1.0)
                    arcane_bonus = 1.0 + max(0, (arcane - 10) * 0.015)
                    player_dmg = int(base_magic_dmg * class_multiplier * arcane_bonus)
                    print(f"*** Arcane strike! {player_dmg} damage! (cost {mana_cost} MP)")
                else:
                    print("Not enough mana!")
                    continue
            elif action in ["3", "defend", "d", "block"]:
                defend = True
                print("*** You brace for impact!")
            elif action in ["4", "heal", "h", "potion"]:
                ItemHandler.use_item(player, 'healing')
                continue
            elif action in ["smite"] and player.character_class == 'paladin':
                if player.mana >= 20:
                    player.mana -= 20
                    faith = player.stats.get('faith', 5)
                    faith_bonus = 1.0 + max(0, (faith - 10) * 0.02)
                    smite_base = player.stats['strength'] + faith * 2 + random.randint(15, 30)
                    smite_dmg = int(smite_base * faith_bonus)
                    hp -= smite_dmg
                    player_dmg = smite_dmg
                    print(f"*** Divine Smite! {smite_dmg} holy damage! (Faith {faith})")
                else:
                    print("Not enough mana for Smite!")
                    continue
            elif action in ["rage"] and player.character_class == 'berserker':
                if rage_used:
                    print("Rage already spent this fight!")
                    continue
                rage_used = True
                rage_active = True
                player_dmg = 0
                print("*** BERSERKER RAGE! Your next attack deals 1.5x damage!")
                continue
            elif action in ["5", "swap", "sw"]:
                player.switch_weapon()
                continue
            else:
                print("Invalid action!")
                continue
            
            hp -= player_dmg
            if hp <= 0:
                break
            
            use_special = (hp < max_hp * GameConstants.BOSS_SPECIAL_HEALTH_THRESHOLD and
                          turn % GameConstants.BOSS_SPECIAL_TURN_FREQUENCY == 0)
            
            if use_special:
                boss_dmg = dmg + boss_config['special_bonus']
                if defend:
                    boss_dmg //= GameConstants.BOSS_DEFEND_REDUCTION
                print(f"*** {boss_config['special_attack']}! {boss_dmg} damage!")
            else:
                boss_dmg = dmg + random.randint(1, 10)
                boss_dmg = DamageCalculator.calculate_enemy_damage(boss_dmg, player, True)
                if defend:
                    boss_dmg //= GameConstants.BOSS_DEFEND_REDUCTION
                print(f"Boss attacks: {boss_dmg} damage!")
            
            player.health -= boss_dmg
            if player.health <= 0:
                logger.error(f"BOSS DEATH: {player.name} (Lvl {player.level}) defeated by {boss_name} on turn {turn}")
                print(f"\n*** Defeated by {boss_name}! GAME OVER!")
                return False
            
            turn += 1
        
        logger.info(f"BOSS VICTORY: {player.name} defeated {boss_name} in {turn} turns on floor {floor}")
        
        print("\n" + "="*60)
        print("*** VICTORY!")
        print("="*60)
        
        room.enemies.remove(boss_name)
        player.bosses_defeated.append(boss_name)
        player.gain_experience(boss_config['exp_reward'])
        
        # FIXED: Add champion's prize to room AFTER defeating boss
        if "champion's prize" not in room.items:
            room.items.append("champion's prize")
            print("\n*** A champion's prize chest appears!")
        
        # Generate scaled boss weapon
        boss_weapon = BossConfig.generate_boss_weapon(floor, player)
        
        logger.info(f"Boss reward: {player.name} received {boss_weapon['name']} ({boss_weapon['damage']} dmg) - scaled for level {player.level}")
        
        tier_label = boss_weapon.get('tier_label', 'GOOD')
        tier_stars = {'GOOD': '★', 'GREAT': '★★★', 'INSANE': '★★★★★'}.get(tier_label, '★')
        print(f"\n*** BOSS WEAPON DROP: {tier_stars} {tier_label} {tier_stars}")
        print(f"*** {boss_weapon['name']} ({boss_weapon['rarity'].upper()}) ")
        print(f"[Scaled for your level: {player.level}]")
        
        # Show weapon comparison
        comparison = WeaponComparison.compare_weapons(boss_weapon, player.weapon, player)
        print(comparison)
        
        # Ask to equip like weapon cache
        try:
            if input("\nEquip this weapon? (y/n): ").strip().lower() in ['y', 'yes']:
                if player.weapon:
                    player.inventory_weapons.append(player.weapon)
                    player.inventory.append(f"WEAPON: {player.weapon['name']}")
                    print(f"Stored previous weapon: {player.weapon['name']}")
                player.equip_weapon(boss_weapon)
            else:
                # Store boss weapon in inventory
                if player.can_add_item():
                    player.inventory_weapons.append(boss_weapon)
                    player.inventory.append(f"WEAPON: {boss_weapon['name']}")
                    print(f"Stored: {boss_weapon['name']}")
                else:
                    print("Inventory full! Boss weapon left on ground.")
                    room.items.append("weapon cache")  # Add it back as a cache
        except KeyboardInterrupt:
            # On interrupt, store weapon if possible
            if player.can_add_item():
                player.inventory_weapons.append(boss_weapon)
                player.inventory.append(f"WEAPON: {boss_weapon['name']}")
                print(f"Stored: {boss_weapon['name']}")
        
        bonus = boss_config['stat_bonus']
        for stat in player.stats:
            player.stats[stat] += bonus
        
        player.health = player.max_health
        player.mana = player.max_mana
        
        print(f"\n*** All stats +{bonus}! Fully healed!")
        return True

#################################################################################
# COMMAND HANDLER WITH DECORATOR PATTERN
#################################################################################
class CommandRegistry:
    """Command registration system"""
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

#################################################################################
# GAME CLASS WITH ALL BUG FIXES
#################################################################################
class Game:
    """Main game controller"""
    
    def __init__(self):
        self.player: Optional[Player] = None
        self.floors: Optional[Dict[int, Dict[str, Room]]] = None
        self.running = True
        self.combat = None
        self.registry = CommandRegistry()
        self._register_commands()
        
    def _register_commands(self):
        """Register all game commands"""
        r = self.registry.register
        
        @r('help', 'h')
        def cmd_help(g): g.show_help()
        
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
            g.fight_enemy(' '.join(args))
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
            g.use_special_item(' '.join(args))
            g.show_room_summary()
        
        @r('upgrade')
        def cmd_upgrade(g): 
            g.upgrade_class()
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
                print("You need a map to use this command!")
                print("Look for one on the ground or buy one from a merchant.")
        
        @r('save')
        def cmd_save(g): g.save_game()
        
        @r('load')
        def cmd_load(g): g.load_game()
        
        @r('delete')
        def cmd_delete(g): g.delete_save()
        
        @r('quit', 'exit')
        def cmd_quit(g): g.quit_game()
    
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
            print("  4. Quit")
            print()
            
            try:
                choice = input("\nChoice: ").strip()
                
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
                    # After delete, loop back to menu
                    continue
                
                elif choice == '4':
                    print("\nGoodbye!")
                    return  # Exit game entirely
                
                else:
                    print("Invalid choice. Please enter 1, 2, 3, or 4.")
                    continue
                    
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                return
        
        # Game starts here after menu selection
        self.combat = CombatSystem(self)
        print("\nType 'help' for commands")
        self.look_around()
        self.show_room_summary()
        self._game_loop()
    
    def _game_loop(self):
        """Main game loop"""
        while self.running:
            try:
                cmd_input = input("\n> ").strip().lower()
                if not cmd_input:
                    continue
                
                parts = cmd_input.split()
                command = parts[0]
                args = parts[1:]
                
                self.registry.execute(command, args, self)

                if self.player and self.running:
                    self.player.show_status_summary()
                    
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
            name = input("Name: ").strip() or "Adventurer"
            
            print("\n╔════════════════════════════════╗")
            print("║  Choose Your Class             ║")
            print("╠════════════════════════════════╣")
            print("║ 1. Warrior   — Strength & grit ║")
            print("║ 2. Mage      — Arcane power    ║")
            print("║ 3. Rogue     — Speed & crits   ║")
            print("║ 4. Paladin   — Holy champion   ║")
            print("║ 5. Berserker — Pure rage       ║")
            print("╚════════════════════════════════╝")
            choice = input("Class: ").strip()
            char_class = {
                '1': 'warrior', '2': 'mage', '3': 'rogue',
                '4': 'paladin', '5': 'berserker'
            }.get(choice, 'warrior')

            # Class description
            descriptions = {
                'warrior':   'STR-focused melee fighter. High HP, grows into a Titan Knight.',
                'mage':      'INT/Arcane spellcaster. Fragile but devastating with magic.',
                'rogue':     'AGI/Luck master. Highest crit rate, stealth weapons.',
                'paladin':   'Holy melee warrior. Divine Smite ability, holy weapon bonus.',
                'berserker': 'Rage fighter. Built-in damage scaling as HP drops. Massive HP pool.',
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
                wchoice = int(input("Choose (1-8): ").strip()) - 1
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
    
    def _generate_dungeon(self):
        """Generate complete dungeon with unique item tracking"""
        logger.info("Starting dungeon generation...")
        print("\n*** Generating dungeon...")
        self.floors = {}
        
        # Track unique items across entire dungeon (items that should only spawn once)
        unique_item_types = {'rusty key', 'bone key', 'torch', 'ancient medallion'}
        
        # Pre-locate the special destination templates by name for injection
        vault_tmpl      = next(t for t in RoomTemplateConfig.SPECIAL_ROOMS if t.name == 'Locked Vault')
        bone_crypt_tmpl = next(t for t in RoomTemplateConfig.SPECIAL_ROOMS if t.name == 'Bone Crypt')

        # Track which floor each key lands on so we can guarantee a destination
        key_floor: dict = {}   # key_item_str -> floor_num

        total_rooms = 0
        all_floors_rooms: dict = {}  # floor_num -> rooms dict (built first pass)

        for floor_num in range(1, GameConstants.NUM_FLOORS + 1):
            print(f"Floor {floor_num}...", end=" ")
            rooms = {}

            if floor_num == 1:
                start_id = 'start'
                # Rusty key always starts in the entrance; record which floor it's on
                start_items = ['health potion', 'old map', 'rusty key']
                key_floor['rusty key'] = 1
                self.player.unique_items_spawned.add('rusty key')
                rooms[start_id] = Room("Entrance Hall", "The dungeon entrance awaits.", floor_num,
                                      start_items, {}, [],
                                      "Adamus the Loyal has set up shop here. Use 'shop' to trade.")
            else:
                start_id = f"floor{floor_num}_start"
                rooms[start_id] = Room(f"Floor {floor_num} Entrance", f"You arrive at floor {floor_num}.",
                                      floor_num, ['health potion'], {}, [],
                                      "Adamus the Loyal has set up shop here. Use 'shop' to trade.")

            templates = RoomTemplateConfig.get_templates_for_floor(floor_num)
            enemies   = RoomTemplateConfig.get_enemies_for_floor(floor_num)
            num_rooms = random.randint(GameConstants.MIN_ROOMS_PER_FLOOR - 2, GameConstants.MAX_ROOMS_PER_FLOOR - 2)

            # Filter out destination-only templates from the random pool so they
            # are only injected via the pairing logic below
            DEST_NAMES = {'Locked Vault', 'Bone Crypt'}
            pool = [t for t in templates if t.name not in DEST_NAMES]
            selected = random.sample(pool, min(num_rooms, len(pool)))

            THINNED_ITEMS = {'health potion', 'energy drink', 'vitality tonic'}

            for i, template in enumerate(selected):
                room_id    = f"floor{floor_num}_room{i+1}"
                room_enemies = self._get_unique_enemies(enemies, template.enemy_count)

                if template.special_type == 'treasure':
                    room_enemies = ['treasure guardian'] + room_enemies[:1]

                items = self._filter_items_by_class(template.items.copy())
                filtered_items = []
                for item in items:
                    if item in unique_item_types:
                        if item not in self.player.unique_items_spawned:
                            filtered_items.append(item)
                            self.player.unique_items_spawned.add(item)
                            # Record which floor this key landed on
                            if item in ('rusty key', 'bone key'):
                                key_floor[item] = floor_num
                    elif item in THINNED_ITEMS and random.random() < 0.5:
                        pass
                    else:
                        filtered_items.append(item)

                rooms[room_id] = Room(template.name, template.description, floor_num,
                                     filtered_items, {}, room_enemies, template.atmosphere)

            all_floors_rooms[floor_num] = rooms

        # ── Second pass: inject destination rooms near their keys ─
        def _inject_dest(tmpl, key_name, search_floors):
            """Add destination room to the earliest floor in search_floors
               that doesn't already have one."""
            for fnum in search_floors:
                frooms = all_floors_rooms[fnum]
                if any(r.name == tmpl.name for r in frooms.values()):
                    return  # already there
            # Pick the first floor in range and inject
            fnum = search_floors[0]
            frooms = all_floors_rooms[fnum]
            enemies = RoomTemplateConfig.get_enemies_for_floor(fnum)
            idx = len(frooms)
            room_id = f"floor{fnum}_dest{idx}"
            room_enemies = self._get_unique_enemies(enemies, tmpl.enemy_count)
            frooms[room_id] = Room(tmpl.name, tmpl.description, fnum,
                                   tmpl.items.copy(), {}, room_enemies, tmpl.atmosphere)
            print(f"  [injected {tmpl.name} on F{fnum}]", end=" ")

        # Rusty key → Locked Vault should appear on the same floor or the next
        if 'rusty key' in key_floor:
            kf = key_floor['rusty key']
            dest_floors = list(range(kf, min(kf + 2, GameConstants.NUM_FLOORS) + 1))
            _inject_dest(vault_tmpl, 'rusty key', dest_floors)

        # Bone key → Bone Crypt should appear on the same floor or within 2 floors
        if 'bone key' in key_floor:
            kf = key_floor['bone key']
            dest_floors = list(range(kf, min(kf + 2, GameConstants.NUM_FLOORS) + 1))
            _inject_dest(bone_crypt_tmpl, 'bone key', dest_floors)

        # Now finalise: move rooms back into self.floors with boss/stairs rooms
        for floor_num in range(1, GameConstants.NUM_FLOORS + 1):
            rooms = all_floors_rooms[floor_num]
            
            boss_template = BossConfig.get_boss_room_template(floor_num)
            boss_config = BossConfig.generate(floor_num)
            boss_room_id = f"floor{floor_num}_boss"
            # Don't include champion's prize in initial items - added after boss defeat
            rooms[boss_room_id] = Room(boss_template.name, boss_template.description, floor_num,
                                       ['ultimate health potion'],  # FIXED: No champion's prize until boss defeated
                                       {}, [boss_config['name']], boss_template.atmosphere)
            
            if floor_num < GameConstants.NUM_FLOORS:
                stairs_id = f"floor{floor_num}_stairs"
                rooms[stairs_id] = Room("Ancient Stairway", "Stone stairs descend deeper.", floor_num)
            # === GUARANTEED PLEASURE SANCTUM (exactly once on floors 6-9) ===
            if not hasattr(self, 'pleasure_sanctum_spawned'):
                self.pleasure_sanctum_spawned = False

            if 6 <= floor_num <= 9 and not self.pleasure_sanctum_spawned:
                # 100% chance on one random floor between 6-9
                if random.random() < 0.33 or floor_num == 9:   # higher chance on later floors
                    sex_id = f"floor{floor_num}_pleasure"
                    sex_tmpl = next((t for t in RoomTemplateConfig.SPECIAL_ROOMS if t.name == "Pleasure Sanctum"), None)
                    if sex_tmpl:
                        rooms[sex_id] = Room(
                            sex_tmpl.name, sex_tmpl.description, floor_num,
                            sex_tmpl.items.copy(), {'out': list(rooms.keys())[0]}, [], sex_tmpl.atmosphere
                        )
                        # Connect via secret exit from a random normal room
                        normal_rooms = [rid for rid in rooms 
                                      if 'boss' not in rid and 'stairs' not in rid 
                                      and 'pleasure' not in rid]
                        if normal_rooms:
                            connector = random.choice(normal_rooms)
                            rooms[connector].exits['secret'] = sex_id
                            rooms[sex_id].exits['out'] = connector
                            self.pleasure_sanctum_spawned = True
                            print(f"  [Pleasure Sanctum seeded on floor {floor_num}]", end=" ")
            self._connect_rooms(rooms, start_id)
            
            self.floors[floor_num] = rooms
            total_rooms += len(rooms)
            print(f"{len(rooms)} rooms")
        
        for floor_num in range(1, GameConstants.NUM_FLOORS):
            stairs_id = f"floor{floor_num}_stairs"
            next_start = f"floor{floor_num+1}_start"
            if stairs_id in self.floors[floor_num] and next_start in self.floors.get(floor_num + 1, {}):
                self.floors[floor_num][stairs_id].exits['down'] = next_start
                self.floors[floor_num + 1][next_start].exits['up'] = stairs_id
        
        logger.info(f"Dungeon generated: {GameConstants.NUM_FLOORS} floors, {total_rooms} total rooms")
        print("*** Complete!")
    
    def _get_unique_enemies(self, pool: List[str], count: int) -> List[str]:
        """Get unique enemies from pool"""
        available = pool.copy()
        random.shuffle(available)
        return available[:min(count, len(available))]
    
    def _filter_items_by_class(self, items: List[str]) -> List[str]:
        """Replace mana items for non-mages"""
        if self.player.character_class == 'mage':
            return items
        
        replacements = {
            'magic scroll': 'energy drink',
            'ice crystal': 'power ring',
            'mana flower': 'armor piece'
        }
        return [replacements.get(i, i) for i in items]
    
    def _connect_rooms(self, rooms: Dict[str, Room], start_id: str):
        """Connect all rooms in floor"""
        directions = ['north', 'south', 'east', 'west']
        reverse = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east'}
        
        room_ids = list(rooms.keys())
        connected = {start_id}
        unconnected = set(room_ids) - connected
        
        while unconnected:
            current = random.choice(list(connected))
            target = random.choice(list(unconnected))
            
            available = [d for d in directions if d not in rooms[current].exits]
            if not available:
                continue
            
            direction = random.choice(available)
            rooms[current].exits[direction] = target
            rooms[target].exits[reverse[direction]] = current
            
            connected.add(target)
            unconnected.remove(target)
        
        for _ in range(len(room_ids) // 3):
            r1, r2 = random.sample(room_ids, 2)
            if r2 not in rooms[r1].exits.values():
                available = [d for d in directions if d not in rooms[r1].exits]
                if available:
                    direction = random.choice(available)
                    if reverse[direction] not in rooms[r2].exits:
                        rooms[r1].exits[direction] = r2
                        rooms[r2].exits[reverse[direction]] = r1
    
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
        
        is_boss = any(matching == BossConfig.generate(f)['name'] for f in range(1, 11))

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

        if not item_name:
            print("Use what?")
            return

        room = self.get_current_room()

        # ====================== PLEASURE SANCTUM ======================
        if room.name == "Pleasure Sanctum":
            print("\n" + "═"*75)
            print("                  THE PLEASURE SANCTUM")
            print("═"*75)
            print("The heavy doors seal behind you. The air is thick with the scent of musk, sweat, and sex.")
            print("Dozens of beings — succubi, incubi, tentacled void elementals, muscular orcs, lithe dark elves,")
            print("demonic knights, harpies, minotaurs, and more — turn their glowing eyes upon you with pure lust.")

            consent = input("\nYour pulse races. Do you wish to fully surrender to the orgy? (y/n): ").strip().lower()
            if consent not in ('y', 'yes'):
                print("You step back. The creatures sigh with disappointment but respect your choice.")
                return

            print("\nYou let your clothes fall to the floor and step into the center of the chamber...\n")

            # ==================== VERY LONG DETAILED SCENE ====================
            print("A towering incubus with obsidian skin and a massive ridged cock immediately lifts you off the ground.")
            print("He impales you in one powerful thrust, stretching you wide as he begins pounding you mercilessly.")
            print("At the same time, a voluptuous succubus straddles your face, grinding her dripping, sweet pussy against your tongue.")
            print("Thick, writhing tentacles from a shimmering void elemental force their way into your mouth and ass,")
            print("pulsing and vibrating while secreting a warm, aphrodisiac fluid that makes your whole body burn with need.")

            print("Two muscular orcs grab your hands, wrapping them around their thick cocks as they grunt and thrust.")
            print("A lithe dark elf drops between your legs, licking and sucking wherever she can reach, her tongue incredibly skilled.")
            print("A celestial knight with glowing wings fucks the succubus on your face, his heavy balls slapping against your forehead.")
            print("A harpy perches above you, lowering herself onto your cock (or using a tentacle on you if female), riding you wildly.")

            print("Hours pass in a blur of flesh and pleasure. You are passed from body to body like a toy.")
            print("The minotaur breeds you so deeply you can barely breathe, flooding you with hot cum.")
            print("A group of demonic knights take turns using every hole while the tentacles continue their relentless assault.")
            print("You lose count of how many times you cum — each orgasm more intense than the last as the runes on the walls glow brighter.")
            print("Cum drips from every part of your body. Your mind goes blank with overwhelming ecstasy.")
            print("Succubi ride you until you’re dry, only for more creatures to take their place.")
            print("You are fucked in every position imaginable — suspended in the air, on all fours, pinned against the wall,")
            print("sandwiched between multiple bodies, and more. The chamber echoes with wet sounds, moans, and your own uncontrollable cries of pleasure.\n")

            print("By the time the orgy finally slows, you lie in a pool of mixed fluids, trembling, exhausted, and glowing with sexual energy.")
            print("The creatures gently caress you, whispering praises as the runes permanently mark you with lustful power.\n")

            print("*** You have been claimed by the Pleasure Sanctum. ***\n")

            # Reward choice
            print("The satisfied creatures offer you one final gift as thanks:")
            print("1. Vibrating Butt Plug of Endless Lust     (+8 Lust — enemies become weak and distracted)")
            print("2. The Eternal Splooger                    (Mythic living dildo-sword with Splooge trait)")
            
            try:
                choice = int(input("\nChoose your reward (1 or 2): ").strip())
                if choice == 1:
                    self.player.inventory.append('vibrating butt plug')
                    self.player.stats['lust'] = self.player.stats.get('lust', 5) + 8
                    print("*** You are now wearing the Vibrating Butt Plug! Lust +8 ***")
                    print("   Your body radiates sexual energy that weakens and distracts enemies.")
                else:
                    weapon = GameConstants.SPECIAL_WEAPONS['the eternal splooger'].copy()
                    if not self.player.weapon or input("Equip The Eternal Splooger now? (y/n): ").strip().lower() in ['y', 'yes']:
                        self.player.equip_weapon(weapon)
                    else:
                        self.player.add_weapon_to_inventory(weapon)
                    print("*** You now wield The Eternal Splooger! It throbs with unholy power. ***")
            except:
                # Default reward
                self.player.inventory.append('vibrating butt plug')
                self.player.stats['lust'] = self.player.stats.get('lust', 5) + 8
                print("*** You received the Vibrating Butt Plug! ***")

            self.player.health = self.player.max_health
            self.player.mana = self.player.max_mana
            print("You leave the Sanctum fully restored and radiating raw sexual energy.")
            return

        if item_name == 'old map' and item_name in self.player.special_items:
            print("You study the old map...")
            self.show_map()
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
                print("You hold up the torch. Nothing unusual here.")
        
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
                print("You examine the key. It looks like it would fit a large lock...")
        
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
                print("The bone key rattles ominously. This is meant for a bone door...")
        
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
                print("The demon seal pulses with dark energy. It's meant for demons...")
        
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
                print("The crystal shard glows softly. It needs a crystal mechanism...")
        
        # VOID ESSENCE - Stabilize void portals
        elif action_type == 'd20' and item_name == "gambler's d20":
            room = self.get_current_room()
            roll = random.randint(1, 20)
            if room.enemies:
                enemy = room.enemies[0]
                print(f"\n  ⚄ You roll the d20 against {enemy}... {roll}!")
                if roll == 20:
                    print(f"  ★ NATURAL 20! Pure luck obliterates {enemy}!")
                    print(f"  (The d20 shatters. One nat 20 per die.)")
                    self.player.inventory.remove("gambler's d20")
                    room.enemies.remove(enemy)
                    self.player.gain_experience(GameConstants.ENEMIES.get(enemy.lower(), {}).get('exp', 50))
                elif roll == 1:
                    print(f"  ✗ Nat 1. You trip, the d20 rolls into a crack. {enemy} looks delighted.")
                    self.player.inventory.remove("gambler's d20")
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
                print("The void essence writhes with otherworldly power. It needs a void tear...")
        
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
                print("The primordial rune hums with ancient power. It belongs on a monument...")
        
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
                print("You hold the medallion. It should be placed on an altar...")
        
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
    
    def open_shop(self):
        """Open shop"""
        if self.player.current_floor > 1 and 'start' not in self.player.current_room:
            print("! No shop here. Visit the floor's starting room to find a merchant.")
            return
        
        if self.player.current_floor == 1 and self.player.current_room != 'start':
            print("! No shop here. Return to the entrance hall to find a merchant.")
            return
        
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
        import random as _r
        greeting = _r.choice(ADAMUS_GREETINGS)
        quip = _r.choice(ADAMUS_QUIPS)
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

        print(f"\n  Stock: {tier_name}  |  {len(items)} items available")
        print("-"*50)
        for i, (name, price, desc) in enumerate(items, 1):
            can_afford = "  " if self.player.gold_coins >= price else "✗ "
            print(f"  {can_afford}{i:>2}. {name:<28} {price:>3}g   {desc}")
        print(f"\n  {len(items)+1}. Leave")
        print("-"*50)

        try:
            choice = int(input("\n  Buy #: ").strip())
            if choice == len(items) + 1:
                return

            if 1 <= choice <= len(items):
                item, price, desc = items[choice - 1]
                if self.player.gold_coins >= price:
                    if self.player.can_add_item() or item in GameConstants.WEARABLE_ITEMS:
                        self.player.gold_coins -= price
                        if item == 'weapon cache':
                            new_weapon = WeaponSystem.generate_weapon(self.player)
                            comparison = WeaponComparison.compare_weapons(new_weapon, self.player.weapon, self.player)
                            print(comparison)
                            try:
                                if input("  Equip? (y/n): ").strip().lower() in ('y','yes'):
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
                        ADAMUS_SALES = [
                            f"Fine. Here's your {item}. Don't come crying to me when it doesn't save you.",
                            f"There. {item}. Pleasure doing business — emphasis on 'business', none on 'pleasure'.",
                            f"{item}, gone. Your gold, gone. My patience, also gone.",
                            f"Enjoy your {item}. It's better than you deserve.",
                            f"Here. {item}. Try not to die before you get any use out of it.",
                        ]
                        import random as _r2
                        print(f"  '{_r2.choice(ADAMUS_SALES)}'")
                        print(f"  Gold remaining: {self.player.gold_coins}g")
                    else:
                        print("Inventory full!")
                else:
                    print(f"Not enough gold! Need {price}g, have {self.player.gold_coins}g")
        except (ValueError, KeyboardInterrupt):
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
    
    def quit_game(self):
        """Exit game"""
        try:
            if input("\nSave before quitting? (y/n): ").strip().lower() in ['y', 'yes']:
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

#################################################################################
# MAIN ENTRY POINT
#################################################################################
def main():
    """Main entry point"""
    try:
        game = Game()
        game.start_game()
    except KeyboardInterrupt:
        print("\n\nGame interrupted. Goodbye!")
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n\nFatal error: {e}")
        print("Please report this bug!")

if __name__ == "__main__":
    main()