"""
LABYRINTH — Item handler
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

