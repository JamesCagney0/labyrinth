"""LABYRINTH — Item definitions"""
from __future__ import annotations
import random, json, os, logging
from typing import Dict, List, Optional, Set, Tuple, Any, TYPE_CHECKING, Callable
from difflib import get_close_matches
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ItemsData:
    """All item-related constants. Imported into GameConstants."""

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
