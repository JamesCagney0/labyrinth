"""
LABYRINTH — Weapon systems
"""
from __future__ import annotations
import random, json, os, logging
from typing import Dict, List, Optional, Set, Tuple, Any, TYPE_CHECKING, Callable
from difflib import get_close_matches
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

from constants import GameConstants
if TYPE_CHECKING:
    from player import Player

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
        paladin_pool = [
            w('Holy Mace',         20, 'melee', 'holy'),
            w('Blessed Sword',     19, 'melee', 'holy'),
            w('Sacred Hammer',     22, 'melee', 'shielded'),
            w('Crusader Blade',    21, 'melee', 'holy'),
            w('Divine Spear',      18, 'melee', 'precise'),
            w('Morning Star',      23, 'melee', 'heavy'),
            w('Radiant Axe',       20, 'melee', 'holy'),
            w('Silver Longsword',  19, 'melee', 'silver'),
            w('Consecrated Club',  21, 'melee', 'holy'),
            w('Templar Sword',     20, 'melee', 'shielded'),
            w('Warhammer',         24, 'melee', 'heavy'),
            w('Faith Brand',       18, 'melee', 'holy'),
        ]
        berserker_pool = [
            w('Greataxe',          26, 'melee', 'berserker'),
            w('Battle Maul',       25, 'melee', 'savage'),
            w('Skull Crusher',     27, 'melee', 'berserker'),
            w('Iron Flail',        24, 'melee', 'bleeding'),
            w('Raging Cleaver',    25, 'melee', 'berserker'),
            w('War Hammer',        26, 'melee', 'heavy'),
            w('Bone Breaker',      24, 'melee', 'savage'),
            w('Serrated Greataxe', 27, 'melee', 'bleeding'),
            w('Fury Blade',        25, 'melee', 'berserker'),
            w('Chaos Maul',        28, 'melee', 'cursed'),
            w('Bloodlust Axe',     26, 'melee', 'vampiric'),
            w('Titan Club',        29, 'melee', 'berserker'),
        ]
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
        random.shuffle(paladin_pool)
        random.shuffle(berserker_pool)
        random.shuffle(void_pool)
        return {
            'warrior':     warrior_pool[:8],
            'mage':        mage_pool[:8],
            'rogue':       rogue_pool[:8],
            'paladin':     paladin_pool[:8],
            'berserker':   berserker_pool[:8],
            'void_walker': void_pool[:8],
        }

#################################################################################
# COMBAT SYSTEM
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

