"""LABYRINTH — Weapon trait and material definitions"""
from __future__ import annotations
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class WeaponsData:
    """All weapon trait/material constants. Imported into GameConstants."""

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
            'desc': 'On hits dealing 40+ damage, erupts dealing +25 splash damage',
            'effect': 'splooge',
            'threshold': 40,
            'splash': 25,
        },
    }

    # ── Enemy Weaknesses ─────────────────────────────────────────
    # trait name → damage multiplier when that trait is on your weapon
