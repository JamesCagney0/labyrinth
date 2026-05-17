"""
LABYRINTH — Static game data
GameConstants, RoomTemplate, RoomTemplateConfig, BossConfig
"""
from __future__ import annotations
import random, json, os, logging
from typing import Dict, List, Optional, Set, Tuple, Any, TYPE_CHECKING, Callable
from difflib import get_close_matches
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class GameConstants:
    """Central configuration class containing all game constants"""
    VERSION = "7.6.5"
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

    # Standalone — never enters the random room pool.
    # Injected once per run on a random floor between 3 and 7.
    FORGOTTEN_GAME_ROOM = RoomTemplate(
        "Forgotten Game Room",
        "A small side chamber, barely large enough for five people.\n"
        "An overturned table sits against one wall, surrounded by collapsed stools.\n\n"
        "Scattered across the floor: hand-drawn maps on yellowed parchment — though several\n"
        "have large sections crossed out and marked 'CHANGES,' suggesting whoever drew them\n"
        "knew better than to trust them completely.\n\n"
        "Scraps of paper covered in notes and numbers, and what looks like a character sheet\n"
        "for someone called 'Argentum.'\n\n"
        "At the top of the sheet, in careful handwriting: 'Welventier Campaign — Session 7.'\n"
        "Below that, a note in different handwriting:\n\n"
        "  'Living dungeon. Materials unlike anything topside.\n"
        "   People come from near and far to Welventier for what the dungeon produces —\n"
        "   resources and creatures it generates seemingly from nothing.\n"
        "   Parts of it shift and change so maps aren't worth the parchment they're drawn on.\n"
        "   Other parts never change. A few have been called safe.\n"
        "   They are not safe. Nothing in here is truly safe.\n\n"
        "   Warp to F3 on entry — skip the first two floors entirely.\n"
        "   Do NOT trust any map past the third corridor.\n\n"
        "   Time reminder: days in here can be hours outside.\n"
        "   If any of us are gone more than a few real-time days, don't come looking.'\n\n"
        "Whatever they were doing here, they left in a hurry.\n\n"
        "In the center of the room, on a small stone pedestal untouched by the chaos,\n"
        "a single twenty-sided die sits perfectly balanced.\n\n"
        "Someone carved four words into the pedestal beneath it:\n\n"
        "  'They never came back.'",
        "Dust motes drift through a crack of light from above.\n\n"
        "A faded note pinned to the wall reads:\n\n"
        "  'Time check — 3 days inside, 2 hours outside.\n"
        "   If we're not out by real-time sundown, assume the worst.'\n\n"
        "The silence here feels different — not threatening. Just sad.",
        ["gambler's d20"], 0, 'easter_egg'
    )

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
                'Gladius of Victory', 'Iron Arena Sword', "Champions Cleaver",
                'Battle-Worn Blade', "Warriors Greatsword",
                "Vanguards Edge", 'Arena Master Sword', "Conquerors Blade",
                "Champions Fury", 'Undying Legend',
            ],
            'mage': [
                "Champions Scepter", 'Arena Orb', 'Battle-Mage Crystal',
                'Combat Staff', "Gladiators Wand",
                "Conquerors Staff", "Vanquishers Tome", 'Master Orb',
                'Fury Scepter', 'Undying Focus',
            ],
            'rogue': [
                'Twin Blades of Honor', 'Arena Knives', "Champions Shiv",
                'Battle-Worn Rapier', 'Iron Short Bow',
                "Conquerors Dagger", "Vanquishers Needle", "Vanguards Claw",
                "Champions Twin Fangs", 'Undying Edge',
            ],
            'paladin': [
                'Holy Champions Mace', 'Sacred Arena Hammer', 'Divine Gladius',
                'Blessed Combat Spear', 'Radiant Crusader Blade',
                'Champions Holy Sword', 'Consecrated Warblade', 'Paladins Arena Mace',
                'Sanctified Hammer', 'Undying Light',
            ],
            'berserker': [
                'Rage Champions Axe', 'Fury Arena Maul', 'Bloodlust Cleaver',
                'Berserkers Trophy', 'Savage Warblade',
                'Carnage Axe', 'Champions Fury Maul', 'Berserk Champions Cleaver',
                'Titan Rage Axe', 'Undying Fury',
            ],
            'void_walker': [
                'Phase Champions Edge', 'Void Arena Blade', 'Null Gladius',
                'Shadow Champions Claw', 'Phase Rapier',
                'Void Champions Fang', 'Null Edge', 'Phase Champions Needle',
                'Void Stalkers Blade', 'Undying Void',
            ],
        },
        2: {  # Necromancer Lord
            'warrior': [
                'Soul Reaper', 'Bone Cleaver', 'Undead Slayer',
                'Crypt Breaker', 'Death Hammer',
                'Soul Crusher', "Necromancers Blade", 'Void Sword',
                'Death Bringer', 'Soul Annihilator',
            ],
            'mage': [
                'Death Staff', 'Bone Wand', 'Cursed Tome',
                'Shadow Orb', 'Undead Crystal',
                'Soul Staff', "Lichs Scepter", 'Void Wand',
                "Deaths Instrument", 'Soul Obliterator',
            ],
            'rogue': [
                'Shadow Fang', 'Bone Shiv', "Deaths Needle",
                'Cursed Rapier', 'Undead Bow',
                'Soul Dagger', "Lichs Claw", 'Void Edge',
                "Deaths Kiss", 'Soul Ripper',
            ],
        
            'paladin': [
                'Holy Champions Mace', 'Sacred Arena Hammer', 'Divine Gladius', 'Blessed Combat Spear', 'Radiant Crusader Blade', 'Champions Holy Sword', 'Consecrated Warblade', 'Paladins Arena Mace', 'Sanctified Hammer', 'Undying Light',
            ],
            'berserker': [
                'Rage Champions Axe', 'Fury Arena Maul', 'Bloodlust Cleaver', 'Berserkers Trophy', 'Savage Warblade', 'Carnage Axe', 'Champions Fury Maul', 'Berserk Champions Cleaver', 'Titan Rage Axe', 'Undying Fury',
            ],
            'void_walker': [
                'Phase Champions Edge', 'Void Arena Blade', 'Null Gladius', 'Shadow Champions Claw', 'Phase Rapier', 'Void Champions Fang', 'Null Edge', 'Phase Champions Needle', 'Void Stalkers Blade', 'Undying Void',
            ],
        },
        3: {  # Crypt Overlord
            'warrior': [
                'Bone Crusher', 'Crypt Hammer', 'Tomb Breaker',
                'Ancient Grave Axe', 'Burial Sword',
                "Overlords Blade", 'Crypt Master Sword', 'Eternal Bone Axe',
                'Soul Cleaver', "Overlords Reckoning",
            ],
            'mage': [
                'Crypt Scepter', 'Ossuary Wand', 'Tomb Crystal',
                'Ancient Bone Staff', 'Burial Orb',
                "Overlords Tome", 'Crypt Master Staff', 'Eternal Bone Wand',
                'Soul Scepter', "Overlords Devastation",
            ],
            'rogue': [
                'Grave Shiv', 'Crypt Needle', 'Tomb Dagger',
                'Ancient Bone Rapier', 'Burial Blade',
                "Overlords Claw", 'Crypt Master Bow', 'Eternal Bone Shiv',
                "Overlords Doom", 'Grave of Eternity',
            ],
        
            'paladin': [
                'Holy Bone Breaker', 'Sacred Death Ward', 'Divine Undead Slayer', 'Blessed Soul Hammer', 'Radiant Crypt Mace', 'Paladins Soul Crusher', 'Sanctified Bone Hammer', 'Holy Death Warden', 'Divine Soul Mace', 'Sacred Obliterator',
            ],
            'berserker': [
                'Rage Soul Reaper', 'Fury Bone Cleaver', 'Berserk Death Hammer', 'Carnage Crypt Axe', 'Savage Soul Crusher', 'Undead Fury Maul', 'Berserkers Death Axe', 'Skull Cleaver', 'Fury Death Bringer', 'Undying Rage',
            ],
            'void_walker': [
                'Void Soul Needle', 'Phase Death Blade', 'Null Bone Shiv', 'Shadow Soul Claw', 'Void Death Fang', 'Phase Lichs Edge', 'Null Death Piercer', 'Void Reapers Claw', 'Shadow Undead Blade', 'Undying Phase',
            ],
        },
        4: {  # Shadow King
            'warrior': [
                'Shadowbane', 'Dark Greatsword', 'Umbra Blade',
                'Shade Axe', 'Night Hammer',
                "Shadow Kings Edge", 'Umbra Cleaver', 'Darkness Blade',
                "Shadows Reckoning", "Nights End",
            ],
            'mage': [
                'Dark Orb', 'Shadow Staff', 'Umbra Crystal',
                'Shade Tome', 'Night Wand',
                "Shadow Kings Scepter", 'Umbra Staff', 'Darkness Orb',
                "Shadows Devastation", "Nights Obliteration",
            ],
            'rogue': [
                'Night Piercer', 'Shadow Needle', 'Umbra Dagger',
                'Shade Rapier', 'Dark Bow',
                "Shadow Kings Claw", 'Umbra Shiv', 'Darkness Blade',
                "Shadows Doom", "Nights Annihilation",
            ],
        
            'paladin': [
                'Holy Crypt Warden', 'Sacred Tomb Hammer', 'Divine Grave Mace', 'Blessed Undead Bane', 'Radiant Crypt Sword', 'Paladins Tomb Mace', 'Sanctified Grave Hammer', 'Holy Overlord Blade', 'Divine Crypt Warden', 'Sacred Annihilator',
            ],
            'berserker': [
                'Rage Tomb Crusher', 'Fury Crypt Maul', 'Berserk Grave Axe', 'Carnage Tomb Hammer', 'Savage Crypt Blade', 'Fury Grave Crusher', 'Berserkers Tomb Axe', 'Rage Bone Maul', 'Overlords Fury', 'Undying Carnage',
            ],
            'void_walker': [
                'Void Crypt Edge', 'Phase Tomb Blade', 'Null Grave Shiv', 'Shadow Tomb Needle', 'Void Overlords Fang', 'Phase Crypt Claw', 'Null Grave Piercer', 'Void Tomb Blade', 'Shadow Crypt Edge', 'Undying Phase',
            ],
        },
        5: {  # Flame Lord
            'warrior': [
                'Flamebringer', 'Ember Sword', 'Inferno Axe',
                'Magma Hammer', 'Cinder Blade',
                "Flame Kings Edge", 'Pyre Cleaver', 'Inferno Greatsword',
                "Solar Reckoning", "Flames Annihilation",
            ],
            'mage': [
                'Inferno Staff', 'Ember Wand', 'Magma Crystal',
                'Cinder Tome', 'Pyre Orb',
                "Flame Kings Scepter", 'Pyroclastic Staff', 'Inferno Wand',
                'Solar Devastation', "Flames Obliteration",
            ],
            'rogue': [
                'Cinder Bow', 'Ember Shiv', 'Inferno Needle',
                'Magma Dagger', 'Pyre Rapier',
                "Flame Kings Claw", 'Pyroclastic Shiv', 'Inferno Dagger',
                'Solar Doom', "Flames End",
            ],
        
            'paladin': [
                'Holy Shadow Ward', 'Sacred Light Hammer', 'Divine Shadow Bane', 'Blessed Kings Mace', 'Radiant Shadow Sword', 'Paladins Shadow Ward', 'Sanctified Kings Hammer', 'Holy Shadow Blade', 'Divine Kings Mace', 'Sacred Shadow Annihilator',
            ],
            'berserker': [
                'Rage Shadow Axe', 'Fury Kings Maul', 'Berserk Shadow Hammer', 'Carnage Kings Axe', 'Savage Shadow Blade', 'Fury Shadow Crusher', 'Berserkers Shadow Maul', 'Rage Kings Axe', 'Shadow Fury Blade', 'Undying Shadow Rage',
            ],
            'void_walker': [
                'Void Shadow Needle', 'Phase Kings Blade', 'Null Shadow Shiv', 'Shadow Kings Claw', 'Void Kings Fang', 'Phase Shadow Edge', 'Null Kings Piercer', 'Void Shadow Blade', 'Phase Kings Claw', 'Undying Shadow Void',
            ],
        },
        6: {  # Frost Titan
            'warrior': [
                'Frostbane Greatsword', 'Glacial Axe', 'Ice Hammer',
                'Frozen Blade', 'Tundra Sword',
                "Frost Giants Edge", 'Eternal Ice Greatsword', 'Blizzard Axe',
                'Absolute Zero Blade', "Winters End",
            ],
            'mage': [
                'Staff of Eternal Winter', 'Glacier Wand', 'Frozen Crystal',
                'Blizzard Tome', 'Tundra Orb',
                "Frost Giants Scepter", 'Eternal Ice Staff', 'Permafrost Wand',
                'Absolute Zero Staff', "Winters Obliteration",
            ],
            'rogue': [
                'Icicle Piercer', 'Frozen Shiv', 'Glacier Needle',
                'Blizzard Dagger', 'Tundra Bow',
                "Frost Giants Claw", 'Eternal Ice Rapier', 'Permafrost Shiv',
                'Absolute Zero Edge', "Winters Doom",
            ],
        
            'paladin': [
                'Holy Flame Ward', 'Sacred Ember Hammer', 'Divine Flame Mace', 'Blessed Ember Sword', 'Radiant Flame Warden', 'Paladins Ember Mace', 'Sanctified Flame Hammer', 'Holy Ember Blade', 'Divine Flame Warden', 'Sacred Ember Annihilator',
            ],
            'berserker': [
                'Rage Ember Axe', 'Fury Flame Maul', 'Berserk Ember Hammer', 'Carnage Flame Axe', 'Savage Ember Blade', 'Fury Flame Crusher', 'Berserkers Ember Maul', 'Rage Flame Axe', 'Ember Fury Blade', 'Undying Flame Rage',
            ],
            'void_walker': [
                'Void Flame Needle', 'Phase Ember Blade', 'Null Flame Shiv', 'Shadow Ember Claw', 'Void Flame Fang', 'Phase Ember Edge', 'Null Flame Piercer', 'Void Ember Blade', 'Phase Flame Claw', 'Undying Flame Void',
            ],
        },
        7: {  # Demon Prince
            'warrior': [
                "Demons Edge", 'Hellfire Sword', 'Abyssal Axe',
                'Infernal Hammer', 'Brimstone Blade',
                "Demon Princes Greatsword", 'Hellgate Cleaver', 'Abyssal Greatsword',
                'Damnation Blade', "Hells Reckoning",
            ],
            'mage': [
                'Abyssal Staff', 'Hellfire Wand', 'Demon Crystal',
                'Infernal Tome', 'Brimstone Orb',
                "Demon Princes Scepter", 'Hellgate Staff', 'Abyssal Wand',
                'Damnation Staff', "Hells Obliteration",
            ],
            'rogue': [
                'Soul Piercer', 'Hellfire Shiv', 'Abyssal Needle',
                'Infernal Dagger', 'Brimstone Bow',
                "Demon Princes Claw", 'Hellgate Rapier', 'Abyssal Shiv',
                'Damnation Edge', "Hells Doom",
            ],
        
            'paladin': [
                'Holy Frost Ward', 'Sacred Ice Hammer', 'Divine Frost Mace', 'Blessed Glacier Sword', 'Radiant Frost Warden', 'Paladins Glacier Mace', 'Sanctified Ice Hammer', 'Holy Frost Blade', 'Divine Glacier Warden', 'Sacred Ice Annihilator',
            ],
            'berserker': [
                'Rage Glacier Axe', 'Fury Frost Maul', 'Berserk Ice Hammer', 'Carnage Frost Axe', 'Savage Glacier Blade', 'Fury Frost Crusher', 'Berserkers Ice Maul', 'Rage Frost Axe', 'Glacier Fury Blade', 'Undying Frost Rage',
            ],
            'void_walker': [
                'Void Frost Needle', 'Phase Ice Blade', 'Null Frost Shiv', 'Shadow Ice Claw', 'Void Glacier Fang', 'Phase Frost Edge', 'Null Ice Piercer', 'Void Frost Blade', 'Phase Glacier Claw', 'Undying Frost Void',
            ],
        },
        8: {  # Void Archon
            'warrior': [
                'Voidreaver', 'Reality Sword', 'Entropy Axe',
                'Oblivion Hammer', 'Nihilum Blade',
                "Void Archons Greatsword", 'Reality Render', 'Entropy Cleaver',
                'Universe Ender', 'The Final Void',
            ],
            'mage': [
                'Reality Staff', 'Void Wand', 'Entropy Crystal',
                'Oblivion Tome', 'Nihilum Orb',
                "Void Archons Scepter", 'Reality Warper', 'Entropy Staff',
                'Universe Obliterator', 'The Final Void Staff',
            ],
            'rogue': [
                'Oblivion Blade', 'Void Shiv', 'Entropy Needle',
                'Reality Dagger', 'Nihilum Bow',
                "Void Archons Claw", 'Reality Ripper', 'Entropy Rapier',
                'Universe Destroyer', 'The Final Void Edge',
            ],
        
            'paladin': [
                'Holy Demon Bane', 'Sacred Exorcist Hammer', 'Divine Demon Ward', 'Blessed Purifier Sword', 'Radiant Exorcist Mace', 'Paladins Demon Bane', 'Sanctified Purifier', 'Holy Demon Ward', 'Divine Exorcist Hammer', 'Sacred Annihilator',
            ],
            'berserker': [
                'Rage Demon Axe', 'Fury Demon Maul', 'Berserk Princes Hammer', 'Carnage Demon Axe', 'Savage Prince Blade', 'Fury Demon Crusher', 'Berserkers Demon Maul', 'Rage Princes Axe', 'Demon Fury Blade', 'Undying Demon Rage',
            ],
            'void_walker': [
                'Void Demon Needle', 'Phase Prince Blade', 'Null Demon Shiv', 'Shadow Demon Claw', 'Void Prince Fang', 'Phase Demon Edge', 'Null Prince Piercer', 'Void Demon Blade', 'Phase Prince Claw', 'Undying Demon Void',
            ],
        },
        9: {  # Primordial Beast
            'warrior': [
                'Titan Slayer', 'Primordial Axe', 'Ancient Fang Sword',
                'Primal Hammer', 'Elder Blade',
                "Beast Kings Greatsword", 'Primordial Reckoner', 'Ancient Wrath Axe',
                "Titans End", 'The Primordial Annihilator',
            ],
            'mage': [
                'Primordial Staff', 'Ancient Wand', 'Titan Crystal',
                'Primal Tome', 'Elder Orb',
                "Beast Kings Scepter", 'Primordial Power Staff', 'Ancient Wrath Wand',
                "Titans Devastation", 'The Primordial Obliterator',
            ],
            'rogue': [
                'Beast Fang', 'Primordial Shiv', 'Ancient Claw Dagger',
                'Primal Bow', 'Elder Rapier',
                "Beast Kings Needle", 'Primordial Render', 'Ancient Wrath Shiv',
                "Titans Doom", 'The Primordial Destroyer',
            ],
        
            'paladin': [
                'Holy Void Ward', 'Sacred Null Hammer', 'Divine Void Bane', 'Blessed Archon Sword', 'Radiant Void Warden', 'Paladins Archon Mace', 'Sanctified Void Hammer', 'Holy Null Blade', 'Divine Void Warden', 'Sacred Void Annihilator',
            ],
            'berserker': [
                'Rage Void Axe', 'Fury Archon Maul', 'Berserk Void Hammer', 'Carnage Archon Axe', 'Savage Void Blade', 'Fury Archon Crusher', 'Berserkers Void Maul', 'Rage Archon Axe', 'Void Fury Blade', 'Undying Void Rage',
            ],
            'void_walker': [
                'Void Archons Needle', 'Phase Archon Blade', 'Null Archon Shiv', 'Shadow Archon Claw', 'Void Archon Fang', 'Phase Archon Edge', 'Null Archon Piercer', 'True Void Blade', 'Phase Archon Claw', 'Undying Archon Void',
            ],
        },
        10: {  # Reality Breaker
            'warrior': [
                'Worldender', 'Cosmos Blade', 'Universe Axe',
                'Reality Hammer', 'Eternal Sword',
                "Reality Breakers Greatsword", 'Cosmos Render', 'Universe Cleaver',
                'The Absolute End', 'Oblivion Incarnate',
            ],
            'mage': [
                'Cosmos Staff', 'Universe Wand', 'Reality Crystal',
                'Eternal Tome', 'Worldend Orb',
                "Reality Breakers Scepter", 'Cosmos Power Staff', 'Universe Warper',
                'The Absolute Obliteration', "Oblivions Voice",
            ],
            'rogue': [
                'Reality Ripper', 'Cosmos Edge', 'Universe Shiv',
                'Eternal Bow', 'Worldend Dagger',
                "Reality Breakers Claw", 'Cosmos Render Blade', 'Universe Destroyer Shiv',
                'The Absolute Doom', "Oblivions Touch",
            ],
            'paladin': [
                'Holy Reality Ward', 'Sacred Cosmos Hammer', 'Divine Universe Mace',
                'Blessed Eternal Sword', 'Radiant Cosmos Warden', 'Paladins Reality Mace',
                'Sanctified Universe Hammer', 'Holy Cosmos Blade', 'Divine Eternal Warden',
                'Sacred Reality Annihilator',
            ],
            'berserker': [
                'Rage Reality Axe', 'Fury Cosmos Maul', 'Berserk Universe Hammer',
                'Carnage Eternal Axe', 'Savage Reality Blade', 'Fury Cosmos Crusher',
                'Berserkers Reality Maul', 'Rage Universe Axe', 'Reality Fury Blade',
                'Undying Reality Rage',
            ],
            'void_walker': [
                'Void Reality Needle', 'Phase Cosmos Blade', 'Null Universe Shiv',
                'Shadow Eternal Claw', 'Void Reality Fang', 'Phase Cosmos Edge',
                'Null Universe Piercer', 'Void Reality Blade', 'Phase Cosmos Claw',
                'Undying Reality Void',
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
        2: ("Necromancers Sanctum", "Dark energy swirls around an obsidian throne.",
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
        cls_key = player.character_class
        # Fused classes fall back to the first parent's weapon pool
        if cls_key not in cls.BOSS_WEAPON_POOLS.get(floor, {}):
            parents = getattr(player, 'fusion_parents', None)
            if parents:
                cls_key = next((p for p in parents if p in cls.BOSS_WEAPON_POOLS.get(floor, {})), 'warrior')
            else:
                cls_key = 'warrior'
        pool = cls.BOSS_WEAPON_POOLS[floor][cls_key]
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

