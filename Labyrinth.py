"""
================================================================================
LABYRINTH  —  A 10-Floor Dungeon RPG
================================================================================
Version : 7.5.2

CHANGELOG 7.5.2:
- COMBAT: Enemy behaviour system — 15 enemies now fight distinctly
  Resistance enemies (stone golem, armored skeleton, ancient guardian, titan spawn)
  Regen enemies (shadow wraith, void spawn, celestial knight, shadow beast)
  Status inflicters (ghoul=bleed, cultist=weaken, corrupted mage=poison, etc)
  Special attacks every N turns (lightning wisp, cosmic horror, etc)
  Buff-others (dark cultist empowers allies each turn)
  Enemy intent shown before each fight
- COMBAT: Player status effects — bleed / poison / weaken
  Inflicted in combat; tick on each enemy turn AND when moving between rooms
  Makes healing items genuinely necessary on later floors
- ITEMS: Conditional consumables
  Elixir of Desperation  — heals 60%% of missing HP (better when low)
  Void Tonic             — converts next hit into 30 MP
  Berserkers Draught     — heals 40%% of damage taken this fight
  Antidote               — cures bleed/poison/weaken + 10 HP
  Battle Tincture        — next 3 attacks deal 30%% more damage
- ITEMS: Cursed wearables — powerful with a cost
  Ring of the Dying (+20 STR / -30 max HP)
  Void Shard Pendant (+15 AGI / -15 max HP)
  Berserkers Brand (+12 STR / take 15%% more damage)
  Assassins Mark (+18 LCK / -20 max HP)
  Soul Chain (+10 VIT / take 10%% more damage)
- LORE: Floor entry text — atmospheric blurb when descending each floor
- LORE: Boss intro monologues — each boss speaks before combat begins
- LORE: Discoverable story journal (5 entries, floors 2/4/5/7/9)
  Researcher Varek's notes piece together why the dungeon exists
  and what the Reality Breaker actually is
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
    VERSION = "7.5.2"
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
                           'luck': 8, 'vitality': 14, 'arcane': 5, 'faith': 5},
            'health_per_level': 15, 'inventory_slots': 5,
            'weapon_types': ['melee'],
            'stat_growth': {'strength': 3, 'intelligence': 1, 'agility': 1,
                            'luck': 0, 'vitality': 2, 'arcane': 0, 'faith': 0},
        },
        'mage': {
            'base_health': 80, 'base_mana': 150,
            # Arcane 14 → reduces mana cost, multiplies magic damage
            'base_stats': {'strength': 8, 'intelligence': 15, 'agility': 10,
                           'luck': 12, 'vitality': 6, 'arcane': 14, 'faith': 5},
            'health_per_level': 8, 'inventory_slots': 5,
            'weapon_types': ['magic'],
            'stat_growth': {'strength': 1, 'intelligence': 3, 'agility': 1,
                            'luck': 1, 'vitality': 0, 'arcane': 2, 'faith': 0},
        },
        'rogue': {
            'base_health': 100, 'base_mana': 0,
            'base_stats': {'strength': 10, 'intelligence': 10, 'agility': 15,
                           'luck': 16, 'vitality': 10, 'arcane': 5, 'faith': 5},
            'health_per_level': 12, 'inventory_slots': 5,
            'weapon_types': ['stealth'],
            'stat_growth': {'strength': 1, 'intelligence': 1, 'agility': 3,
                            'luck': 2, 'vitality': 1, 'arcane': 0, 'faith': 0},
        },
        'paladin': {
            'base_health': 110, 'base_mana': 60,
            # Holy warrior: moderate strength, great vitality, steady luck
            # Passive: holy weapons deal an extra +25% (stacks with trait bonus)
            # Boss ability: Divine Smite (costs 20 mana, guaranteed holy damage)
            'base_stats': {'strength': 13, 'intelligence': 10, 'agility': 8,
                           'luck': 10, 'vitality': 15, 'arcane': 5, 'faith': 14},
            'health_per_level': 13, 'inventory_slots': 5,
            'weapon_types': ['melee'],
            'stat_growth': {'strength': 2, 'intelligence': 1, 'agility': 1,
                            'luck': 1, 'vitality': 2, 'arcane': 0, 'faith': 2},
        },
        'berserker': {
            'base_health': 140, 'base_mana': 0,
            # Rage class: highest raw strength and vitality, lowest agility/luck
            # Passive: berserker scaling always applies regardless of weapon trait
            # Boss ability: Rage (free, boosts next attack by 50%, usable once per fight)
            'base_stats': {'strength': 18, 'intelligence': 5, 'agility': 7,
                           'luck': 6, 'vitality': 18, 'arcane': 5, 'faith': 5},
            'health_per_level': 18, 'inventory_slots': 5,
            'weapon_types': ['melee'],
            'stat_growth': {'strength': 4, 'intelligence': 0, 'agility': 1,
                            'luck': 0, 'vitality': 3, 'arcane': 0, 'faith': 0},
        },
        'void_walker': {
            # Unlocked after first game clear. Lowest HP, no mana — uses Void Essence.
            # Passive — Void Resonance: crits deal 2.5x instead of 1.75x.
            # Passive — Void Hunger: vampiric trait gives 25% lifesteal (vs 12%).
            # Boss ability — Phase: once per fight, skip the next enemy attack entirely.
            'base_health': 65, 'base_mana': 0,
            'base_stats': {'strength': 9, 'intelligence': 12, 'agility': 18,
                           'luck': 14, 'vitality': 6, 'arcane': 5, 'faith': 5},
            'health_per_level': 7, 'inventory_slots': 6,
            'weapon_types': ['stealth'],
            'stat_growth': {'strength': 1, 'intelligence': 2, 'agility': 2,
                            'luck': 2, 'vitality': 0, 'arcane': 0, 'faith': 0},
        },
    }
    
    CLASS_NAMES = {
        1: {'warrior': 'Warrior',       'mage': 'Mage',          'rogue': 'Rogue',
            'paladin': 'Paladin',       'berserker': 'Berserker', 'void_walker': 'Void Walker'},
        2: {'warrior': 'Vanguard',      'mage': 'Sorcerer',      'rogue': 'Assassin',
            'paladin': 'Crusader',      'berserker': 'Bloodrage',  'void_walker': 'Void Stalker'},
        3: {'warrior': 'Warlord',       'mage': 'Archmage',      'rogue': 'Shadow Master',
            'paladin': 'Holy Knight',   'berserker': 'War Champion','void_walker': 'Void Phantom'},
        4: {'warrior': 'Iron Titan',    'mage': 'Spellweaver',   'rogue': 'Phantom',
            'paladin': 'Divine Shield', 'berserker': 'Doom Bringer','void_walker': 'Reality Thief'},
        5: {'warrior': 'Titan Knight',  'mage': 'Void Sage',     'rogue': 'Death Walker',
            'paladin': 'Avatar of Light','berserker': 'Chaos Titan','void_walker': 'Void Sovereign'},
    }

    # Upgrade thresholds — one per ~2 floors so the final tier lands at floor 9-10
    # Level 4 → Tier 2  (floors 1-2)
    # Level 8 → Tier 3  (floors 3-4)
    # Level 12 → Tier 4 (floors 5-6)
    # Level 16 → Tier 5 (floors 7-8)
    # Level 20 → Tier 5 complete (floor 9-10, no further upgrade)
    CLASS_UPGRADE_LEVELS = [4, 8, 12, 16]
    RARITY_BOOST_PER_TIER = 0.05
    
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
    # HP raised ~35% so weapon power alone can't trivialize under-leveled boss fights
    ENEMIES = {
        'sewer rat':        {'health':  20, 'damage':  7, 'exp':  15, 'desc': 'A disease-ridden rat with glowing red eyes'},
        'goblin':           {'health':  34, 'damage': 10, 'exp':  25, 'desc': 'A small, green-skinned creature wielding a crude club'},
        'skeleton':         {'health':  41, 'damage': 13, 'exp':  30, 'desc': 'Animated bones held together by dark magic'},
        'prison guard':     {'health':  54, 'damage': 15, 'exp':  35, 'desc': 'A corrupted guard in tattered armor'},
        'armored skeleton': {'health':  61, 'damage': 18, 'exp':  45, 'desc': 'A skeleton warrior clad in ancient armor'},
        'shadow wraith':    {'health':  68, 'damage': 23, 'exp':  55, 'desc': 'A spectral being that feeds on fear'},
        'corrupted mage':   {'health':  54, 'damage': 25, 'exp':  60, 'desc': 'A once-noble mage consumed by forbidden magic'},
        'ghoul':            {'health':  74, 'damage': 20, 'exp':  50, 'desc': 'A flesh-eating undead creature'},
        'fire elemental':   {'health':  81, 'damage': 28, 'exp':  70, 'desc': 'A being of pure flame and rage'},
        'ice elemental':    {'health':  78, 'damage': 25, 'exp':  68, 'desc': 'A crystalline creature radiating freezing cold'},
        'lightning wisp':   {'health':  68, 'damage': 31, 'exp':  75, 'desc': 'Crackling energy given form'},
        'stone golem':      {'health': 108, 'damage': 23, 'exp':  65, 'desc': 'A massive construct of animated stone'},
        'lesser demon':     {'health':  95, 'damage': 33, 'exp':  85, 'desc': 'A horned creature from the abyss'},
        'dark cultist':     {'health':  88, 'damage': 30, 'exp':  80, 'desc': 'A fanatic devoted to dark powers'},
        'shadow beast':     {'health': 101, 'damage': 35, 'exp':  90, 'desc': 'A monstrous predator born of darkness'},
        'void spawn':       {'health': 108, 'damage': 38, 'exp':  95, 'desc': 'An aberration from beyond reality'},
        'ancient guardian': {'health': 122, 'damage': 40, 'exp': 110, 'desc': 'An eternal sentinel of forgotten secrets'},
        'cosmic horror':    {'health': 115, 'damage': 44, 'exp': 120, 'desc': 'An incomprehensible being from the void'},
        'titan spawn':      {'health': 135, 'damage': 38, 'exp': 105, 'desc': 'Offspring of the primordial titans'},
        'celestial knight': {'health': 128, 'damage': 43, 'exp': 115, 'desc': 'A fallen warrior of the heavens'},
        'treasure guardian':{'health':  81, 'damage': 25, 'exp':  65, 'desc': 'A magical construct protecting valuable treasure'}
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
        'health potion':          {'heal': 30,   'type': 'health'},
        'ultimate health potion': {'heal': 'full','type': 'health'},
        'magic scroll':           {'heal': 25,   'type': 'mana'},
        'ice crystal':            {'heal': 50,   'type': 'mana'},
        'energy drink':           {'heal': 20,   'type': 'health'},
        'vitality tonic':         {'heal': 35,   'type': 'health'},
        'elixir of life':         {'heal': 50,   'type': 'health'},
        # Conditional consumables (v7.5.2)
        'elixir of desperation':  {'type': 'conditional', 'mode': 'pct_missing', 'pct': 0.60,
                                   'desc': 'Heals 60% of missing HP — far better the lower you are'},
        'void tonic':             {'type': 'conditional', 'mode': 'absorb',      'mana_on_hit': 30,
                                   'desc': 'Next hit converts to 30 MP instead of damage'},
        "berserker's draught":    {'type': 'conditional', 'mode': 'dmg_taken',   'pct': 0.40, 'min': 20,
                                   'desc': 'Heals 40% of damage taken this fight (minimum 20 HP)'},
        'antidote':               {'type': 'conditional', 'mode': 'cure',        'heal': 10,
                                   'desc': 'Cures bleed, poison, and weaken. Restores 10 HP'},
        'battle tincture':        {'type': 'conditional', 'mode': 'boost',       'turns': 3, 'mult': 1.30,
                                   'desc': 'Next 3 attacks deal 30% more damage'},
    }
    
    EXPERIENCE_ITEMS = {
        'experience gem': {'amount': 50},
        'victory scroll': {'amount': 75},
        'wisdom gem': {'amount': 100},
        'frozen artifact': {'amount': 100},
        'soul crystal': {'amount': 150}
    }
    
    WEARABLE_ITEMS = {
        # Standard wearables
        'armor piece':        {'stat': 'strength',     'bonus': 5},
        'cursed amulet':      {'stat': 'intelligence', 'bonus': 3},
        "nature's blessing":  {'stat': 'agility',      'bonus': 4},
        'healing herb':       {'stat': 'agility',      'bonus': 2},
        'mana flower':        {'stat': 'intelligence', 'bonus': 4},
        'power ring':         {'stat': 'strength',     'bonus': 4},
        'warrior charm':      {'stat': 'strength',     'bonus': 3},
        'swift boots':        {'stat': 'agility',      'bonus': 5},
        'leather bracer':     {'stat': 'agility',      'bonus': 3},
        'arcane pendant':     {'stat': 'intelligence', 'bonus': 6},
        'titan gauntlet':     {'stat': 'strength',     'bonus': 7},
        'shadow cloak':       {'stat': 'agility',      'bonus': 6},
        # Cursed wearables (v7.5.2) — powerful but with a cost
        'ring of the dying':  {'stat': 'strength',     'bonus': 20, 'hp_penalty': -30,
                               'cursed': True, 'desc': '+20 STR / -30 max HP'},
        'void shard pendant': {'stat': 'agility',      'bonus': 15, 'hp_penalty': -15,
                               'cursed': True, 'desc': '+15 AGI / -15 max HP'},
        "berserker's brand":  {'stat': 'strength',     'bonus': 12, 'dmg_taken_mult': 1.15,
                               'cursed': True, 'desc': '+12 STR / take 15% more damage'},
        "assassin's mark":    {'stat': 'luck',         'bonus': 18, 'hp_penalty': -20,
                               'cursed': True, 'desc': '+18 LCK / -20 max HP'},
        'soul chain':         {'stat': 'vitality',     'bonus': 10, 'dmg_taken_mult': 1.10,
                               'cursed': True, 'desc': '+10 VIT / take 10% more damage'},
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
        'primordial rune': 'rune',
        'journal_1': 'journal', 'journal_2': 'journal',
        'journal_3': 'journal', 'journal_4': 'journal',
        'journal_5': 'journal',
    }
    
    QUEST_ITEMS = ['rusty key', 'old map', 'legendary artifact', 'bone key', 
                   'ancient medallion', 'crystal shard', 'demon seal', 'void essence', 'primordial rune']
    
    # Tiered shop — each floor range unlocks new stock at scaled prices.
    # Format: { item_name: (price, description, class_filter_or_None) }
    SHOP_TIERS = {
        (1, 2): {   # Floors 1-2: The basics. Dirt cheap, nothing fancy.
            'health potion':      (5,  'Restores 30 HP',            None),
            'energy drink':       (6,  'Restores 20 HP',            None),
            'torch':              (7,  'Lights the Hidden Alcove',  None),
            'experience gem':     (12, 'Grants 50 XP',              None),
            'armor piece':        (15, '+5 STR wearable',           None),
            'power ring':         (18, '+4 STR wearable',           None),
            'warrior charm':      (14, '+3 STR wearable',           None),
            'magic scroll':       (10, 'Restores 25 MP',            'mage'),
        },
        (3, 4): {   # Floors 3-4: Crypt goods. Prices creep up.
            'health potion':      (8,  'Restores 30 HP',            None),
            'vitality tonic':     (12, 'Restores 35 HP',            None),
            'elixir of life':     (30, 'Restores 50 HP',            None),
            'experience gem':     (18, 'Grants 50 XP',              None),
            'wisdom gem':         (28, 'Grants 100 XP',             None),
            'swift boots':        (22, '+5 AGI wearable',           None),
            'leather bracer':     (20, '+3 AGI wearable',           None),
            'arcane pendant':     (30, '+6 INT wearable',           None),
            'soul crystal':       (32, 'Grants 150 XP',             None),
            'magic scroll':       (14, 'Restores 25 MP',            'mage'),
            'mana flower':        (25, '+4 INT wearable',           'mage'),
        },
        (5, 6): {   # Floors 5-6: Elemental hazards. Stock gets serious.
            'elixir of life':     (38, 'Restores 50 HP',            None),
            'ultimate health potion': (48, 'Full HP restore',       None),
            'vitality tonic':     (14, 'Restores 35 HP',            None),
            'wisdom gem':         (32, 'Grants 100 XP',             None),
            'soul crystal':       (38, 'Grants 150 XP',             None),
            'titan gauntlet':     (48, '+7 STR wearable',           None),
            'shadow cloak':       (44, '+6 AGI wearable',           None),
            "nature's blessing":  (35, '+4 AGI wearable',           None),
            'arcane pendant':     (35, '+6 INT wearable',           None),
            'cursed amulet':      (30, '+3 INT wearable (cursed)',   None),
            'magic scroll':       (18, 'Restores 25 MP',            'mage'),
            'ice crystal':        (40, 'Restores 50 MP',            'mage'),
        },
        (7, 8): {   # Floors 7-8: Demon territory. Adamus charges accordingly.
            'ultimate health potion': (55, 'Full HP restore',       None),
            'elixir of life':     (45, 'Restores 50 HP',            None),
            'soul crystal':       (44, 'Grants 150 XP',             None),
            'wisdom gem':         (38, 'Grants 100 XP',             None),
            'titan gauntlet':     (55, '+7 STR wearable',           None),
            'shadow cloak':       (52, '+6 AGI wearable',           None),
            'cursed amulet':      (38, '+3 INT wearable (cursed)',   None),
            'mana flower':        (42, '+4 INT wearable',           'mage'),
            'ice crystal':        (45, 'Restores 50 MP',            'mage'),
            'weapon cache':       (70, 'Random weapon — gamble!',   None),
        },
        (9, 10): {  # Floors 9-10: Endgame. Adamus knows you need it.
            'ultimate health potion': (65, 'Full HP restore',       None),
            'elixir of life':     (55, 'Restores 50 HP',            None),
            'soul crystal':       (52, 'Grants 150 XP',             None),
            'wisdom gem':         (48, 'Grants 100 XP',             None),
            'titan gauntlet':     (65, '+7 STR wearable',           None),
            'shadow cloak':       (62, '+6 AGI wearable',           None),
            'arcane pendant':     (55, '+6 INT wearable',           None),
            'cursed amulet':      (50, '+3 INT wearable (cursed)',   None),
            'ice crystal':        (52, 'Restores 50 MP',            'mage'),
            'weapon cache':       (85, 'Random weapon — gamble!',   None),
            'experience gem':     (45, 'Grants 50 XP',              None),
        },
    }

    # Keep flat dict for any legacy references
    SHOP_ITEMS = {
        'health potion': 5, 'magic scroll': 8, 'energy drink': 6,
        'experience gem': 15, 'armor piece': 20, 'power ring': 25,
        'swift boots': 25, 'elixir of life': 30, 'soul crystal': 40
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


    # ── NEW GAME+ ─────────────────────────────────────────────────
    # The Fractured Labyrinth — a corruption of the original dungeon.
    # Enemies have independent stat blocks; much tankier and harder hitting.

    # ── NG+ themed title screens ─────────────────────────────────
    # Each matches the original LABYRINTH style but distorted to theme.
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

    @classmethod
    def get_fusion(cls, class1: str, class2: str) -> Optional[Dict]:
        """Return fusion data for two classes, order-independent."""
        key = tuple(sorted([class1, class2]))
        return cls.FUSION_CLASSES.get(key)


    # ── Floor entry lore (v7.5.2) ────────────────────────────────
    # Shown when the player descends to each floor. Sets atmosphere.
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
    

    NG_PLUS_THEME_CONFIG = {
        'fractured_entry': {
            'floors': (1, 2),
            'enemies': ['fracture imp', 'void rat', 'corrupted soldier', 'mirror skeleton'],
            'templates': [
                RoomTemplate("The Shatter Hall", "The floor is cracked into floating tiles over an infinite drop. The walls breathe.",
                           "Every step sounds like glass breaking somewhere far below.", ['weapon cache', 'health potion']),
                RoomTemplate("Inverted Barracks", "The room is upside-down. Soldiers' bunks hang from the floor above you.",
                           "Gravity here works as a suggestion, not a rule.", ['armor piece', 'energy drink']),
                RoomTemplate("The Flickering Cell", "A prison cell that blinks in and out of existence every few seconds.",
                           "The prisoner inside is long gone. Or never existed.", ['rusty key', 'experience gem']),
                RoomTemplate("Error Corridor", "A hallway lined with identical doors. Each leads back here.",
                           "A message is burned into the wall: THIS SHOULD NOT EXIST.", ['weapon cache', 'health potion']),
                RoomTemplate("The Mirrored Pit", "A pit that reflects the ceiling. Or is the ceiling a pit?",
                           "Your reflection moves a half-second after you do.", ['torch', 'power ring']),
                RoomTemplate("Fragmented Office", "A warden's office, but the walls are missing and the furniture floats.",
                           "The paperwork is still in perfect order.", ['rusty key', 'armor piece']),
                RoomTemplate("The Null Passage", "A corridor where all colour has been drained. Everything is static grey.",
                           "Sounds are muffled here, like the dungeon is holding its breath.", ['weapon cache', 'vitality tonic']),
                RoomTemplate("Recursive Tunnel", "A tunnel that curves back on itself infinitely.",
                           "You have been here before. You will be here again.", ['experience gem', 'health potion']),
            ]
        },
        'mirror_crypt': {
            'floors': (3, 4),
            'enemies': ['mirror skeleton', 'null knight', 'echo wraith', 'void mage'],
            'templates': [
                RoomTemplate("The Echo Chamber", "Every sound you make returns seconds later, slightly wrong.",
                           "The dead here are copies of the dead elsewhere.", ['soul crystal', 'weapon cache']),
                RoomTemplate("Null Sarcophagi", "Stone coffins filled with nothing — not air, not darkness. Nothing.",
                           "Opening one reveals a void that stares back.", ['arcane pendant', 'weapon cache']),
                RoomTemplate("The Mirror Burial", "Burial niches that reflect an empty dungeon — the same dungeon, without you.",
                           "In every reflection, something watches.", ['wisdom gem', 'health potion']),
                RoomTemplate("Fractured Study", "A necromancer's study where the books write themselves.",
                           "The spells are ones that have never been cast and never will be.", ['magic scroll', 'arcane pendant']),
                RoomTemplate("Labyrinth of Skulls", "The skull-lined walls show different faces each time you look.",
                           "Some of the faces you recognise. That shouldn't be possible.", ['weapon cache', 'torch']),
                RoomTemplate("The Hollow Embalming", "Preparation tools for bodies that have no substance to preserve.",
                           "The scent of something sweet and wrong fills the room.", ['vitality tonic', 'soul crystal']),
                RoomTemplate("Inverted Tomb", "A tomb where the ceiling holds the graves and the floor holds the sky.",
                           "Climbing up means going down. Going down means nothing.", ['weapon cache', 'arcane pendant']),
                RoomTemplate("The Screaming Gallery", "Shadows that don't match any objects writhe between the pillars.",
                           "The screaming stopped three seconds ago. Or it hasn't started yet.", ['shadow cloak', 'wisdom gem']),
            ]
        },
        'null_fields': {
            'floors': (5, 6),
            'enemies': ['plasma elemental', 'crystal wraith', 'storm titan', 'void golem'],
            'templates': [
                RoomTemplate("The Boiling Dark", "Heat that has no source, so intense the air itself glows.",
                           "There is no flame here. The heat is a memory.", ['weapon cache', 'elixir of life']),
                RoomTemplate("Zero Chamber", "Absolute cold — not frozen, but returned to a state before temperature existed.",
                           "Sound dies here. So do most things.", ['ice crystal', 'frozen artifact']),
                RoomTemplate("The Static Storm", "Lightning that strikes upward and sideways and inward.",
                           "The static charges your teeth and fills your skull with white noise.", ['magic scroll', 'power ring']),
                RoomTemplate("Collapsed Nexus", "The point where all elements cancelled each other out.",
                           "What remains is worse than any of them alone.", ['weapon cache', 'titan gauntlet']),
                RoomTemplate("The Memory of Fire", "A room that burned so completely it left an impression on reality.",
                           "The fire is gone but its shape remains, licking at nothing.", ['elixir of life', 'soul crystal']),
                RoomTemplate("Null Ice Plains", "Ice that doesn't melt, doesn't reflect light, and makes no sound when broken.",
                           "Something is frozen inside every block. You can see it moving.", ['ice crystal', 'weapon cache']),
                RoomTemplate("The Last Lightning", "The final bolt of a storm that ended an age, still suspended mid-strike.",
                           "It has been falling for a thousand years.", ['weapon cache', 'arcane pendant']),
                RoomTemplate("Petrified Nothing", "Stone that was once alive but became something emptier than dead.",
                           "A void golem built this room and considers it a garden.", ['titan gauntlet', 'wisdom gem']),
            ]
        },
        'dread_sanctum': {
            'floors': (7, 8),
            'enemies': ['fracture demon', 'null cultist', 'shadow devourer', 'entropy spawn'],
            'templates': [
                RoomTemplate("The Unwriting Room", "Symbols cover the walls, but they erase themselves as you read them.",
                           "Someone — or something — doesn't want this knowledge to exist.", ['demon seal', 'weapon cache']),
                RoomTemplate("The Wrong Door", "A door to a place that predates the concept of place.",
                           "Whatever is on the other side has been trying to get through.", ['shadow cloak', 'soul crystal']),
                RoomTemplate("Collapsed Sanctum", "A holy place that was inverted so thoroughly it became its own opposite.",
                           "The altars face downward. The prayers go nowhere.", ['weapon cache', 'ultimate health potion']),
                RoomTemplate("The Null Pit", "A chasm that leads not to a floor but to the absence of floors.",
                           "Things climb up from it that were never in it.", ['demon seal', 'arcane pendant']),
                RoomTemplate("Entropy Circle", "The ritual circle glows with the light of dying stars.",
                           "Each line drawn here is one more thing unmade.", ['demon seal', 'soul crystal']),
                RoomTemplate("The Bleeding Altar", "An altar that bleeds from its stone, though stone cannot bleed.",
                           "The blood spells words in a language that hurts to see.", ['weapon cache', 'elixir of life']),
                RoomTemplate("The Eaten Cathedral", "A cathedral that has been consumed from the inside out.",
                           "What ate it is still here, digesting.", ['void essence', 'wisdom gem']),
                RoomTemplate("The Last Cultist's Room", "One cultist remained. Their writings cover every surface.",
                           "They describe the end in perfect detail. They seem pleased.", ['ultimate health potion', 'soul crystal']),
            ]
        },
        'void_core': {
            'floors': (9, 10),
            'enemies': ['void titan', 'fractured celestial', 'null guardian', 'entropy spawn'],
            'templates': [
                RoomTemplate("The Primordial Wound", "A tear in everything. Not just space — in the concept of space.",
                           "Looking at it directly is the last decision many have made.", ['primordial rune', 'titan gauntlet']),
                RoomTemplate("Observatory of Nothing", "Windows that look out onto the space before existence.",
                           "Stars that have not yet been born flicker there, uncertain.", ['weapon cache', 'wisdom gem']),
                RoomTemplate("The Final Corridor", "A hallway that exists at the end of all timelines simultaneously.",
                           "Every version of you that ever lived has walked this hall. Most did not leave.", ['soul crystal', 'legendary artifact']),
                RoomTemplate("The Unmade Room", "A room that was created and then taken back, but forgot to fully stop existing.",
                           "Physics applies here on a best-effort basis.", ['void essence', 'ultimate health potion']),
                RoomTemplate("The Titan's Last Breath", "The final exhale of something that held up the world.",
                           "The world it held is gone. The breath remains.", ['titan gauntlet', 'weapon cache']),
                RoomTemplate("The Forge of Ends", "Where weapons are made from collapsed stars.",
                           "The last weapon forged here was used on someone who deserved it.", ['weapon cache', 'wisdom gem']),
                RoomTemplate("The Memory Palace", "Every moment ever forgotten lives here, piled ceiling-high.",
                           "Walking through it means remembering things that never happened to you.", ['soul crystal', 'experience gem']),
                RoomTemplate("The Origin Armory", "Weapons forged before language existed to name them.",
                           "They hum with purpose that predates purpose itself.", ['weapon cache', 'weapon cache']),
            ]
        },
    }

    NG_PLUS_BOSS_ROOMS = {
        1:  ("The Glitch Arena",         "The arena flickers between states of existence. The crowd cheers in reverse.",
             "The Glitch manifests from a cascade of corrupted reality."),
        2:  ("The Architect's Ruin",     "A structure that was built and unbuilt simultaneously. It is both.",
             "The Undying Architect assembles itself from broken geometry."),
        3:  ("The Empty Throne",         "A throne room with no throne, no walls, and no floor. Just a king.",
             "The Hollow King rises from the nothing it has always been."),
        4:  ("The Darkness Itself",      "Not a dark room. Darkness, made into a room. There is a difference.",
             "The Shadow Itself detaches from every shadow in existence and converges here."),
        5:  ("The Recursive Furnace",    "A furnace that burns its own heat, forever.",
             "The Infernal Echo screams in a voice that has been screaming since before fire."),
        6:  ("The Cold Absolute",        "A place so cold that entropy itself has slowed. Almost stopped.",
             "Absolute Zero crystallises from the fundamental temperature of death."),
        7:  ("The Void Court",           "A court where nothing has standing and nothing is law.",
             "The Void Prince takes its throne made of absence."),
        8:  ("The Fracture Point",       "The exact location where this reality began to break.",
             "The Fracture God touches the crack it made and widens it."),
        9:  ("The First Place",          "The dungeon as it existed before the dungeon existed.",
             "The First Beast opens its eyes for the first time. Again."),
        10: ("The End of the Map",       "Beyond this point, the dungeon's own geometry gives up.",
             "The Origin Breaker stands at the place where everything stops. It is smiling."),
    }


    # ── Room template pools per NG+ world ────────────────────────
    # Fractured Labyrinth rooms are already in NG_PLUS_THEME_CONFIG.
    # The other 4 worlds share the same template structure.

    NG_PLUS_DROWNED_THEME = {
        'sunken_entry':   {'floors': (1, 2), 'templates': [
            RoomTemplate("The Flooded Gatehouse", "Knee-deep water. The gate is barnacled shut.",
                       "Fish circle in the water. They're the wrong shape for fish.", ['health potion', 'weapon cache']),
            RoomTemplate("Drowned Barracks", "Soldiers' quarters preserved in cold salt water.",
                       "The bunks still hold their occupants, who do not sleep.", ['armor piece', 'energy drink']),
            RoomTemplate("The Sunken Mess Hall", "Tables set for a meal never eaten. Everything is waterlogged.",
                       "The food still exists, technically.", ['health potion', 'golden coin']),
            RoomTemplate("The Coral Corridor", "Coral has grown through the walls and out the other side.",
                       "It pulses faintly. Coral doesn't do that.", ['weapon cache', 'experience gem']),
            RoomTemplate("The Tide Pool Chamber", "A chamber that floods and drains on a cycle.",
                       "Something lives in the current. It's waiting for the right tide.", ['rusty key', 'power ring']),
            RoomTemplate("Drowned Warden's Post", "The warden drowned at their desk. Still on duty.",
                       "The logbook is still being updated.", ['rusty key', 'armor piece']),
            RoomTemplate("The Brine Passage", "Salt-encrusted passage with water trickling from every crack.",
                       "The salt preserves things. Not in a good way.", ['weapon cache', 'vitality tonic']),
            RoomTemplate("The Kelp Forest", "A dungeon room overgrown with impossible kelp.",
                       "Things move between the fronds. You can't tell which things.", ['experience gem', 'health potion']),
        ]},
        'sunken_palace':  {'floors': (3, 4), 'templates': [
            RoomTemplate("The Drowned Throne Room", "A throne room with the throne chained to the floor.",
                       "The chain was added after the throne tried to leave.", ['soul crystal', 'weapon cache']),
            RoomTemplate("The Siren's Study", "Books written in ink that runs in the damp air.",
                       "Still readable. You wish they weren't.", ['magic scroll', 'arcane pendant']),
            RoomTemplate("The Saltwater Crypt", "Saltwater-preserved bodies in niches.",
                       "Preservation makes them look more alive, not less.", ['health potion', 'wisdom gem']),
            RoomTemplate("The Pressure Hall", "Walls that bow inward under the weight of water above.",
                       "The groaning is structural. Probably.", ['weapon cache', 'torch']),
            RoomTemplate("The Drowned Gallery", "Portraits of the royal family, all faces eaten away by brine.",
                       "The eyes remain on every one. They follow you.", ['shadow cloak', 'experience gem']),
            RoomTemplate("The Pearl Chamber", "Pearls the size of heads. Far too many pearls.",
                       "They glow faintly. Pearl doesn't glow.", ['weapon cache', 'arcane pendant']),
            RoomTemplate("The Sunken Ballroom", "A ballroom frozen mid-celebration.",
                       "The skeletons still dance. No music plays.", ['soul crystal', 'ultimate health potion']),
            RoomTemplate("The Cold Archive", "Records of the kingdom. All sealed in watertight cases.",
                       "Something doesn't want these opened.", ['wisdom gem', 'weapon cache']),
        ]},
        'coral_depths':   {'floors': (5, 6), 'templates': [
            RoomTemplate("The Reef Cavern", "A cavern made entirely of living coral.",
                       "Every surface hums with something between life and not.", ['weapon cache', 'elixir of life']),
            RoomTemplate("The Bioluminescent Hall", "No torches needed. The walls themselves provide light.",
                       "The light pulses in a rhythm that matches nothing natural.", ['ice crystal', 'frozen artifact']),
            RoomTemplate("The Kraken's Nursery", "Smaller versions of something much larger move in the shadows.",
                       "They're young. They will not stay young.", ['magic scroll', 'power ring']),
            RoomTemplate("The Deep Current", "A current of water strong enough to knock you sideways.",
                       "It flows from somewhere you can't see to somewhere worse.", ['weapon cache', 'titan gauntlet']),
            RoomTemplate("The Pressure Vent", "Vents that release jets of superheated water.",
                       "The organisms that live near them have adapted. Uncomfortably.", ['elixir of life', 'soul crystal']),
            RoomTemplate("The Abyss Lookout", "A platform overlooking absolute darkness below.",
                       "Something looks back up. It is very large.", ['ice crystal', 'weapon cache']),
            RoomTemplate("The Coral Cathedral", "Coral that grew in the shape of a cathedral. Exactly.",
                       "It was not planted. It chose this shape.", ['weapon cache', 'arcane pendant']),
            RoomTemplate("The Deep Shrine", "A shrine to the thing at the bottom of the deepest trench.",
                       "Still receiving offerings. The offerings are people.", ['titan gauntlet', 'wisdom gem']),
        ]},
        'the_abyss':      {'floors': (7, 8), 'templates': [
            RoomTemplate("The Abyssal Gate", "A gate into water so deep it has its own ecosystem.",
                       "The ecosystem has opinions about visitors.", ['demon seal', 'weapon cache']),
            RoomTemplate("The Leviathan's Den", "A chamber sized for something much larger than you.",
                       "The scale is wrong. Everything is wrong.", ['shadow cloak', 'soul crystal']),
            RoomTemplate("The Dark Current Chamber", "Water that moves against itself in impossible directions.",
                       "Navigation is theoretical here.", ['weapon cache', 'ultimate health potion']),
            RoomTemplate("The Drowned Ritual Space", "Geometric shapes on the floor, glowing in patterns.",
                       "The ritual is ongoing. You have interrupted it.", ['demon seal', 'arcane pendant']),
            RoomTemplate("The Void Kelp", "Kelp that grows upward and also inward.",
                       "Touching it is strongly inadvisable.", ['demon seal', 'soul crystal']),
            RoomTemplate("The Pressure Core", "The deepest room in the Drowned Kingdom. The walls weep water.",
                       "You feel the weight of miles of ocean above you.", ['weapon cache', 'elixir of life']),
            RoomTemplate("The Sunken Sanctum", "A sanctum that sank very deliberately.",
                       "It wanted to be here. It still does.", ['void essence', 'wisdom gem']),
            RoomTemplate("The Tide's End", "Where the tide comes to finish its business.",
                       "The business is you.", ['ultimate health potion', 'soul crystal']),
        ]},
        'the_deep_throne':{'floors': (9, 10), 'templates': [
            RoomTemplate("The Eternal Trench", "The oldest geological feature in any ocean.",
                       "The things at the bottom have been there since before geology.", ['primordial rune', 'titan gauntlet']),
            RoomTemplate("The Crushing Dark", "Light does not function correctly here.",
                       "Neither does most of what you consider reality.", ['weapon cache', 'wisdom gem']),
            RoomTemplate("The Last Corridor", "The final approach. The water is very still.",
                       "Still water means the current has stopped. The current stopped when it arrived.", ['soul crystal', 'legendary artifact']),
            RoomTemplate("The Void Trench", "A trench that goes deeper than the ocean floor.",
                       "It goes somewhere else. You will not enjoy somewhere else.", ['void essence', 'ultimate health potion']),
            RoomTemplate("The Drowned Archive", "Records of every creature that ever sank.",
                       "Your name is already here.", ['titan gauntlet', 'weapon cache']),
            RoomTemplate("The Sunken Core", "The heart of the Drowned Kingdom. Still beating.",
                       "The heart is not metaphorical.", ['weapon cache', 'wisdom gem']),
            RoomTemplate("The Throne Approach", "The antechamber to the Drowned Eternal's seat.",
                       "The attendants are here. They have been waiting.", ['soul crystal', 'experience gem']),
            RoomTemplate("The Eternal Depths", "Beyond language. Beyond measure. Still dangerous.",
                       "The danger is the only constant left.", ['weapon cache', 'weapon cache']),
        ]},
    }

    NG_PLUS_ASHEN_THEME = {
        'ash_fields':     {'floors': (1, 2), 'templates': [
            RoomTemplate("The Scorched Gate", "The entrance burned so completely the stone is glass.",
                       "It still radiates heat. It will never stop.", ['weapon cache', 'health potion']),
            RoomTemplate("The Cinder Barracks", "Soldiers' quarters melted into one another.",
                       "The soldiers remain. In a technical sense.", ['armor piece', 'energy drink']),
            RoomTemplate("The Ash Field", "A vast field of ash with no visible source.",
                       "The ash moves against the (nonexistent) wind.", ['health potion', 'golden coin']),
            RoomTemplate("The Ember Garden", "A garden where the flowers are made of compressed ember.",
                       "They're beautiful. They're also on fire.", ['weapon cache', 'experience gem']),
            RoomTemplate("The Hot Stone Passage", "Passage where the floor radiates heat through your boots.",
                       "The heat has a direction. It's pointing at something.", ['rusty key', 'power ring']),
            RoomTemplate("The Burned Archive", "An archive where every record has burned except the ash.",
                       "The ash forms legible words if you look long enough.", ['rusty key', 'armor piece']),
            RoomTemplate("The Char Corridor", "A corridor made of charred wood that should have collapsed.",
                       "It hasn't. Something is holding it up.", ['weapon cache', 'vitality tonic']),
            RoomTemplate("The Soot Hall", "Soot two inches thick on every surface.",
                       "Footprints in the soot. They lead deeper in.", ['experience gem', 'health potion']),
        ]},
        'the_burned_city':{'floors': (3, 4), 'templates': [
            RoomTemplate("The Glass Throne Room", "The heat fused everything to glass. The throne is beautiful.",
                       "The throne is occupied. What sits in it is not glass.", ['soul crystal', 'weapon cache']),
            RoomTemplate("The Cinder Library", "Books burned to the shapes of books. Holding ash.",
                       "One book still has pages. The words are warnings.", ['magic scroll', 'arcane pendant']),
            RoomTemplate("The Ember Crypt", "Crypts where the dead burned before burial was needed.",
                       "The burning continues. The dead continue.", ['health potion', 'wisdom gem']),
            RoomTemplate("The Slag Gallery", "Portraits melted to slag, faces still visible in the metal.",
                       "The expressions are wrong for paintings. Too alive.", ['weapon cache', 'torch']),
            RoomTemplate("The Pyro Hall", "Cultist meeting space, still set up for a meeting.",
                       "The candles are lit. Someone set them recently.", ['shadow cloak', 'experience gem']),
            RoomTemplate("The Ash Cathedral", "Dedicated to the principle of fire. Very serious about it.",
                       "The congregation is still here. Ash takes interesting forms.", ['weapon cache', 'arcane pendant']),
            RoomTemplate("The Last Market", "A market that burned mid-transaction.",
                       "The merchants are still waiting on payment.", ['soul crystal', 'ultimate health potion']),
            RoomTemplate("The Cinder Armory", "Weapons that survived because they were already metal.",
                       "They've been reforged by heat into something better or worse.", ['wisdom gem', 'weapon cache']),
        ]},
        'magma_sea':      {'floors': (5, 6), 'templates': [
            RoomTemplate("The Lava Bridge", "A stone bridge over a sea of lava that never cooled.",
                       "The bridge is holding. For now. The lava is patient.", ['weapon cache', 'elixir of life']),
            RoomTemplate("The Magma Chamber", "The heart of the volcano that decided to become a dungeon.",
                       "The magma has opinions and occasionally expresses them.", ['ice crystal', 'frozen artifact']),
            RoomTemplate("The Cooling Field", "Lava that cooled too fast and created a field of black glass.",
                       "The glass shows reflections of things not present.", ['magic scroll', 'power ring']),
            RoomTemplate("The Fire Nexus", "Every flame in the Ashen Wastes connects here.",
                       "You can hear them all burning simultaneously.", ['weapon cache', 'titan gauntlet']),
            RoomTemplate("The Ash Sea", "A sea of fine ash that moves like water.",
                       "Things swim in it. You can see their fins.", ['elixir of life', 'soul crystal']),
            RoomTemplate("The Ember Field", "Embers the size of houses, drifting upward slowly.",
                       "The source of the embers is below you.", ['ice crystal', 'weapon cache']),
            RoomTemplate("The Cinder Forge", "A forge that runs on something other than bellows.",
                       "The something is angry and very hot.", ['weapon cache', 'arcane pendant']),
            RoomTemplate("The Heat Cathedral", "The real place of worship in the Ashen Wastes.",
                       "The idol is just fire. But it responds to prayer.", ['titan gauntlet', 'wisdom gem']),
        ]},
        'the_deep_burn':  {'floors': (7, 8), 'templates': [
            RoomTemplate("The Incineration Chamber", "Designed to burn things. Currently burning.",
                       "The things it's burning look back at you.", ['demon seal', 'weapon cache']),
            RoomTemplate("The Eternal Flame Hall", "Flames that have not been extinguished for millennia.",
                       "They recognise you. This is bad.", ['shadow cloak', 'soul crystal']),
            RoomTemplate("The Pyre Core", "The original pyre from which everything spread.",
                       "Still burning. Will always burn.", ['weapon cache', 'ultimate health potion']),
            RoomTemplate("The Char Sanctum", "A sanctum of ash and char that has become something holy.",
                       "The holiness radiates heat.", ['demon seal', 'arcane pendant']),
            RoomTemplate("The Cinder Abyss", "A drop into burning darkness.",
                       "The burning darkness drops further than physics allows.", ['demon seal', 'soul crystal']),
            RoomTemplate("The Last Light", "The only light source in this section that isn't fire.",
                       "It has been here since before the fire. It remembers the before.", ['weapon cache', 'elixir of life']),
            RoomTemplate("The Heat Void", "Heat so intense it has eaten the space around it.",
                       "Moving through this room takes more steps than it should.", ['void essence', 'wisdom gem']),
            RoomTemplate("The Sacrificial Kiln", "Built for something larger and older than sacrifice.",
                       "Still in use. Still effective.", ['ultimate health potion', 'soul crystal']),
        ]},
        'the_first_fire': {'floors': (9, 10), 'templates': [
            RoomTemplate("The Primordial Hearth", "The first fire ever lit, still going.",
                       "Everything that ever burned traces back to here.", ['primordial rune', 'titan gauntlet']),
            RoomTemplate("The Ash Observatory", "An observatory looking out onto nothing but ash.",
                       "The ash forms constellations. They are not friendly ones.", ['weapon cache', 'wisdom gem']),
            RoomTemplate("The Final Ember", "One ember. The last. The one that would end everything if it went out.",
                       "You are not allowed to extinguish it.", ['soul crystal', 'legendary artifact']),
            RoomTemplate("The Pyroclast Hall", "A hall made from the hardened ejecta of the origin eruption.",
                       "The walls show the history of fire in cross-section.", ['void essence', 'ultimate health potion']),
            RoomTemplate("The Origin Vent", "The vent from which the first fire emerged.",
                       "Still venting. Still original.", ['titan gauntlet', 'weapon cache']),
            RoomTemplate("The Cinder Core", "The core of the Ashen Wastes. Everything else is aftermath.",
                       "The aftermath is impressive.", ['weapon cache', 'wisdom gem']),
            RoomTemplate("The Burning Throne Approach", "The approach to the burning throne. The heat is personal here.",
                       "The heat specifically targets you. This is intentional.", ['soul crystal', 'experience gem']),
            RoomTemplate("The Last Fire", "This is where fire ends. Or starts. Depends on direction.",
                       "You are going the wrong direction.", ['weapon cache', 'weapon cache']),
        ]},
    }

    NG_PLUS_MECHANICAL_THEME = {
        'the_entry':      {'floors': (1, 2), 'templates': [
            RoomTemplate("The Intake Chamber", "Where new components are received.",
                       "You have been received. Processing.", ['weapon cache', 'health potion']),
            RoomTemplate("The Assembly Line", "Still running. Still assembling. You don't want to know what.",
                       "The arms move in perfect synchrony.", ['armor piece', 'energy drink']),
            RoomTemplate("The Blueprint Room", "Designs for everything in this dungeon, including the traps.",
                       "Including, apparently, you.", ['health potion', 'golden coin']),
            RoomTemplate("The Gear Hall", "A hall of interlocking gears from floor to ceiling.",
                       "The gears serve no mechanical purpose. They know this.", ['weapon cache', 'experience gem']),
            RoomTemplate("The Brass Corridor", "Every surface is polished brass, every joint perfect.",
                       "It's watching you through the reflections.", ['rusty key', 'power ring']),
            RoomTemplate("The Engineer's Office", "Still occupied. The engineer upgraded themselves years ago.",
                       "The chair has been modified. So has everything else.", ['rusty key', 'armor piece']),
            RoomTemplate("The Calibration Chamber", "Where precision is measured. Where imprecision is corrected.",
                       "You are imprecise. You have been noted.", ['weapon cache', 'vitality tonic']),
            RoomTemplate("The Testing Ground", "Where the mechanisms are tested before deployment.",
                       "You are being tested. The mechanism is everything here.", ['experience gem', 'health potion']),
        ]},
        'the_gear_works': {'floors': (3, 4), 'templates': [
            RoomTemplate("The Master Gear Room", "One central gear, house-sized, everything else orbiting it.",
                       "It turns too slowly to see. You can feel it.", ['soul crystal', 'weapon cache']),
            RoomTemplate("The Clock Archive", "The history of time, measured in gears.",
                       "One clock runs backwards. It's more accurate than the others.", ['magic scroll', 'arcane pendant']),
            RoomTemplate("The Iron Crypt", "Where obsolete models are stored. Or destroyed. Depends on performance.",
                       "Some of the models are watching.", ['health potion', 'wisdom gem']),
            RoomTemplate("The Automation Hall", "Machines doing things that don't need doing.",
                       "They know. They continue anyway.", ['weapon cache', 'torch']),
            RoomTemplate("The Piston Chamber", "Pistons the size of columns, driving something below.",
                       "What's below doesn't need driving. It goes willingly.", ['shadow cloak', 'experience gem']),
            RoomTemplate("The Gear Cathedral", "Worship of motion as a principle.",
                       "The congregation is in perpetual motion. Has been for decades.", ['weapon cache', 'arcane pendant']),
            RoomTemplate("The Clockwork Armory", "Weapons designed and built by machine.",
                       "They're better than hand-made. The machines took this personally.", ['soul crystal', 'ultimate health potion']),
            RoomTemplate("The Maintenance Bay", "Where things are fixed. Not always improved.",
                       "The mechanics here have been modified past recognisability.", ['wisdom gem', 'weapon cache']),
        ]},
        'the_steam_core': {'floors': (5, 6), 'templates': [
            RoomTemplate("The Boiler Room", "Heat and pressure at engineering limits.",
                       "The limits were set conservatively. The machines disagree.", ['weapon cache', 'elixir of life']),
            RoomTemplate("The Steam Conduit", "Pipes large enough to walk through, full of superheated steam.",
                       "The steam carries something other than heat.", ['ice crystal', 'frozen artifact']),
            RoomTemplate("The Turbine Hall", "Turbines running at speeds that blur the eye.",
                       "What they're generating isn't listed in the specs.", ['magic scroll', 'power ring']),
            RoomTemplate("The Pressure Vault", "A vault sealed by pressure. Opens when the pressure is wrong.",
                       "The pressure is usually wrong.", ['weapon cache', 'titan gauntlet']),
            RoomTemplate("The Engine Room", "The main engine. Still running. Was never meant to stop.",
                       "It hasn't. It won't.", ['elixir of life', 'soul crystal']),
            RoomTemplate("The Cooling System", "The system that prevents total meltdown.",
                       "It's losing the argument.", ['ice crystal', 'weapon cache']),
            RoomTemplate("The Arc Generator", "Generates arcs of something that isn't electricity.",
                       "The difference matters at close range.", ['weapon cache', 'arcane pendant']),
            RoomTemplate("The Core Access", "Access to the core systems. Restricted.",
                       "The restriction has been noted. You are continuing anyway.", ['titan gauntlet', 'wisdom gem']),
        ]},
        'the_deep_machine':{'floors': (7, 8), 'templates': [
            RoomTemplate("The Override Chamber", "Where control is taken or given.",
                       "The control was given voluntarily. Once.", ['demon seal', 'weapon cache']),
            RoomTemplate("The Null Protocol Room", "Where things are unmade rather than made.",
                       "Unmade things leave residue.", ['shadow cloak', 'soul crystal']),
            RoomTemplate("The Deep Mechanism", "The mechanism under the mechanism under the mechanism.",
                       "It goes deeper. You are at the surface of deep.", ['weapon cache', 'ultimate health potion']),
            RoomTemplate("The Automaton Sanctum", "Where automatons go that have achieved something.",
                       "What they've achieved is not listed in the manual.", ['demon seal', 'arcane pendant']),
            RoomTemplate("The Clock Void", "A clock stopped at the moment everything changed.",
                       "Everything changed. The clock recorded it. The clock regrets recording it.", ['demon seal', 'soul crystal']),
            RoomTemplate("The Final Circuit", "The last circuit in the system. The rest is upstream.",
                       "Upstream is not a direction you want to go.", ['weapon cache', 'elixir of life']),
            RoomTemplate("The Broken Protocol", "Where the rules of the machine broke down.",
                       "The break-down was scheduled. Intentional.", ['void essence', 'wisdom gem']),
            RoomTemplate("The Core Maintenance", "Maintained by things that maintain themselves.",
                       "Self-maintenance has gone in interesting directions.", ['ultimate health potion', 'soul crystal']),
        ]},
        'the_prime':      {'floors': (9, 10), 'templates': [
            RoomTemplate("The Prime Assembly", "Where the first version was built.",
                       "The first version is still here, watching.", ['primordial rune', 'titan gauntlet']),
            RoomTemplate("The Blueprint Vault", "Original designs for everything.",
                       "The designs include contingencies for everything, including this.", ['weapon cache', 'wisdom gem']),
            RoomTemplate("The Eternal Engine Chamber", "The engine that runs everything.",
                       "It was built to run forever. It will.", ['soul crystal', 'legendary artifact']),
            RoomTemplate("The Gear Void", "Gears meshing in arrangements that defy geometry.",
                       "The geometry gave up. The gears kept going.", ['void essence', 'ultimate health potion']),
            RoomTemplate("The Origin Component", "The first gear. Still turning. Everything else is derived.",
                       "The derivation has been extensive.", ['titan gauntlet', 'weapon cache']),
            RoomTemplate("The Final Mechanism", "The mechanism at the end of all mechanisms.",
                       "It is still mechanical. Everything else stopped being mechanical ages ago.", ['weapon cache', 'wisdom gem']),
            RoomTemplate("The Constructor's Hall", "The hall of the thing that built all of this.",
                       "It is still here. It is still building.", ['soul crystal', 'experience gem']),
            RoomTemplate("The Prime Vault", "The vault of original components and original intentions.",
                       "The intentions were not good.", ['weapon cache', 'weapon cache']),
        ]},
    }

    NG_PLUS_PLAGUE_THEME = {
        'the_infected_nave':{'floors': (1, 2), 'templates': [
            RoomTemplate("The Welcoming Chapel", "Where new members of the order are greeted.",
                       "The greeting involves a handshake. Don't shake hands.", ['weapon cache', 'health potion']),
            RoomTemplate("The Infected Barracks", "Monks' quarters. The monks are still in them.",
                       "They are praying. Loudly. To something that answers.", ['armor piece', 'energy drink']),
            RoomTemplate("The Prayer Hall", "Rows of kneeling figures. None are human.",
                       "The prayer is audible. The content is worse.", ['health potion', 'golden coin']),
            RoomTemplate("The Reliquary", "Sacred objects behind glass. Most of them still contagious.",
                       "The glass has cracks.", ['weapon cache', 'experience gem']),
            RoomTemplate("The Confession Booth", "Confessions are heard here. Penance assigned.",
                       "The penance involves contact with the faithful.", ['rusty key', 'power ring']),
            RoomTemplate("The Abbot's Office", "A holy office for an unholy purpose.",
                       "The abbot is still here. Still working.", ['rusty key', 'armor piece']),
            RoomTemplate("The Blessed Corridor", "Blessed by something. The blessing is visible.",
                       "You would rather not see it.", ['weapon cache', 'vitality tonic']),
            RoomTemplate("The Font", "Holy water, technically. The holiness is debatable.",
                       "The water moves on its own.", ['experience gem', 'health potion']),
        ]},
        'the_dark_vestry': {'floors': (3, 4), 'templates': [
            RoomTemplate("The Vestry", "Ceremonial robes hanging in rows. Some still occupied.",
                       "The occupants don't need the robes but wear them out of tradition.", ['soul crystal', 'weapon cache']),
            RoomTemplate("The Forbidden Library", "Books that the church considers essential.",
                       "The church's standards are alarming.", ['magic scroll', 'arcane pendant']),
            RoomTemplate("The Bone Altar", "An altar made of the remains of the devout.",
                       "The devout contributed willingly. Mostly.", ['health potion', 'wisdom gem']),
            RoomTemplate("The Infected Study", "A scholar's room. The scholar is still studying.",
                       "The subject of study is communicable.", ['weapon cache', 'torch']),
            RoomTemplate("The Dark Scriptorium", "Texts written in something other than ink.",
                       "The authorship is collective and ongoing.", ['shadow cloak', 'experience gem']),
            RoomTemplate("The Consecration Chamber", "Where things are made holy.",
                       "Holiness here is not what it says in the books.", ['weapon cache', 'arcane pendant']),
            RoomTemplate("The Sacred Infirmary", "Where the faithful are healed. The healing is visible.",
                       "You would define it differently.", ['soul crystal', 'ultimate health potion']),
            RoomTemplate("The Bishop's Chambers", "Personal quarters of the Bishop. Still personal.",
                       "The Bishop considers you personal business.", ['wisdom gem', 'weapon cache']),
        ]},
        'the_sanctum':    {'floors': (5, 6), 'templates': [
            RoomTemplate("The Inner Sanctum", "The heart of the cathedral. The faith is concentrated here.",
                       "The concentration is visible. Don't breathe it in.", ['weapon cache', 'elixir of life']),
            RoomTemplate("The Blight Garden", "A garden of medicinal herbs. The medicine has changed.",
                       "The change is not medical.", ['ice crystal', 'frozen artifact']),
            RoomTemplate("The Inquisition Hall", "Where judgement is rendered and executed simultaneously.",
                       "You have been judged. The execution is in progress.", ['magic scroll', 'power ring']),
            RoomTemplate("The Plague Saint's Shrine", "A shrine to a saint who died of their blessing.",
                       "The shrine is still receiving offerings. The saint is still accepting them.", ['weapon cache', 'titan gauntlet']),
            RoomTemplate("The Ritual Space", "Geometric patterns on the floor, worn deep by repetition.",
                       "The ritual has been performed enough times to affect reality.", ['elixir of life', 'soul crystal']),
            RoomTemplate("The Blessed Tomb", "A tomb that opens from the inside.",
                       "It has opened. Whatever was inside is no longer inside.", ['ice crystal', 'weapon cache']),
            RoomTemplate("The Cardinal's Hall", "A hall of the church's highest officials.",
                       "They are all still here. They have been improved.", ['weapon cache', 'arcane pendant']),
            RoomTemplate("The Faith Core", "Where faith is created and distributed.",
                       "The distribution is non-optional.", ['titan gauntlet', 'wisdom gem']),
        ]},
        'the_deep_faith':  {'floors': (7, 8), 'templates': [
            RoomTemplate("The Eternal Service", "A service that has been running for centuries.",
                       "The congregation has changed. The service has not.", ['demon seal', 'weapon cache']),
            RoomTemplate("The Communion Hall", "Where the faithful share in something.",
                       "The something is not bread and wine.", ['shadow cloak', 'soul crystal']),
            RoomTemplate("The Plague Core", "The source of the original plague.",
                       "It is still here. It is grateful for the company.", ['weapon cache', 'ultimate health potion']),
            RoomTemplate("The Null Prayer Room", "A room dedicated to something with no name.",
                       "The prayer continues. The name remains absent.", ['demon seal', 'arcane pendant']),
            RoomTemplate("The Martyrs' Hall", "Those who died for the faith are commemorated here.",
                       "Commemorated, and still present. Still faithful.", ['demon seal', 'soul crystal']),
            RoomTemplate("The Sacred Void", "A void at the centre of the cathedral.",
                       "The void prays. The prayers are audible.", ['weapon cache', 'elixir of life']),
            RoomTemplate("The Consecrated Dark", "Darkness that has been made holy.",
                       "The holiness is the problem.", ['void essence', 'wisdom gem']),
            RoomTemplate("The Deepest Confession", "Where the worst confessions are heard.",
                       "You have walked into one.", ['ultimate health potion', 'soul crystal']),
        ]},
        'the_eternal_altar':{'floors': (9, 10), 'templates': [
            RoomTemplate("The Primordial Chapel", "The first chapel of the order. Still in service.",
                       "The original faith is stronger here. The original faith is the problem.", ['primordial rune', 'titan gauntlet']),
            RoomTemplate("The Saint's Observatory", "Where the saints watch over everything.",
                       "The watching is very thorough.", ['weapon cache', 'wisdom gem']),
            RoomTemplate("The Final Sermon", "A sermon that has been in progress for a very long time.",
                       "You have arrived for the final argument.", ['soul crystal', 'legendary artifact']),
            RoomTemplate("The Plague Void", "The void at the end of all plague.",
                       "Or the beginning. It depends on which way you're facing.", ['void essence', 'ultimate health potion']),
            RoomTemplate("The Origin Infection", "The first case. Still active.",
                       "Patient zero is still here, technically.", ['titan gauntlet', 'weapon cache']),
            RoomTemplate("The Cathedral Core", "The structure that holds the cathedral together.",
                       "The structure is not architectural.", ['weapon cache', 'wisdom gem']),
            RoomTemplate("The Altar Approach", "The approach to the eternal altar.",
                       "The altar is expecting you.", ['soul crystal', 'experience gem']),
            RoomTemplate("The End of Faith", "Where faith terminates.",
                       "Or begins again. The cycle has no preference.", ['weapon cache', 'weapon cache']),
        ]},
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
                   ['primordial rune', 'legendary artifact'], 1, 'rune_monument')
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

    # Hard per-floor weapon damage caps — keeps boss fights from being trivialised
    # by an INSANE-tier roll. Sized for a 4-8 turn fight at each floor.
    WEAPON_DAMAGE_CAPS: Dict[int, int] = {
        1: 50,  2: 62,  3: 76,  4: 90,
        5: 106, 6: 124, 7: 144, 8: 166,
        9: 190, 10: 220,
    }

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
        (1.08, 10), (1.12, 10), (1.15, 10),                           # GREAT  (30%) — reduced from 1.20-1.30
        (1.20,  5), (1.30,  5),                                        # INSANE (10%) — reduced from 1.60-1.70
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
    def generate_ng_plus(cls, floor: int, ng_cycle: int = 1,
                          world_key: str = None, weapon_scale: float = 1.0) -> Dict[str, Any]:
        """Generate NG+ boss configuration — independent stat blocks.

        world_key selects the world's boss_data; weapon_scale inflates HP when
        the player is carrying legacy overpowered weapons.
        """
        if world_key:
            world = GameConstants.NG_PLUS_WORLDS.get(world_key,
                    GameConstants.NG_PLUS_WORLDS['fractured_labyrinth'])
            data = world['boss_data'][floor]
        else:
            data = GameConstants.NG_PLUS_BOSS_DATA[floor]
        cycle_mult = 1 + (ng_cycle - 1) * 0.20
        return {
            'floor': floor,
            'name': data['name'],
            'base_health': int(data['base_health'] * cycle_mult * weapon_scale),
            'health_scaling': int(data['health_scaling'] * cycle_mult),
            'damage': int(data['damage'] * cycle_mult),
            'exp_reward': int(data['exp_reward'] * cycle_mult),
            'special_attack': data['special'],
            'special_bonus': int(data['special_bonus'] * cycle_mult),
            'stat_bonus': data['stat_bonus'],
            'min_level': data['min_level'],
        }

    @classmethod
    def get_ng_plus_boss_room_template(cls, floor: int) -> 'RoomTemplate':
        """Get NG+ boss room template (world 1 default)"""
        room_data = RoomTemplateConfig.NG_PLUS_BOSS_ROOMS[floor]
        return RoomTemplate(
            room_data[0], room_data[1], room_data[2],
            ["champion's prize", 'ultimate health potion'],
            enemy_count=0, special_type='boss'
        )

    @classmethod
    def get_ng_plus_boss_room_template_for_world(cls, floor: int, world_key: str) -> 'RoomTemplate':
        """Get NG+ boss room template for a specific world"""
        world_data = GameConstants.NG_PLUS_WORLDS.get(world_key,
                     GameConstants.NG_PLUS_WORLDS['fractured_labyrinth'])
        room_data  = world_data['boss_rooms'][floor]
        return RoomTemplate(
            room_data[0], room_data[1], room_data[2],
            ["champion's prize", 'ultimate health potion'],
            enemy_count=0, special_type='boss'
        )
    
    @classmethod
    def generate_boss_weapon(cls, floor: int, player: 'Player') -> Dict:
        """Pick a boss weapon from the tier-weighted pool and scale its damage.

        Damage is now level-based only — no longer compounding off the player's
        current weapon.  Hard caps apply to every floor so fights can't be
        trivialized by an INSANE-tier roll.

        Pool breakdown per boss per class (10 total):
          Indices 0-4  GOOD   → weight 12 each = 60%  → tier mult 1.00-1.05x
          Indices 5-7  GREAT  → weight 10 each = 30%  → tier mult 1.08-1.15x
          Indices 8-9  INSANE → weight  5 each = 10%  → tier mult 1.20-1.30x
        """
        pool = cls.BOSS_WEAPON_POOLS[floor][player.character_class]
        weights = [cls.WEAPON_TIER_MAP[i][1] for i in range(len(pool))]
        chosen_idx = random.choices(range(len(pool)), weights=weights, k=1)[0]
        weapon_name = pool[chosen_idx]
        tier_mult, _ = cls.WEAPON_TIER_MAP[chosen_idx]

        if chosen_idx < 5:
            tier_label, rarity = 'GOOD', 'legendary'
        elif chosen_idx < 8:
            tier_label, rarity = 'GREAT', 'legendary'
        else:
            tier_label, rarity = 'INSANE', 'mythic'

        weapon_type = GameConstants.CLASSES[player.character_class]['weapon_types'][0]

        # Level-based scaling only — no more compounding off the player's weapon.
        # base_weapon_damage already includes the legendary rarity multiplier so
        # that the stored number looks meaningful on the weapon card.
        # calculate_player_damage will NOT re-apply the multiplier for boss fights.
        rarity_data = GameConstants.WEAPON_RARITIES['legendary']
        base_damage  = random.randint(rarity_data['base_min'], rarity_data['base_max'])
        base_damage += player.level * (1 + floor // 3)          # gentle level+floor scale
        final_damage = int(base_damage * rarity_data['multiplier'])

        # Hard per-floor caps — applied BEFORE tier multiplier.
        # Sized so that (stored + avg_STR) gives a 4-8 turn boss fight.
        FLOOR_CAPS = {
            1: 50,  2: 62,  3: 76,  4: 90,
            5: 106, 6: 124, 7: 144, 8: 166,
            9: 190, 10: 220,
        }
        final_damage = min(final_damage, FLOOR_CAPS.get(floor, 220))

        # Tier multiplier (reduced from old 1.60-1.70 to prevent one-shots)
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
            # Conditional items (v7.5.2)
            if effect.get('type') == 'conditional':
                mode = effect.get('mode')
                if mode == 'pct_missing':
                    missing = player.max_health - player.health
                    healed = max(1, int(missing * effect['pct']))
                    player.health = min(player.max_health, player.health + healed)
                    print(f"+ Elixir of Desperation: +{healed} HP restored!")
                elif mode == 'absorb':
                    player.void_absorb_active = True
                    print(f"+ Void Tonic active: next hit converts to {effect['mana_on_hit']} MP!")
                elif mode == 'dmg_taken':
                    taken = getattr(player, 'fight_damage_taken', 0)
                    healed = max(effect.get('min', 20), int(taken * effect['pct']))
                    healed = min(healed, player.max_health - player.health)
                    if healed <= 0:
                        print("Berserker's Draught: No damage taken yet — save it for a fight!")
                        return False
                    player.health += healed
                    print(f"+ Berserker's Draught: +{healed} HP from battle damage!")
                elif mode == 'cure':
                    cured = list(player.status_effects.keys())
                    player.status_effects.clear()
                    healed = min(effect.get('heal', 0), player.max_health - player.health)
                    player.health += healed
                    if cured:
                        print(f"+ Antidote cures: {', '.join(cured)}! +{healed} HP")
                    else:
                        print(f"+ Antidote: No effects to cure. +{healed} HP")
                elif mode == 'boost':
                    player.combat_boost_turns = effect['turns']
                    player.combat_boost_mult  = effect['mult']
                    print(f"+ Battle Tincture: next {effect['turns']} attacks deal "
                          f"{int((effect['mult']-1)*100)}% more damage!")
                return True

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
            player.stats[effect['stat']] = player.stats.get(effect['stat'], 0) + effect['bonus']
            player.wearables.append({'item': item_name, 'stat': effect['stat'], 'bonus': effect['bonus']})
            label = f"+{effect['bonus']} {effect['stat']}"
            if effect.get('cursed'):
                # Apply penalties
                if effect.get('hp_penalty'):
                    player.max_health += effect['hp_penalty']
                    player.health = min(player.health, player.max_health)
                    label += f" / {effect['hp_penalty']} max HP"
                if effect.get('dmg_taken_mult'):
                    pct = int((effect['dmg_taken_mult'] - 1) * 100)
                    label += f" / +{pct}% dmg taken"
                print(f"*** Cursed item equipped: {item_name}! {label}")
                print(f"    {effect.get('desc', '')}")
            else:
                print(f"*** Equipped {item_name}! {label}")

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
        skip_rarity_mult: bool = False,
    ) -> int:
        """Calculate player damage including traits, crits, and enemy weaknesses.

        skip_rarity_mult=True is passed by boss fights only. Weapon damage stored
        by generate_boss_weapon already has the rarity multiplier baked in, so
        re-applying it in combat causes the 3x-boss-HP scaling bug.
        Regular enemy combat keeps skip_rarity_mult=False to preserve balance.
        """
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
        # Boss fights skip remultiplication — rarity already baked into stored damage
        if skip_rarity_mult:
            damage = float(base + strength_bonus)
        else:
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
            crit_mult = 2.5 if player.character_class == 'void_walker' else 1.75
            damage *= crit_mult
            if player.character_class == 'void_walker':
                trait_notes.append("VOID RESONANCE CRIT! (2.5x)")
            else:
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

        # Print any trait proc messages
        for note in trait_notes:
            print(f"  ✦ {note}")

        # Battle tincture boost (v7.5.2)
        if getattr(player, 'combat_boost_turns', 0) > 0:
            damage = int(damage * player.combat_boost_mult)
            player.combat_boost_turns -= 1
            if player.combat_boost_turns == 0:
                player.combat_boost_mult = 1.0
                print("  ✦ Battle Tincture wears off.")
            else:
                print(f"  ✦ Battle Tincture: {player.combat_boost_turns} boosted attacks left.")

        # Weaken status debuff
        if 'weaken' in getattr(player, 'status_effects', {}):
            damage = int(damage * GameConstants.STATUS_EFFECTS['weaken']['dmg_mult'])
            print("  ✦ Weakened: reduced damage!")

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

        # NG+ cycle stacking: +15% per additional cycle beyond the first
        # (first cycle uses independent stat blocks; subsequent cycles stack)
        ng_plus = getattr(player, 'ng_plus', 0)
        if ng_plus > 1:
            final = int(final * (1 + (ng_plus - 1) * 0.15))

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
        self.total_gold_earned = 0
        self.secret_room_unlocked = False
        self.unique_items_spawned: Set[str] = set()  # Track unique items spawned
        self.item_hints_shown:    Set[str] = set()  # Items whose full hint has been shown
        self.status_effects:      Dict[str, int] = {}  # name → turns remaining
        self.fight_damage_taken:  int   = 0    # total damage taken this fight (berserker's draught)
        self.combat_boost_turns:  int   = 0    # turns of battle tincture active
        self.combat_boost_mult:   float = 1.0  # active damage boost multiplier
        self.void_absorb_active:  bool  = False  # void tonic: absorb next hit → MP
    
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
    
    def can_fuse_class(self) -> bool:
        """Fusion available at tier 5 in NG+."""
        return (self.class_tier >= 5
                and getattr(self, 'ng_plus', 0) > 0
                and not getattr(self, 'fusion_parents', None))

    def fuse_class(self, target_class: str) -> bool:
        """Fuse current class with target_class into a fusion speciality."""
        if not self.can_fuse_class():
            return False
        fusion = GameConstants.get_fusion(self.character_class, target_class)
        if not fusion:
            return False

        self.fusion_parents = (self.character_class, target_class)

        # Average parent base stats then add fusion bonus
        parent1 = GameConstants.CLASSES[self.character_class]['base_stats']
        parent2 = GameConstants.CLASSES[target_class]['base_stats']
        bonus   = fusion['stat_bonus']
        levels  = max(0, self.level - 1)
        g1 = GameConstants.CLASSES[self.character_class]['stat_growth']
        g2 = GameConstants.CLASSES[target_class]['stat_growth']

        for stat in parent1:
            avg_base   = (parent1[stat] + parent2.get(stat, 0)) // 2
            avg_growth = (g1.get(stat, 0) + g2.get(stat, 0)) / 2
            new_val    = avg_base + bonus.get(stat, 0) + int(avg_growth * levels)
            # Never reduce stats the player already has
            self.stats[stat] = max(self.stats.get(stat, 0), new_val)

        # HP boost
        old_max = self.max_health
        self.max_health += fusion['health_per_level'] * levels
        self.health = min(self.health + (self.max_health - old_max), self.max_health)

        self.character_class = fusion['name'].lower().replace(' ', '_')
        self.class_tier = 5  # stays at 5

        print(f"\n{'★'*50}")
        print(f"  CLASS FUSION COMPLETE")
        print(f"  {self.fusion_parents[0].title()} + {self.fusion_parents[1].title()}")
        print(f"  → {fusion['name'].upper()}")
        print(f"  {fusion['description']}")
        print(f"{'★'*50}")
        return True

    def get_class_title(self) -> str:
        """Return the display name for current class and tier."""
        if getattr(self, 'fusion_parents', None):
            fusion = GameConstants.get_fusion(*self.fusion_parents)
            return fusion['name'] if fusion else self.character_class.replace('_', ' ').title()
        tier_names = GameConstants.CLASS_NAMES.get(self.class_tier, {})
        return tier_names.get(self.character_class, self.character_class.replace('_', ' ').title())


    def upgrade_class(self) -> bool:
        """Upgrade class tier"""
        if not self.can_upgrade_class():
            return False
        
        old_tier = self.class_tier
        self.class_tier += 1
        self.rarity_boost += GameConstants.RARITY_BOOST_PER_TIER
        
        config = GameConstants.CLASSES[self.character_class]
        old_tier_bonus = (old_tier - 1) * 5
        growth = config['stat_growth']

        # Calculate what stats would have been from base+tier+growth only,
        # then save any surplus the player earned from wearables/shrines/items.
        external_bonuses = {}
        for stat, base_val in config['base_stats'].items():
            clean_val = base_val + old_tier_bonus + growth.get(stat, 0) * (self.level - 1)
            external_bonuses[stat] = self.stats.get(stat, clean_val) - clean_val

        tier_bonus = (self.class_tier - 1) * 5

        # Rebuild base stats from scratch for the new tier…
        self.stats = {k: v + tier_bonus for k, v in config['base_stats'].items()}
        for stat, bonus in growth.items():
            self.stats[stat] += bonus * (self.level - 1)

        # …then restore the externally-earned bonuses so nothing is lost.
        for stat, bonus in external_bonuses.items():
            if stat in self.stats and bonus > 0:
                self.stats[stat] += bonus
        
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

        if item == "gambler's d20":
            if "gambler's d20" not in self.special_items:
                self.special_items.append("gambler's d20")
                print("+ Gambler's d20 (★ doesn't use inventory space)")
                print("  Auto-rolls before boss fights. Use 'use d20' at any time.")
                return True
            else:
                print("You already have a d20!")
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
                # Only add the inventory label if it isn't already there
                label = f"WEAPON: {self.weapon['name']}"
                if label not in self.inventory:
                    self.inventory.append(label)
            self.inventory_weapons.remove(target)
            # Safely remove the label — may be absent for weapons added
            # before this tracking existed (boss rewards, NG+ pickups)
            label = f"WEAPON: {target['name']}"
            if label in self.inventory:
                self.inventory.remove(label)
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
        fp = getattr(self, 'fusion_parents', None)
        if fp:
            fd = GameConstants.get_fusion(*fp)
            fname = fd['name'] if fd else 'Unknown Fusion'
            print(f"Class Fusion: {fname} [{fp[0].title()} + {fp[1].title()}]")
        if self.can_fuse_class():
            print("  ★ CLASS FUSION AVAILABLE — type 'fuse'")

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
            'special_items': self.special_items, 'unique_items_spawned': list(self.unique_items_spawned),
            'ng_plus': getattr(self, 'ng_plus', 0),
            'ng_world': getattr(self, 'ng_world', 'fractured_labyrinth'),
            'item_hints_shown':   list(getattr(self, 'item_hints_shown', set())),
            'status_effects':     getattr(self, 'status_effects', {}),
            'fusion_parents': list(getattr(self, 'fusion_parents', None) or []),
            'ng_weapon_scale': getattr(self, 'ng_weapon_scale', 1.0),
            'total_gold_earned': getattr(self, 'total_gold_earned', 0)
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

        if not hasattr(player, 'item_hints_shown'):
            player.item_hints_shown = set()
        elif isinstance(player.item_hints_shown, list):
            player.item_hints_shown = set(player.item_hints_shown)
        fp = getattr(player, 'fusion_parents', [])
        player.fusion_parents = tuple(fp) if fp else None
        if not hasattr(player, 'ng_weapon_scale'):
            player.ng_weapon_scale = 1.0
        for _attr, _default in [
            ('status_effects', {}), ('item_hints_shown', set()),
            ('fight_damage_taken', 0), ('combat_boost_turns', 0),
            ('combat_boost_mult', 1.0), ('void_absorb_active', False),
        ]:
            if not hasattr(player, _attr):
                setattr(player, _attr, _default)
        if isinstance(player.item_hints_shown, list):
            player.item_hints_shown = set(player.item_hints_shown)
        if not hasattr(player, 'total_gold_earned'):
            player.total_gold_earned = 0
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

        # ── Fix stat loss from upgrade_class bug ──────────────────
        # Old code rebuilt stats from scratch on tier-up, wiping any
        # wearable/shrine/item bonuses. Recalculate what the stats
        # *should* be from base+tier+growth, then ensure the player
        # has at least that much (never reduce stats they legitimately have).
        tier_bonus = (self.class_tier - 1) * 5
        for stat, base_val in base.items():
            minimum = base_val + tier_bonus + growth.get(stat, 0) * levels
            if self.stats.get(stat, 0) < minimum:
                old_val = self.stats.get(stat, 0)
                self.stats[stat] = minimum
                migrated.append(f"{stat.capitalize()} corrected {old_val} → {minimum}")

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
                if not info:
                    # Check all NG+ world enemy pools
                    for world_data in GameConstants.NG_PLUS_WORLDS.values():
                        info = world_data['enemies'].get(enemy.lower())
                        if info:
                            break
                if info:
                    print(f"  - {enemy}: {info['desc']}")
                else:
                    print(f"  - {enemy}")
        
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
        void_pool = [
            w('Shadow Needle',     16, 'stealth', 'vampiric'),
            w('Void Dagger',       17, 'stealth', 'swift'),
            w('Null Blade',        18, 'stealth', 'executioner'),
            w('Fracture Shiv',     15, 'stealth', 'bleeding'),
            w('Phase Edge',        16, 'stealth', 'precise'),
            w('Entropy Knife',     17, 'stealth', 'venomous'),
            w('Void Rapier',       19, 'stealth', 'bleeding'),
            w('Dark Matter Claw',  15, 'stealth', 'vampiric'),
            w('Null Piercer',      18, 'stealth', 'swift'),
            w('Rift Blade',        17, 'stealth', 'executioner'),
            w('Absence Knife',     16, 'stealth', 'cursed'),
            w('Void Fang',         18, 'stealth', 'savage'),
        ]
        random.shuffle(warrior_pool)
        random.shuffle(mage_pool)
        random.shuffle(rogue_pool)
        random.shuffle(void_pool)
        return {
            'warrior':     warrior_pool[:8],
            'mage':        mage_pool[:8],
            'rogue':       rogue_pool[:8],
            'void_walker': void_pool[:8],
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
        # Use NG+ enemy stats — world-specific if applicable
        ng = getattr(player, 'ng_plus', 0)
        if ng > 0:
            wk           = getattr(player, 'ng_world', 'fractured_labyrinth')
            wdata        = GameConstants.NG_PLUS_WORLDS.get(wk,
                           GameConstants.NG_PLUS_WORLDS['fractured_labyrinth'])
            enemy_raw    = wdata['enemies'].get(enemy_name.lower())
            weapon_scale = max(1.0, getattr(player, 'ng_weapon_scale', 1.0))
            if enemy_raw and weapon_scale > 1.0:
                enemy = dict(enemy_raw)
                enemy['health'] = int(enemy_raw['health'] * weapon_scale)
            else:
                enemy = enemy_raw
        else:
            enemy = GameConstants.ENEMIES.get(enemy_name.lower())
        if not enemy:
            enemy = GameConstants.ENEMIES.get(enemy_name.lower()) or GameConstants.NG_PLUS_ENEMIES.get(enemy_name.lower())
        if not enemy:
            logger.warning(f"Unknown enemy attempted: {enemy_name}")
            print(f"Unknown enemy: {enemy_name}")
            return True

        hp = enemy['health']
        player.fight_damage_taken = 0
        max_hp = hp
        dmg = enemy['damage']

        # Load this enemy's behaviour pattern (v7.5.2)
        behaviour = GameConstants.ENEMY_BEHAVIOURS.get(enemy_name.lower(), {})

        # Show enemy weakness hint if weapon has matching trait
        if player.weapon:
            en_lower = enemy_name.lower()
            weaknesses = GameConstants.ENEMY_WEAKNESSES.get(en_lower, {})
            for trait_key in player.weapon.get('traits', []):
                if trait_key in weaknesses and weaknesses[trait_key] > 1.0:
                    td_name = GameConstants.WEAPON_TRAITS.get(trait_key, {}).get('name', trait_key)
                    print(f"  ◈ {enemy_name} is WEAK to {td_name}!")

        # Show damage reduction warning if enemy has armour and weapon lacks bypass trait
        if behaviour.get('dmg_reduce'):
            needed = [t.strip() for t in behaviour.get('dmg_cond', '').split(',')]
            weapon_traits = player.weapon.get('traits', []) if player.weapon else []
            if not any(t in weapon_traits for t in needed):
                print(f"  ⚠  {enemy_name} resists your weapon! Try traits: {', '.join(needed)}")

        # Show intent before first attack
        if behaviour.get('intent'):
            print(f"  ⚔  {behaviour['intent']}")

        logger.info(f"Combat: {player.name} vs {enemy_name} (HP {hp})")
        print(f"\n*** Combat: {enemy_name}!")
        print(f"{enemy['desc']}")

        # Per-fight DoT state (applied TO enemy)
        dot_stack: list = []   # [{'damage': int, 'turns': int, 'type': str}]

        turn = 0
        first_hit = True
        while hp > 0 and player.health > 0:
            turn += 1

            # ── Enemy behaviour: regen ────────────────────────────
            if behaviour.get('regen') and hp < max_hp and turn > 1:
                regen_cond = behaviour.get('regen_cond', 'always')
                w_traits   = player.weapon.get('traits', []) if player.weapon else []
                blocked    = (regen_cond.startswith('no_trait:') and
                              any(t.strip() in w_traits
                                  for t in regen_cond[9:].split(',')))
                if not blocked:
                    regen_amt = behaviour['regen']
                    hp = min(hp + regen_amt, max_hp)
                    print(f"  ✦ {enemy_name} regenerates {regen_amt} HP! "
                          f"({hp}/{max_hp}) — use a countering trait to prevent this!")

            # ── Enemy behaviour: buff others ──────────────────────
            buff_active = False
            if behaviour.get('buff_others') and len(room.enemies) > 1:
                buff_active = True
                print(f"  ✦ {enemy_name} chants — other enemies in this room grow stronger!")

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
                        fp = getattr(player, 'fusion_parents', None)
                        fd_passive = GameConstants.get_fusion(*fp)['passive'] if fp else ''
                        uses_void_hunger = (player.character_class == 'void_walker'
                                            or fd_passive == 'void_resonance')
                        ls_pct = 0.25 if uses_void_hunger else td['lifesteal_pct']
                        heal = max(1, int(damage * ls_pct))
                        player.health = min(player.max_health, player.health + heal)
                        label = "Void Hunger" if uses_void_hunger else "Vampiric"
                        print(f"  ✦ {label}: +{heal} HP drained!")

            if hp <= 0:
                logger.info(f"Victory: {player.name} defeated {enemy_name} in {turn} turns")
                print(f"*** Defeated {enemy_name}!")
                # Fusion kill passives
                if getattr(player, 'fusion_parents', None):
                    fd = GameConstants.get_fusion(*player.fusion_parents)
                    if fd and fd['passive'] == 'execute_restore':
                        heal = max(1, int(player.max_health * 0.15))
                        player.health = min(player.max_health, player.health + heal)
                        print(f"  ✦ Execute Momentum: +{heal} HP restored!")
                room.enemies.remove(enemy_name)
                player.gain_experience(enemy['exp'])
                self._handle_drops(enemy_name, room, player)
                return True

            # ── Enemy attacks ─────────────────────────────────────
            # Special attack on rhythm turns
            spec_turn = behaviour.get('special_turn', 0)
            if spec_turn and turn % spec_turn == 0:
                base_hit = DamageCalculator.calculate_enemy_damage(dmg, player)
                hit = int(base_hit * behaviour.get('special_dmg_mult', 1.5))
                print(f"*** {behaviour.get('special_msg', 'SPECIAL ATTACK')}! "
                      f"{enemy_name} deals {hit} damage!")
            else:
                hit = DamageCalculator.calculate_enemy_damage(dmg, player)
                # buff_others boost
                if buff_active:
                    hit = int(hit * 1.20)
                print(f"{enemy_name} hits for {hit} damage! "
                      f"[Your HP: {player.health - hit}/{player.max_health}]")

            # Void tonic absorption
            if getattr(player, 'void_absorb_active', False):
                player.void_absorb_active = False
                mp_gain = min(30, player.max_mana - player.mana) if hasattr(player, 'mana') else 0
                if mp_gain > 0:
                    player.mana += mp_gain
                print(f"  ✦ Void Tonic absorbs the hit! +{mp_gain} MP")
            else:
                # Cursed wearable damage multiplier
                cursed_mult = 1.0
                for item in player.inventory:
                    wi = GameConstants.WEARABLE_ITEMS.get(item, {})
                    if wi.get('cursed') and wi.get('dmg_taken_mult'):
                        cursed_mult = max(cursed_mult, wi['dmg_taken_mult'])
                if cursed_mult > 1.0:
                    hit = int(hit * cursed_mult)

                player.health -= hit
                player.fight_damage_taken = getattr(player, 'fight_damage_taken', 0) + hit

                # Status infliction on hit
                if behaviour.get('inflict') and random.random() < 0.45:
                    effect = behaviour['inflict']
                    if effect not in player.status_effects:
                        duration = GameConstants.STATUS_EFFECTS[effect]['duration']
                        player.status_effects[effect] = duration
                        icon = GameConstants.STATUS_EFFECTS[effect]['icon']
                        msg  = GameConstants.STATUS_EFFECTS[effect]['msg']
                        print(f"  {icon} {msg}")

                # Status effects tick
                for eff, turns in list(player.status_effects.items()):
                    se = GameConstants.STATUS_EFFECTS.get(eff, {})
                    if 'dmg_per_turn' in se:
                        tick = se['dmg_per_turn']
                        player.health -= tick
                        print(f"  {se['icon']} {eff.capitalize()} ticks: -{tick} HP "
                              f"({turns-1} turns left)")
                    player.status_effects[eff] = turns - 1
                player.status_effects = {k: v for k, v in player.status_effects.items() if v > 0}

                if player.health <= 0:
                    logger.error(f"PLAYER DEATH: {player.name} killed by {enemy_name}")
                    RecordsManager.update(total_deaths=1)
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
            player.total_gold_earned += coins
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
    
    # ── Boss combat helpers ───────────────────────────────────────

    def _resolve_player_boss_action(
        self, action: str, player: Player, boss_name: str,
        hp: int, max_hp: int, turn: int,
        rage_used: bool, rage_active: bool,
        phase_used: bool, boss_config: dict
    ) -> tuple:
        """Resolve one player action in boss combat.

        Returns (player_dmg, rage_used, rage_active, phase_used, defend, skip_turn)
        skip_turn=True means the action consumed the turn without dealing damage.
        """
        player_dmg = 0
        defend = False
        skip_turn = False

        if action in ["1", "attack", "a", "strike"]:
            player_dmg = DamageCalculator.calculate_player_damage(
                player, enemy_name=boss_name,
                enemy_hp=hp, enemy_max_hp=max_hp,
                first_hit=(turn == 1),
                skip_rarity_mult=True,
            )
            if rage_active:
                player_dmg = int(player_dmg * 1.5)
                rage_active = False
                print(f"*** RAGE STRIKE! {player_dmg} damage!")
            else:
                print(f"*** You strike for {player_dmg} damage!")

        elif action in ["2", "magic", "m", "spell"] and player.character_class == 'mage':
            if player.mana >= GameConstants.MAGIC_MANA_COST:
                player.mana -= GameConstants.MAGIC_MANA_COST
                spell_mult   = random.choice(GameConstants.MAGIC_MULTIPLIERS)
                base_magic   = random.randint(*GameConstants.MAGIC_DAMAGE_RANGE)
                arc_bonus    = player.stats.get('arcane', 0) * 0.5
                mana_bonus   = (player.mana / max(1, player.max_mana)) * 20
                player_dmg   = int((base_magic + player.stats['intelligence'] +
                                    arc_bonus + mana_bonus) * spell_mult)
                player_dmg   = max(player_dmg, player.stats['intelligence'])
                print(f"*** Magic spell hits for {player_dmg} damage!")
            else:
                print(f"Not enough mana! ({player.mana}/{GameConstants.MAGIC_MANA_COST} MP)")
                skip_turn = True

        elif action in ["2", "smite"] and player.character_class == 'paladin':
            if player.mana >= 20:
                player.mana -= 20
                faith      = player.stats.get('faith', 5)
                str_bonus  = player.stats['strength']
                smite_mult = 1.25 + (faith / 100)
                player_dmg = int((str_bonus * 1.5 + faith * 2) * smite_mult)
                print(f"*** DIVINE SMITE! Holy power: {player_dmg} damage!")
            else:
                print(f"Not enough mana! ({player.mana}/20 MP)")
                skip_turn = True

        elif action in ["2", "rage"] and player.character_class == 'berserker':
            if rage_used:
                print("Rage already spent this fight!")
                skip_turn = True
            else:
                rage_used   = True
                rage_active = True
                player_dmg  = 0
                print("*** BERSERKER RAGE! Your next attack deals 1.5x damage!")
                skip_turn = True

        elif action in ["2", "phase"] and player.character_class == 'void_walker':
            if phase_used:
                print("Phase already spent this fight!")
                skip_turn = True
            else:
                phase_used = True
                player_dmg = 0
                print("*** VOID PHASE! You slip between dimensions.")
                print("    The next enemy attack passes through you.")
                skip_turn = True

        elif action in ["2"] and getattr(player, 'fusion_parents', None):
            fusion = GameConstants.get_fusion(*player.fusion_parents)
            if fusion:
                if getattr(player, '_fusion_ab_used', False):
                    print(f"{fusion['boss_ability_name']} already spent this fight!")
                    skip_turn = True
                else:
                    player._fusion_ab_used = True
                    player_dmg, phase_used = self._resolve_fusion_ability(
                        fusion, player, phase_used)

        elif action in ["3", "defend", "d", "block"]:
            defend = True
            print("*** You take a defensive stance!")

        elif action in ["4", "heal", "h", "potion"]:
            ItemHandler.use_item(player, 'healing')
            skip_turn = True

        elif action in ["5", "swap", "sw"]:
            if player.inventory_weapons:
                player.switch_weapon()
            else:
                print("No stored weapons to swap.")
            skip_turn = True

        else:
            print("Invalid action. Try: attack, defend, heal, swap")
            skip_turn = True

        return player_dmg, rage_used, rage_active, phase_used, defend, skip_turn

    def _resolve_fusion_ability(self, fusion: dict, player: Player,
                                 phase_used: bool) -> tuple:
        """Resolve a fusion class boss ability. Returns (damage, phase_used)."""
        ab = fusion['boss_ability']
        player_dmg = 0

        if ab == 'spellblade_surge':
            phys = DamageCalculator.calculate_player_damage(player, skip_rarity_mult=True)
            mag  = max(10, int(player.stats['intelligence'] * 1.5) + player.stats.get('arcane', 0))
            player_dmg = phys + mag
            print(f"*** SPELLBLADE SURGE! {phys} physical + {mag} arcane = {player_dmg} total!")
        elif ab == 'blitz_strike':
            h1, h2 = (DamageCalculator.calculate_player_damage(player, skip_rarity_mult=True) for _ in range(2))
            player_dmg = int(h1 * 0.75) + int(h2 * 0.75)
            print(f"*** BLITZ STRIKE! {int(h1*0.75)} + {int(h2*0.75)} = {player_dmg} damage!")
        elif ab == 'wrath':
            base = DamageCalculator.calculate_player_damage(player, skip_rarity_mult=True)
            player_dmg = int(base * 1.5) + player.stats.get('faith', 5) * 2
            print(f"*** WRATH! Holy fury unleashed — {player_dmg} damage!")
        elif ab == 'total_war':
            hp_ratio = 1 + (1 - player.health / max(1, player.max_health))
            base = DamageCalculator.calculate_player_damage(player, skip_rarity_mult=True)
            player_dmg = int(base * (1.5 + hp_ratio))
            print(f"*** TOTAL WAR! ({hp_ratio:.2f}x HP multiplier) — {player_dmg} damage!")
        elif ab == 'void_strike':
            player_dmg = int(DamageCalculator.calculate_player_damage(player, skip_rarity_mult=True) * 1.6)
            print(f"*** VOID STRIKE! Bypasses resistance — {player_dmg} damage!")
        elif ab == 'shadow_spell':
            player_dmg = int((player.stats['intelligence'] * 2.5 + player.stats.get('arcane', 0)) * 2.5)
            print(f"*** SHADOW SPELL! Guaranteed critical strike — {player_dmg} arcane damage!")
        elif ab == 'divine_blaze':
            player_dmg = int((player.stats['intelligence'] * 1.8 + player.stats.get('arcane', 0) + player.stats.get('faith', 0) * 1.5) * 1.2)
            print(f"*** DIVINE BLAZE! Holy fire scorches the enemy — {player_dmg} damage!")
        elif ab == 'chaos_eruption':
            missing_pct = 1 - (player.health / max(1, player.max_health))
            player_dmg  = int(player.stats['intelligence'] * 3 * (1 + missing_pct * 2))
            cost        = max(5, player.health // 4)
            player.health = max(1, player.health - cost)
            print(f"*** CHAOS ERUPTION! {player_dmg} damage — but costs {cost} HP!")
        elif ab == 'phase_spell':
            player_dmg = int((player.stats['intelligence'] * 2 + player.stats.get('arcane', 0)) * 1.8)
            player._phase_absorbed = False
            phase_used = True
            print(f"*** PHASE SPELL! {player_dmg} magic damage — enemy retaliation skipped!")
        elif ab == 'holy_backstab':
            base = DamageCalculator.calculate_player_damage(player, skip_rarity_mult=True)
            player_dmg = int(base * 2.0) + player.stats.get('faith', 0) * 2
            print(f"*** HOLY BACKSTAB! Executioner + Holy Aura — {player_dmg} damage!")
        elif ab == 'frenzy':
            hits = [int(DamageCalculator.calculate_player_damage(player, skip_rarity_mult=True) * 0.6) for _ in range(3)]
            player_dmg = sum(hits)
            print(f"*** FRENZY! Triple hit: {hits[0]} + {hits[1]} + {hits[2]} = {player_dmg} damage!")
        elif ab == 'vanish_strike':
            phase_used = True
            player._phase_absorbed = False
            player_dmg = int(DamageCalculator.calculate_player_damage(player, skip_rarity_mult=True) * 2.5)
            print(f"*** VANISH STRIKE! Phase then critical hit — {player_dmg} damage!")
        elif ab == 'divine_fury':
            missing = 1 - player.health / max(1, player.max_health)
            player_dmg = int((player.stats['strength'] * 1.5 + player.stats.get('faith', 0) * 2) * (1 + missing))
            print(f"*** DIVINE FURY! Holy rage combined — {player_dmg} damage!")
        elif ab == 'null_smite':
            base = DamageCalculator.calculate_player_damage(player, skip_rarity_mult=True)
            player_dmg = int(base * 1.4) + player.stats.get('faith', 0) * 3
            print(f"*** NULL SMITE! Bypasses enemy defense — {player_dmg} damage!")
        elif ab == 'void_rage':
            phase_used = True
            player._phase_absorbed = False
            hp_ratio   = 1 + (1 - player.health / max(1, player.max_health))
            base       = DamageCalculator.calculate_player_damage(player, skip_rarity_mult=True)
            player_dmg = int(base * 1.5 * hp_ratio)
            print(f"*** VOID RAGE! Phase + Berserker combined — {player_dmg} damage!")
        else:
            player_dmg = DamageCalculator.calculate_player_damage(player, skip_rarity_mult=True)
            print(f"*** {fusion['boss_ability_name'].upper()}! {player_dmg} damage!")

        return player_dmg, phase_used

    def _apply_boss_attack(
        self, player: Player, boss_name: str, boss_config: dict,
        turn: int, phase_used: bool, defend: bool
    ) -> tuple:
        """Calculate and apply the boss's attack for this turn.

        Returns (alive, phase_used) where alive=False means player died.
        """
        use_special = (
            turn % GameConstants.BOSS_SPECIAL_TURN_FREQUENCY == 0 or
            (hasattr(player, '_boss_hp_ref') and
             player._boss_hp_ref < boss_config['base_health'] * GameConstants.BOSS_SPECIAL_HEALTH_THRESHOLD)
        )
        dmg = boss_config['damage'] + random.randint(1, boss_config['health_scaling'])

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

        if phase_used and not getattr(player, '_phase_absorbed', False):
            player._phase_absorbed = True
            print("*** VOID PHASE absorbs the attack! (0 damage!)")
            return True, phase_used

        player.health -= boss_dmg
        if player.health <= 0:
            logger.error(
                f"BOSS DEATH: {player.name} (Lvl {player.level}) "
                f"defeated by {boss_name} on turn {turn}"
            )
            RecordsManager.update(total_deaths=1)
            print(f"\n*** Defeated by {boss_name}! GAME OVER!")
            return False, phase_used

        return True, phase_used

    def fight_boss(self, boss_name: str, player: Player, room: Room) -> bool:
        """Boss combat — orchestrates the turn loop using focused helpers."""
        floor = player.current_floor
        ng    = getattr(player, 'ng_plus', 0)
        if ng > 0:
            world_key    = getattr(player, 'ng_world', 'fractured_labyrinth')
            weapon_scale = max(1.0, getattr(player, 'ng_weapon_scale', 1.0))
            boss_config  = BossConfig.generate_ng_plus(floor, ng, world_key,
                                                        weapon_scale=weapon_scale)
        else:
            boss_config = BossConfig.generate(floor)

        logger.info(
            f"BOSS FIGHT: {player.name} (Lvl {player.level}, HP {player.health}) "
            f"vs {boss_name} on floor {floor}"
        )
        print("\n" + "="*60)
        print(f"*** BOSS FIGHT: {boss_name.upper()}!")
        print("="*60)
        intro = GameConstants.BOSS_INTROS.get(boss_name)
        if intro:
            print()
            print(f"  {intro}")
            print()

        if player.level < boss_config['min_level']:
            logger.warning(
                f"Player {player.name} (Lvl {player.level}) attempting "
                f"{boss_name} (recommended Lvl {boss_config['min_level']})"
            )
            print(f"! WARNING: Recommended level {boss_config['min_level']}+!")
            try:
                if input("Continue? (y/n): ").strip().lower() not in ['y', 'yes']:
                    return True
            except KeyboardInterrupt:
                return True

        # Pre-fight weapon swap
        if player.inventory_weapons:
            print("\n--- Pre-fight: check your loadout ---")
            print(f"  Current weapon: {player.weapon['name']} ({player.weapon['damage']} dmg)")
            for i, w in enumerate(player.inventory_weapons, 1):
                print(f"  {i}. {w['name']} ({w['damage']} dmg, {w.get('rarity','common')})")
            print("  0. Keep current weapon")
            try:
                sw_choice = input("  Swap weapon before fight? (0 to skip): ").strip()
                if sw_choice != '0' and sw_choice.isdigit():
                    idx = int(sw_choice) - 1
                    if 0 <= idx < len(player.inventory_weapons):
                        player.switch_weapon(str(idx + 1))
            except (ValueError, KeyboardInterrupt):
                pass

        # d20 check
        if "gambler's d20" in player.special_items:
            roll = random.randint(1, 20)
            print(f"\n  ⚄ You pull out the Gambler's d20 and roll... {roll}!")
            if roll == 20:
                print(f"  ★ NATURAL 20! The universe conspires against {boss_name}!")
                print("  ★ INSTANT KILL! (The d20 shatters.)")
                player.special_items.remove("gambler's d20")
                player.gain_experience(boss_config['exp_reward'])
                room.enemies.clear()
                room.items.append("champion's prize")
                return True
            elif roll == 1:
                print("  ✗ Critical failure. You fumbled the d20. Gone forever.")
                player.special_items.remove("gambler's d20")
            else:
                print(f"  Not a 20. The d20 stays for next time.")

        hp     = boss_config['base_health'] + boss_config['health_scaling'] * player.level
        max_hp = hp
        turn   = 1
        rage_used   = False
        rage_active = False
        phase_used  = False

        while hp > 0 and player.health > 0:
            print(f"\n--- Turn {turn} ---")

            # Cursed drain
            if player.weapon:
                for tk in player.weapon.get('traits', []):
                    td = GameConstants.WEAPON_TRAITS.get(tk, {})
                    if td.get('effect') == 'cursed':
                        player.health -= td['hp_drain']
                        print(f"  ✦ Cursed drain: -{td['hp_drain']} HP")
                        if player.health <= 0:
                            print("*** The curse claims you! GAME OVER!")
                            return False

            # HUD
            if player.character_class in ('mage', 'paladin'):
                print(f"You: {player.health}/{player.max_health} HP | {player.mana}/{player.max_mana} MP")
            else:
                print(f"You: {player.health}/{player.max_health} HP")
            print(f"{boss_name}: {hp}/{max_hp} HP")

            # Build action menu
            actions = ["1. Attack"]
            if player.character_class == 'mage':
                actions.append("2. Magic")
            elif player.character_class == 'paladin' and player.mana >= 20:
                actions.append("2. Smite (20 MP)")
            elif player.character_class == 'berserker':
                actions.append(f"2. Rage{' [SPENT]' if rage_used else ''}")
            elif player.character_class == 'void_walker':
                actions.append(f"2. Phase{' [SPENT]' if phase_used else ''}")
            elif getattr(player, 'fusion_parents', None):
                fd = GameConstants.get_fusion(*player.fusion_parents)
                if fd:
                    spent = getattr(player, '_fusion_ab_used', False)
                    actions.append(f"2. {fd['boss_ability_name']}{' [SPENT]' if spent else ''}")
            actions.append("3. Defend")
            if any(i in GameConstants.HEALING_ITEMS for i in player.inventory):
                actions.append("4. Heal")
            if player.inventory_weapons:
                actions.append("5. Swap Weapon")

            print("  " + " | ".join(actions))
            print("  (type the number or word, e.g. 'attack' or '1')")

            try:
                action = input("Action: ").strip().lower()
            except KeyboardInterrupt:
                action = "defend"

            (player_dmg, rage_used, rage_active, phase_used,
             defend, skip_turn) = self._resolve_player_boss_action(
                action, player, boss_name, hp, max_hp, turn,
                rage_used, rage_active, phase_used, boss_config
            )

            if skip_turn:
                turn += 1
                continue

            if player_dmg > 0:
                hp -= player_dmg

            if hp <= 0:
                break

            # Boss's turn
            player._boss_hp_ref = hp
            alive, phase_used = self._apply_boss_attack(
                player, boss_name, boss_config, turn, phase_used, defend
            )
            if not alive:
                return False

            turn += 1

        # ── Victory ──────────────────────────────────────────────
        logger.info(
            f"BOSS VICTORY: {player.name} defeated {boss_name} "
            f"in {turn} turns on floor {floor}"
        )
        print("\n" + "="*60)
        print("*** VICTORY!")
        print("="*60)

        # Clean up per-fight flags
        for attr in ('_phase_absorbed', '_fusion_ab_used', '_boss_hp_ref'):
            if hasattr(player, attr):
                delattr(player, attr)

        room.enemies.remove(boss_name)
        player.bosses_defeated.append(boss_name)
        player.gain_experience(boss_config['exp_reward'])
        RecordsManager.update(total_bosses_defeated=1, best_floor_reached=floor)

        if "champion's prize" not in room.items:
            room.items.append("champion's prize")
            print("\n*** A champion's prize chest appears!")

        boss_weapon = BossConfig.generate_boss_weapon(floor, player)
        logger.info(
            f"Boss reward: {player.name} received {boss_weapon['name']} "
            f"({boss_weapon['damage']} dmg)"
        )
        tier_label = boss_weapon.get('tier_label', 'GOOD')
        tier_stars = {'GOOD': '★', 'GREAT': '★★★', 'INSANE': '★★★★★'}.get(tier_label, '★')
        print(f"\n*** BOSS WEAPON DROP: {tier_stars} {tier_label} {tier_stars}")
        print(f"*** {boss_weapon['name']} ({boss_weapon['rarity'].upper()})")
        print(f"[Scaled for your level: {player.level}]")

        comparison = WeaponComparison.compare_weapons(boss_weapon, player.weapon, player)
        print(comparison)

        try:
            equip = input("  Equip new weapon? (y/n): ").strip().lower()
        except KeyboardInterrupt:
            equip = 'n'

        if equip in ('y', 'yes'):
            if player.weapon:
                player.inventory_weapons.append(player.weapon)
                label = f"WEAPON: {player.weapon['name']}"
                if label not in player.inventory:
                    player.inventory.append(label)
            player.weapon = boss_weapon
            print(f"  Equipped {boss_weapon['name']}!")
        else:
            player.add_weapon_to_inventory(boss_weapon)
            print(f"  Stored {boss_weapon['name']} in inventory.")

        stat_bonus = boss_config['stat_bonus']
        chosen_stat = random.choice(['strength', 'agility', 'intelligence', 'luck', 'vitality'])
        player.stats[chosen_stat] = player.stats.get(chosen_stat, 0) + stat_bonus
        print(f"\n  +{stat_bonus} {chosen_stat.capitalize()} from the battle!")

        if floor == GameConstants.NUM_FLOORS:
            logger.info(f"GAME COMPLETE: {player.name} defeated all bosses!")
            try:
                input("\n  [ Press Enter to see your victory screen... ]")
            except KeyboardInterrupt:
                pass
            self._victory_screen()

        return True


#################################################################################
# COMMAND REGISTRY
#################################################################################
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


#################################################################################
# HALL OF RECORDS — persistent cross-run stats
#################################################################################
class RecordsManager:
    """Persists stats across all runs in saves/records.json"""
    PATH = os.path.join(GameConstants.SAVE_DIRECTORY, 'records.json')

    DEFAULTS = {
        'total_bosses_defeated': 0,
        'total_deaths':          0,
        'total_floors_cleared':  0,
        'runs_completed':        0,
        'best_floor_reached':    0,
        'void_walker_unlocked':  False,
        'adamus_impressed':      False,
        'first_clear_name':      None,
    }

    @classmethod
    def load(cls) -> dict:
        try:
            if os.path.exists(cls.PATH):
                with open(cls.PATH) as f:
                    data = json.load(f)
                # backfill any new keys
                for k, v in cls.DEFAULTS.items():
                    data.setdefault(k, v)
                return data
        except (json.JSONDecodeError, OSError, KeyError):
            pass
        return cls.DEFAULTS.copy()

    @classmethod
    def save(cls, records: dict) -> None:
        try:
            os.makedirs(GameConstants.SAVE_DIRECTORY, exist_ok=True)
            with open(cls.PATH, 'w') as f:
                json.dump(records, f, indent=2)
        except OSError:
            pass

    @classmethod
    def update(cls, **kwargs) -> dict:
        rec = cls.load()
        for k, v in kwargs.items():
            if k in ('total_bosses_defeated', 'total_deaths',
                     'total_floors_cleared', 'runs_completed'):
                rec[k] = rec.get(k, 0) + v
            elif k == 'best_floor_reached':
                rec[k] = max(rec.get(k, 0), v)
            else:
                rec[k] = v
        cls.save(rec)
        return rec

    @classmethod
    def display(cls) -> None:
        rec = cls.load()
        print("\n" + "═"*50)
        print("  ★  HALL OF RECORDS  ★")
        print("═"*50)
        print(f"  Bosses defeated (all runs) : {rec['total_bosses_defeated']}")
        print(f"  Floors cleared (all runs)  : {rec['total_floors_cleared']}")
        print(f"  Deaths (all runs)          : {rec['total_deaths']}")
        print(f"  Runs completed             : {rec['runs_completed']}")
        print(f"  Best floor reached         : {rec['best_floor_reached']}/10")
        if rec['first_clear_name']:
            print(f"  First clear by             : {rec['first_clear_name']}")
        print()
        if rec['void_walker_unlocked']:
            print("  ★ VOID WALKER UNLOCKED — available at character creation")
        else:
            print("  [ Beat the game to unlock the Void Walker class ]")
        print("═"*50)

#################################################################################
# COMMAND REGISTRY
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
            if not g.player.can_upgrade_class():
                if g.player.class_tier >= 5:
                    print("  Already at maximum tier.")
                else:
                    print(f"  Need Level {GameConstants.CLASS_UPGRADE_LEVELS.get(g.player.class_tier + 1, '?')} to upgrade.")
                return
            if g.player.upgrade_class():
                print(f"\n  ★ Class upgraded to Tier {g.player.class_tier}!")
                print(f"  You are now: {g.player.get_class_title()}")
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

        @r('fuse', 'fusion')
        def cmd_fuse(g): g.fuse_class_menu()
    
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
                    continue

                elif choice == '4':
                    RecordsManager.display()
                    try:
                        input("  [ Press Enter to return ]")
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
            choice = input("Class: ").strip()
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
        """Generate complete dungeon with unique item tracking.
        Branches into NG+ content when player.ng_plus > 0."""
        ng = getattr(self.player, 'ng_plus', 0)
        if ng > 0:
            ng_world_key  = getattr(self.player, 'ng_world', 'fractured_labyrinth')
            ng_world_data = GameConstants.NG_PLUS_WORLDS.get(ng_world_key,
                            GameConstants.NG_PLUS_WORLDS['fractured_labyrinth'])
            ng_world_name = ng_world_data['display_name']
        else:
            ng_world_name = 'dungeon'
        logger.info(f"Starting dungeon generation (NG+{ng})...")
        print(f"\n*** Generating {ng_world_name if ng > 0 else 'dungeon'}...")
        self.floors = {}

        if ng > 0:
            self._generate_ng_plus_dungeon(ng)
            return

        # Track unique items across entire dungeon (items that should only spawn once)
        unique_item_types = {'rusty key', 'bone key', 'torch', 'ancient medallion',
                              'journal_1','journal_2','journal_3','journal_4','journal_5'}
        # Which floor each journal entry appears on
        JOURNAL_FLOORS = {2: 'journal_1', 4: 'journal_2', 5: 'journal_3',
                          7: 'journal_4', 9: 'journal_5'}
        
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
            # Deduplicate by name — same template name can appear in both
            # the theme config and SPECIAL_ROOMS, which random.sample would
            # treat as distinct objects and potentially pick both.
            seen_names = set()
            pool = []
            for t in templates:
                if t.name not in DEST_NAMES and t.name not in seen_names:
                    pool.append(t)
                    seen_names.add(t.name)
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
            boss_floor  = self.player.current_floor
            ng          = getattr(self.player, 'ng_plus', 0)
            if ng > 0:
                world_key   = getattr(self.player, 'ng_world', 'fractured_labyrinth')
                boss_config = BossConfig.generate_ng_plus(boss_floor, ng, world_key,
                                                           weapon_scale=max(1.0, getattr(self.player, 'ng_weapon_scale', 1.0)))
            else:
                boss_config = BossConfig.generate(boss_floor)
            if boss_config['name'] not in self.player.bosses_defeated:
                print(f"! Blocked! Defeat {boss_config['name']} first!")
                return
        
        old_floor = self.player.current_floor
        
        if direction in ['down', 'up'] and 'floor' in next_id:
            next_floor = int(next_id.split('_')[0].replace('floor', ''))
            if next_floor != self.player.current_floor:
                self.player.current_floor = next_floor
                print(f"\n→ Floor {self.player.current_floor}")
                RecordsManager.update(total_floors_cleared=1,
                                      best_floor_reached=next_floor)
                # Floor lore (v7.5.2)
                lore = GameConstants.FLOOR_LORE.get(next_floor)
                if lore:
                    print()
                    print(lore)
                
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

        # Status effects tick between rooms
        if getattr(self.player, 'status_effects', {}):
            for eff, turns in list(self.player.status_effects.items()):
                se = GameConstants.STATUS_EFFECTS.get(eff, {})
                if 'dmg_per_turn' in se and turns > 0:
                    tick = max(1, se['dmg_per_turn'] // 2)
                    self.player.health -= tick
                    print(f"  {se['icon']} {eff.capitalize()} ticks: -{tick} HP "
                          f"({turns-1} turns left)")
                    if self.player.health <= 0:
                        self.player.health = 1
                self.player.status_effects[eff] = turns - 1
            self.player.status_effects = {
                k: v for k, v in self.player.status_effects.items() if v > 0
            }

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
    
    def _fight_enemy_command(self, enemy_name: str):
        """Command handler: routes fight to CombatSystem."""
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
        """Use a special/quest item. Dispatches to a focused handler per item."""
        if not item_name:
            print("Use what?")
            return

        # Old map — lives in special_items, not inventory
        if item_name == 'old map':
            if item_name in self.player.special_items:
                print("You study the old map...")
                self.show_map()
            else:
                print("You don't have an old map.")
            return

        # d20 — also lives in special_items
        if item_name in ("gambler's d20", "d20"):
            if "gambler's d20" not in self.player.special_items:
                print("You don't have a Gambler's d20.")
            else:
                self._use_d20()
            return

        if item_name not in self.player.inventory:
            print(f"Don't have '{item_name}'")
            return

        if item_name not in GameConstants.ACTIONABLE_ITEMS:
            print(f"Can't use '{item_name}' like that")
            return

        handler = {
            'torch':             self._use_torch,
            'rusty key':         self._use_rusty_key,
            'bone key':          self._use_bone_key,
            'demon seal':        self._use_demon_seal,
            'crystal shard':     self._use_crystal_shard,
            'void essence':      self._use_void_essence,
            'primordial rune':   self._use_primordial_rune,
            'ancient medallion': self._use_ancient_medallion,
            'journal_1':         lambda: self._read_journal('journal_1'),
            'journal_2':         lambda: self._read_journal('journal_2'),
            'journal_3':         lambda: self._read_journal('journal_3'),
            'journal_4':         lambda: self._read_journal('journal_4'),
            'journal_5':         lambda: self._read_journal('journal_5'),
        }.get(item_name)

        if handler:
            handler()
        else:
            print(f"Can't use '{item_name}' here.")

    # ── Special item handlers ─────────────────────────────────────

    def _use_d20(self):
        """Gambler's d20 — instant-kill chance in any fight."""
        room = self.get_current_room()
        if not room.enemies:
            print("No enemies here to use the d20 on.")
            return
        roll = random.randint(1, 20)
        print(f"\n  ⚄ You roll the Gambler's d20... {roll}!")
        if roll == 20:
            print("  ★ NATURAL 20! Cosmic annihilation!")
            for enemy in list(room.enemies):
                ng_e = getattr(self.player, 'ng_plus', 0)
                if ng_e > 0:
                    wk = getattr(self.player, 'ng_world', 'fractured_labyrinth')
                    ep = GameConstants.NG_PLUS_WORLDS.get(wk, {}).get('enemies', GameConstants.NG_PLUS_ENEMIES)
                else:
                    ep = GameConstants.ENEMIES
                self.player.gain_experience(ep.get(enemy.lower(), {'exp': 50}).get('exp', 50))
                room.enemies.clear()
            print("  ★ All enemies annihilated! (The d20 shatters.)")
            self.player.special_items.remove("gambler's d20")
        elif roll == 1:
            print("  ✗ Critical failure. The d20 bounces away. Gone forever.")
            self.player.special_items.remove("gambler's d20")
        else:
            print("  Not a 20. The d20 stays in your pocket.")

    def _use_torch(self):
        """Torch — unlocks Hidden Alcove secret rooms."""
        room = self.get_current_room()
        if 'Hidden Alcove' in room.name and not self.player.secret_room_unlocked:
            print("\n*** You place the torch in the wall sconce...")
            print("A hidden door slides open!")
            self.player.secret_room_unlocked = True
            self.player.inventory.remove('torch')
            # Add passage to the secret room
            for r_id, r in self.floors[self.player.current_floor].items():
                if 'Secret' in r.name and r_id not in room.exits.values():
                    room.exits['secret'] = r_id
                    print(f"  A hidden passage leads to: {r.name}")
                    break
        else:
            if 'torch' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('torch')
                print("You hold up the torch. Nothing happens here.")
                print("  ★ HINT: Find the Hidden Alcove — it has a torch sconce on the wall.")
                print("         The sconce looks like it could hold something. Use the torch there.")
            else:
                print("The torch flickers. You need a Hidden Alcove with a wall sconce.")

    def _use_rusty_key(self):
        """Rusty key — opens the Locked Vault."""
        room = self.get_current_room()
        if room.name == 'Locked Vault' and not room.visited:
            print("\n*** You insert the rusty key into the ancient lock...")
            print("The vault opens! Inside: piles of treasure!")
            self.player.inventory.remove('rusty key')
            gold = random.randint(50, 150)
            self.player.gold_coins += gold
            self.player.total_gold_earned += gold
            room.items.extend(['ultimate health potion', 'power ring', 'experience gem'])
            print(f"  +{gold} gold coins!")
            print("  Found: ultimate health potion, power ring, experience gem")
        else:
            if 'rusty key' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('rusty key')
                print("You examine the key. It looks like it would fit a large lock...")
                print("  ★ HINT: Find the Locked Vault — a sealed room with an ornate chest")
                print("         and an old rusty keyhole. Use the key there to claim the treasure.")
            else:
                print("The rusty key is waiting for the Locked Vault.")

    def _use_bone_key(self):
        """Bone key — opens the Bone Crypt."""
        room = self.get_current_room()
        if room.name == 'Bone Crypt':
            print("\n*** The bone key rattles as you insert it into the bone door...")
            print("Ancient remains and forbidden knowledge lie within!")
            self.player.inventory.remove('bone key')
            room.items.extend(['wisdom gem', 'shadow cloak', 'ancient medallion'])
            self.player.gain_experience(200)
            print("  Found: wisdom gem, shadow cloak, ancient medallion")
            print("  +200 XP from the forbidden knowledge!")
        else:
            if 'bone key' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('bone key')
                print("The bone key rattles ominously. This is meant for a bone door...")
                print("  ★ HINT: Find the Bone Crypt — a chamber where ancient bones line the walls")
                print("         and a sealed bone door blocks the way deeper. The key fits that lock.")
            else:
                print("The bone key rattles. It belongs in the Bone Crypt.")

    def _use_demon_seal(self):
        """Demon seal — banishes demons or opens Demon Gates."""
        room = self.get_current_room()
        demons = [e for e in room.enemies if 'demon' in e.lower() or 'devil' in e.lower()]
        if room.name == 'Demon Gate':
            print("\n*** You press the demon seal against the arcane chains...")
            print("The gate shatters! A reward lies beyond!")
            self.player.inventory.remove('demon seal')
            room.items.extend(['power ring', 'demon seal', 'ultimate health potion'])
            print("  Found: power ring, demon seal, ultimate health potion")
        elif demons:
            print(f"\n*** You brandish the demon seal! The demons recoil!")
            for d in demons:
                room.enemies.remove(d)
                ng_e = getattr(self.player, 'ng_plus', 0)
                ep = (GameConstants.NG_PLUS_WORLDS.get(
                    getattr(self.player, 'ng_world', 'fractured_labyrinth'), {})
                    .get('enemies', GameConstants.NG_PLUS_ENEMIES) if ng_e > 0
                    else GameConstants.ENEMIES)
                exp = ep.get(d.lower(), {'exp': 85}).get('exp', 85)
                print(f"  The {d} is banished! +{exp} exp")
                self.player.gain_experience(exp)
            self.player.inventory.remove('demon seal')
        else:
            if 'demon seal' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('demon seal')
                print("The demon seal pulses with dark energy. It's meant for demons...")
                print("  ★ HINT: Use it in a Demon Gate room (sealed by arcane chains)")
                print("         or carry it into any room with demon enemies to banish them instantly.")
            else:
                print("The seal pulses. Take it to a Demon Gate or use it against demon enemies.")

    def _use_crystal_shard(self):
        """Crystal shard — activates Crystal Chamber mechanism."""
        room = self.get_current_room()
        if room.name == 'Crystal Chamber':
            print("\n*** You insert the crystal shard into the mechanism...")
            print("The crystals resonate! Energy surges through you!")
            self.player.inventory.remove('crystal shard')
            for stat in ['strength', 'intelligence', 'agility']:
                self.player.stats[stat] = self.player.stats.get(stat, 0) + 3
            self.player.max_health += 20
            self.player.health = min(self.player.health + 20, self.player.max_health)
            print("  +3 STR, +3 INT, +3 AGI, +20 Max HP!")
        else:
            if 'crystal shard' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('crystal shard')
                print("The crystal shard glows softly. It needs a crystal mechanism...")
                print("  ★ HINT: Find the Crystal Chamber — every surface covered in crystalline")
                print("         formations with a dormant mechanism at the centre. Insert the shard there.")
            else:
                print("The shard glows. Bring it to the Crystal Chamber.")

    def _use_void_essence(self):
        """Void essence — seals the Void Tear."""
        room = self.get_current_room()
        if room.name == 'Void Tear':
            print("\n*** You channel the void essence into the tear...")
            print("The void tears seals shut! Reality stabilises!")
            self.player.inventory.remove('void essence')
            self.player.stats['intelligence'] = self.player.stats.get('intelligence', 0) + 5
            self.player.stats['luck']          = self.player.stats.get('luck', 0) + 3
            self.player.gain_experience(300)
            print("  +5 INT, +3 LCK, +300 XP!")
        else:
            if 'void essence' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('void essence')
                print("The void essence writhes with otherworldly power. It needs a void tear...")
                print("  ★ HINT: Find the Void Tear — a room where reality fractures, with a")
                print("         swirling unstable portal. Channel the essence into it to stabilise it.")
            else:
                print("The essence writhes. It belongs in the Void Tear room.")

    def _use_primordial_rune(self):
        """Primordial rune — charges the Primordial Monument."""
        room = self.get_current_room()
        if room.name == 'Primordial Monument':
            print("\n*** You place the primordial rune on the monument...")
            print("Ancient power flows into you!")
            self.player.inventory.remove('primordial rune')
            for stat in self.player.stats:
                self.player.stats[stat] = self.player.stats.get(stat, 0) + 2
            self.player.max_health += 30
            self.player.health = min(self.player.health + 30, self.player.max_health)
            print("  +2 to ALL stats, +30 Max HP!")
        else:
            if 'primordial rune' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('primordial rune')
                print("The primordial rune hums with ancient power. It belongs on a monument...")
                print("  ★ HINT: Find the Primordial Monument — an ancient stone covered in glowing")
                print("         runic inscriptions. Place the rune there to unlock its full power.")
            else:
                print("The rune hums. Place it on the Primordial Monument.")

    def _read_journal(self, journal_key: str):
        """Read a discoverable journal entry."""
        entry = GameConstants.JOURNAL_ENTRIES.get(journal_key)
        if entry:
            print("\n" + "─"*52)
            print(entry)
            print("─"*52)
            print("  (The journal is worn but readable. You keep it.)")
        else:
            print("The journal is too damaged to read.")

    def _use_ancient_medallion(self):
        """Ancient medallion — activates the Sacred Shrine."""
        room = self.get_current_room()
        if room.name == 'Sacred Shrine':
            print("\n*** You place the medallion on the altar...")
            print("The shrine awakens! Ancient blessings wash over you!")
            self.player.inventory.remove('ancient medallion')
            self.player.max_health += 50
            self.player.health = min(self.player.health + 50, self.player.max_health)
            self.player.stats['strength']     = self.player.stats.get('strength', 0) + 4
            self.player.stats['vitality']     = self.player.stats.get('vitality', 0) + 4
            self.player.rarity_boost         += 15
            print("  +50 Max HP, +4 STR, +4 VIT, +15% weapon rarity boost!")
        else:
            if 'ancient medallion' not in self.player.item_hints_shown:
                self.player.item_hints_shown.add('ancient medallion')
                print("You hold the medallion. It should be placed on an altar...")
                print("  ★ HINT: Find the Sacred Shrine — an ancient room with a stone altar")
                print("         that has a circular indentation. Place the medallion there.")
            else:
                print("The medallion waits for the Sacred Shrine.")
    def open_shop(self):
        """Open shop"""
        if self.player.current_floor > 1 and 'start' not in self.player.current_room:
            print("! No shop here. Visit the floor's starting room to find a merchant.")
            return
        
        if self.player.current_floor == 1 and self.player.current_room != 'start':
            print("! No shop here. Return to the entrance hall to find a merchant.")
            return
        
        rec = RecordsManager.load()
        # One-time acknowledgment the first shop visit after clearing the game
        if rec.get('runs_completed', 0) > 0 and not rec.get('adamus_impressed', False):
            RecordsManager.update(adamus_impressed=True)
            print("\n" + "="*50)
            print("  ☠  ADAMUS THE LOYAL — Purveyor of Fine Goods  ☠")
            print("="*50)
            print(f"  '{self.player.name}.'")
            print(f"  Adamus pauses. Sets down whatever he was doing.")
            print(f"  He doesn't look at you.")
            print(f"  'You actually did it. I didn't think you had it in you.'")
            print(f"  A long pause.")
            print(f"  \"Don't make me say that again. Now. What do you need.\"")
            print("-"*50)
            print(f"  Your Gold: {self.player.gold_coins}")
        else:
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

            greeting = random.choice(ADAMUS_GREETINGS)
            quip     = random.choice(ADAMUS_QUIPS)
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



        def _weapon_sell_value(w) -> int:
            """Calculate sell value based on damage and rarity."""
            RARITY_SELL_MULT = {
                'common': 0.30, 'uncommon': 0.38, 'rare': 0.48,
                'epic': 0.60, 'legendary': 0.80, 'mythic': 1.00,
            }
            base   = w.get('damage', 10)
            mult   = RARITY_SELL_MULT.get(w.get('rarity', 'common'), 0.30)
            traits = len(w.get('traits', []))
            value  = int(base * mult) + (traits * 3)
            return max(5, value)

        ADAMUS_SALES = [
            f"Fine. Here's your {{item}}. Don't come crying to me when it doesn't save you.",
            f"There. {{item}}. Pleasure doing business — emphasis on 'business', none on 'pleasure'.",
            f"{{item}}, gone. Your gold, gone. My patience, also gone.",
            f"Enjoy your {{item}}. It's better than you deserve.",
            f"Here. {{item}}. Try not to die before you get any use out of it.",
        ]

        ADAMUS_BUYS = [
            "Fine. I'll take it. Don't expect me to be grateful.",
            "Done. Here's your gold. I've seen better but I won't say when.",
            "Sold. I'll give it a good home. Better than you were giving it.",
            "Transaction complete. Try not to spend it on something stupid.",
            "There. Gold for the weapon. We're even. Don't get sentimental.",
        ]

        ADAMUS_LEGENDARY_CHECKS = [
            f"...Hold on. Let me actually look at this.",
            f"You understand what you're holding, right?",
            f"I've only seen two of these in twenty years of trading.",
        ]

        ADAMUS_MYTHIC_CHECKS = [
            f"Put that away. I'm not buying that. I'm not even — where did you GET this.",
            f"No. Absolutely not. I don't deal in things that could level a city block.",
            f"A mythic. In MY shop. Do you have ANY idea what this is worth.",
        ]

        while True:
            print(f"\n  Stock: {tier_name}  |  {len(items)} items available")
            print("-"*50)
            for i, (name, price, desc) in enumerate(items, 1):
                can_afford = "  " if self.player.gold_coins >= price else "✗ "
                print(f"  {can_afford}{i:>2}. {name:<28} {price:>3}g   {desc}")
            print("-"*50)
            sell_opts = []
            if self.player.inventory_weapons:
                print(f"\n  Weapons you can sell:")
                for j, w in enumerate(self.player.inventory_weapons):
                    val = _weapon_sell_value(w)
                    rar = w.get('rarity', 'common').upper()
                    print(f"  S{j+1}. {w['name']:<28} {w.get('damage',0):>3}dmg  {rar:<10}  → {val}g")
                    sell_opts.append(w)
                print()
            print(f"  {len(items)+1}. Leave")
            print(f"  Your Gold: {self.player.gold_coins}g")
            print("-"*50)

            try:
                raw = input("\n  Choice (buy # or S# to sell): ").strip()
            except KeyboardInterrupt:
                print("  Adamus waves you off.")
                return

            if not raw:
                continue

            # ── Leave ───────────────────────────────────────────
            if raw in (str(len(items)+1), 'leave', 'exit', 'q'):
                print("  Adamus doesn't say goodbye. He never does.")
                return

            # ── Sell ────────────────────────────────────────────
            if raw.lower().startswith('s') and len(raw) > 1:
                try:
                    sidx = int(raw[1:]) - 1
                    if not (0 <= sidx < len(sell_opts)):
                        print("  Invalid sell choice.")
                        continue
                    w = sell_opts[sidx]
                    val = _weapon_sell_value(w)
                    rarity = w.get('rarity', 'common')
                    wname  = w.get('name', 'Unknown')

                    # Adamus reacts to rarity before confirming
                    if rarity == 'mythic':
                        print(f"\n  Adamus looks at {wname}.")
                        print(f"  '{random.choice(ADAMUS_MYTHIC_CHECKS)}'")
                        print(f"  'I'll give you {val}g. But I'm doing you a disservice.'")
                        print(f"  'Are you absolutely certain you want to sell this?'")
                        try:
                            confirm = input("  Sell mythic weapon? (yes/no): ").strip().lower()
                        except KeyboardInterrupt:
                            confirm = 'no'
                        if confirm not in ('yes', 'y'):
                            print("  Adamus nods. 'Wise.'")
                            continue

                    elif rarity == 'legendary':
                        print(f"\n  Adamus picks up {wname} and turns it over slowly.")
                        print(f"  '{random.choice(ADAMUS_LEGENDARY_CHECKS)}'")
                        print(f"  'I can do {val}g. You sure about this?'")
                        try:
                            confirm = input("  Sell legendary weapon? (yes/no): ").strip().lower()
                        except KeyboardInterrupt:
                            confirm = 'no'
                        if confirm not in ('yes', 'y'):
                            print("  Adamus sets it back down. 'Thought so.'")
                            continue

                    # Complete the sale
                    self.player.inventory_weapons.remove(w)
                    label = f"WEAPON: {{w['name']}}"
                    if label in self.player.inventory:
                        self.player.inventory.remove(label)
                    self.player.gold_coins += val
                    self.player.total_gold_earned += val
                    print(f"  '{random.choice(ADAMUS_BUYS)}'")
                    print(f"  Sold {wname} for {val}g  |  Gold: {{self.player.gold_coins}}g")
                    sell_opts = list(self.player.inventory_weapons)
                    continue
                except (ValueError, IndexError):
                    print("  Invalid sell choice.")
                    continue

            # ── Buy ─────────────────────────────────────────────
            try:
                choice = int(raw)
            except ValueError:
                print("  Adamus stares at you. 'That's not a number.'")
                continue

            if not (1 <= choice <= len(items)):
                print("  Invalid choice.")
                continue

            item, price, desc = items[choice - 1]
            if self.player.gold_coins < price:
                print(f"  'Not enough gold. Need {{price}}g, you have {{self.player.gold_coins}}g.'")
                continue

            if not self.player.can_add_item() and item not in GameConstants.WEARABLE_ITEMS:
                print("  Inventory full!")
                continue

            self.player.gold_coins -= price
            if item == 'weapon cache':
                new_weapon = WeaponSystem.generate_weapon(self.player)
                comparison = WeaponSystem.compare_weapons(new_weapon, self.player)
                print(comparison)
                try:
                    if input("  Equip? (y/n): ").strip().lower() in ('y', 'yes'):
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

            sale_line = random.choice(ADAMUS_SALES).format(item=item)
            print(f"  '{sale_line}'")
            print(f"  Gold remaining: {{self.player.gold_coins}}g")
    
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
                    except (json.JSONDecodeError, OSError, KeyError, TypeError):
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
                    except (json.JSONDecodeError, OSError, KeyError, TypeError):
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

            # Determine if this is an NG+ save so room names load correctly
            ng         = getattr(self.player, 'ng_plus', 0)
            ng_world   = getattr(self.player, 'ng_world', 'fractured_labyrinth')
            is_ng_plus = ng > 0

            self.floors = {}
            for floor_str, floor_data in save_data['floors'].items():
                floor_num = int(floor_str)
                self.floors[floor_num] = {}

                for room_id, room_data in floor_data.items():
                    if room_id == 'start' or (room_id.endswith('_start') and is_ng_plus):
                        if is_ng_plus:
                            world_data = GameConstants.NG_PLUS_WORLDS.get(ng_world,
                                         GameConstants.NG_PLUS_WORLDS['fractured_labyrinth'])
                            world_name = world_data['display_name']
                            name = f"{world_name} — Entry" if floor_num == 1 else f"{world_name} — Floor {floor_num}"
                            desc = "Adamus is here, somehow. He looks unsurprised."
                        else:
                            name = "Entrance Hall"
                            desc = "The dungeon entrance."
                        atmo = "Adamus the Loyal has set up shop here. Use 'shop' to trade."

                    elif 'boss' in room_id:
                        if is_ng_plus:
                            boss_tmpl = BossConfig.get_ng_plus_boss_room_template_for_world(floor_num, ng_world)
                            name, desc, atmo = boss_tmpl.name, boss_tmpl.description, boss_tmpl.atmosphere
                        else:
                            template  = BossConfig.get_boss_room_template(floor_num)
                            name, desc, atmo = template.name, template.description, template.atmosphere

                    elif 'stairs' in room_id:
                        if is_ng_plus:
                            world_data = GameConstants.NG_PLUS_WORLDS.get(ng_world,
                                         GameConstants.NG_PLUS_WORLDS['fractured_labyrinth'])
                            name = f"{world_data['display_name']} — Descent"
                            desc = "Steps down into something worse."
                        else:
                            name = "Ancient Stairway"
                            desc = "Stone stairs descend deeper."
                        atmo = ""

                    elif 'secret' in room_id:
                        name, desc, atmo = "Secret Treasure Vault", "A hidden vault glitters with treasures!", "Countless riches!"

                    else:
                        if is_ng_plus:
                            # Pick from NG+ room config for this world and floor
                            room_config_map = {
                                'fractured_labyrinth': RoomTemplateConfig.NG_PLUS_THEME_CONFIG,
                                'drowned_kingdom':     RoomTemplateConfig.NG_PLUS_DROWNED_THEME,
                                'ashen_wastes':        RoomTemplateConfig.NG_PLUS_ASHEN_THEME,
                                'mechanical_depths':   RoomTemplateConfig.NG_PLUS_MECHANICAL_THEME,
                                'plague_cathedral':    RoomTemplateConfig.NG_PLUS_PLAGUE_THEME,
                            }
                            room_configs = room_config_map.get(ng_world,
                                           RoomTemplateConfig.NG_PLUS_THEME_CONFIG)
                            zone_data = None
                            for _, cfg in room_configs.items():
                                if cfg.get('floors', (1,2))[0] <= floor_num <= cfg.get('floors', (1,2))[1]:
                                    zone_data = cfg
                                    break
                            if zone_data and zone_data.get('templates'):
                                template = random.choice(zone_data['templates'])
                                name, desc, atmo = template.name, template.description, template.atmosphere
                            else:
                                name, desc, atmo = "Fractured Chamber", "Reality here is uncertain.", ""
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
                    except (json.JSONDecodeError, OSError, KeyError, TypeError):
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
        except OSError as e:
            logging.error(f"Delete save error: {e}", exc_info=True)
            print(f"✗ Delete failed: {e}")
    

    # ─────────────────────────────────────────────────────────────

    def _generate_ng_plus_dungeon(self, ng: int):
        """Generate the selected NG+ world dungeon."""
        weapon_scale  = max(1.0, getattr(self.player, 'ng_weapon_scale', 1.0))
        world_key     = getattr(self.player, 'ng_world', 'fractured_labyrinth')
        world_data    = GameConstants.NG_PLUS_WORLDS.get(world_key,
                        GameConstants.NG_PLUS_WORLDS['fractured_labyrinth'])
        world_name    = world_data['display_name']
        JOURNAL_FLOORS = {2: 'journal_1', 4: 'journal_2', 5: 'journal_3',
                          7: 'journal_4', 9: 'journal_5'}

        # Map world keys to their room template configs
        room_config_map = {
            'fractured_labyrinth': RoomTemplateConfig.NG_PLUS_THEME_CONFIG,
            'drowned_kingdom':     RoomTemplateConfig.NG_PLUS_DROWNED_THEME,
            'ashen_wastes':        RoomTemplateConfig.NG_PLUS_ASHEN_THEME,
            'mechanical_depths':   RoomTemplateConfig.NG_PLUS_MECHANICAL_THEME,
            'plague_cathedral':    RoomTemplateConfig.NG_PLUS_PLAGUE_THEME,
        }
        room_configs = room_config_map.get(world_key,
                       RoomTemplateConfig.NG_PLUS_THEME_CONFIG)

        total_rooms = 0
        self.floors = {}

        for floor_num in range(1, GameConstants.NUM_FLOORS + 1):
            print(f"Floor {floor_num}...", end=" ")
            rooms = {}

            start_id   = 'start' if floor_num == 1 else f"floor{floor_num}_start"
            start_name = f"{world_name} — Entry" if floor_num == 1 else f"{world_name} — Floor {floor_num}"
            start_desc = f"Adamus is here, somehow. He looks unsurprised." if floor_num == 1 else f"Deeper into {world_name}."
            rooms[start_id] = Room(
                start_name, start_desc, floor_num,
                ['health potion', 'old map'] if floor_num == 1 else ['health potion'],
                {}, [],
                "Adamus the Loyal has set up shop here. Use 'shop' to trade."
            )

            # Pick the right zone template pool for this floor
            zone_data = None
            for zone_key, zone_cfg in room_configs.items():
                floors_range = zone_cfg.get('floors', (1, 2))
                if floors_range[0] <= floor_num <= floors_range[1]:
                    zone_data = zone_cfg
                    break
            if not zone_data:
                zone_data = list(room_configs.values())[-1]

            enemies_pool = world_data['floor_themes'].get(floor_num,
                           list(world_data['enemies'].keys())[:3])

            templates = zone_data['templates']
            num_rooms = random.randint(
                GameConstants.MIN_ROOMS_PER_FLOOR - 2,
                GameConstants.MAX_ROOMS_PER_FLOOR - 2
            )
            selected  = random.sample(templates, min(num_rooms, len(templates)))

            THINNED   = {'health potion', 'energy drink', 'vitality tonic'}
            for i, tmpl in enumerate(selected):
                room_id      = f"floor{floor_num}_room{i+1}"
                room_enemies = self._get_unique_enemies(enemies_pool, tmpl.enemy_count)
                filtered     = [item for item in tmpl.items
                                if item not in THINNED or random.random() >= 0.45]
                rooms[room_id] = Room(
                    tmpl.name, tmpl.description, floor_num,
                    filtered, {}, room_enemies, tmpl.atmosphere
                )

            # Boss room
            boss_tmpl  = BossConfig.get_ng_plus_boss_room_template_for_world(floor_num, world_key)
            boss_cfg   = BossConfig.generate_ng_plus(floor_num, ng,
                                                      world_key=world_key,
                                                      weapon_scale=weapon_scale)
            boss_id    = f"floor{floor_num}_boss"
            rooms[boss_id] = Room(
                boss_tmpl.name, boss_tmpl.description, floor_num,
                ['ultimate health potion'], {},
                [boss_cfg['name']], boss_tmpl.atmosphere
            )

            if floor_num < GameConstants.NUM_FLOORS:
                stairs_id = f"floor{floor_num}_stairs"
                rooms[stairs_id] = Room(
                    f"{world_name} — Descent",
                    "Steps down into something worse.", floor_num
                )

            # Inject journal entry if this floor has one
            journal_key = JOURNAL_FLOORS.get(floor_num)
            if journal_key and journal_key not in self.player.unique_items_spawned:
                # Place in a non-boss, non-start room
                candidates = [r for r_id, r in rooms.items()
                              if 'boss' not in r_id and r_id != start_id]
                if candidates:
                    target_room = random.choice(candidates)
                    target_room.items.append(journal_key)
                    self.player.unique_items_spawned.add(journal_key)

            self._connect_rooms(rooms, start_id)
            self.floors[floor_num] = rooms
            total_rooms += len(rooms)
            print(f"{len(rooms)} rooms")

        for floor_num in range(1, GameConstants.NUM_FLOORS):
            stairs_id  = f"floor{floor_num}_stairs"
            next_start = f"floor{floor_num+1}_start"
            if stairs_id in self.floors[floor_num] and next_start in self.floors.get(floor_num+1, {}):
                self.floors[floor_num][stairs_id].exits['down'] = next_start
                self.floors[floor_num+1][next_start].exits['up'] = stairs_id

        logger.info(f"NG+ dungeon generated ({world_name}): {total_rooms} rooms")
        print(f"*** {world_name} is ready.")


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
            self.start_game()
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