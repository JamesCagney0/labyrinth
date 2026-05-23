"""
LABYRINTH — Player class
"""
from __future__ import annotations
import random, logging
from typing import Dict, List, Optional, Set
from collections import Counter

logger = logging.getLogger(__name__)

from constants import GameConstants
from utils import safe_input

class Player:
    """Player character with stats and inventory"""
    
    def __init__(self, name: str, character_class: str = "warrior"):
        self.name = name
        self.character_class = character_class
        self.class_tier = 1
        self.level = 1
        self.experience = 0
        self.experience_to_next = GameConstants.BASE_EXPERIENCE_NEEDED
        
        config = GameConstants.CLASSES.get(character_class) or GameConstants.CLASSES['warrior']
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
        self.shop_visits:         int = 0
        self.status_effects:      Dict[str, int] = {}  # name → turns remaining
        self.fight_damage_taken:  int   = 0    # total damage taken this fight (berserker's draught)
        self.combat_boost_turns:  int   = 0    # turns of battle tincture active
        self.combat_boost_mult:   float = 1.0  # active damage boost multiplier
        self.void_absorb_active:  bool  = False  # void tonic: absorb next hit → MP
    
    def _base_class_config(self) -> dict:
        """Return the CLASSES config entry for this character, fusion-safe.

        Fusion classes (e.g. 'shadow_knight') are not in GameConstants.CLASSES.
        For those, we return a synthesised config that averages both parents so
        that level-up stat growth and HP scaling remain consistent.  Weapon type
        falls back to the first parent's weapon type.
        """
        if self.character_class in GameConstants.CLASSES:
            return GameConstants.CLASSES[self.character_class]

        # Fusion class — average both parents
        parents = getattr(self, 'fusion_parents', None)
        p1_key = parents[0] if parents else 'warrior'
        p2_key = parents[1] if parents and len(parents) > 1 else p1_key
        c1 = GameConstants.CLASSES.get(p1_key, GameConstants.CLASSES['warrior'])
        c2 = GameConstants.CLASSES.get(p2_key, GameConstants.CLASSES['warrior'])

        avg_growth = {}
        for stat in c1['stat_growth']:
            avg_growth[stat] = (c1['stat_growth'].get(stat, 0) + c2['stat_growth'].get(stat, 0)) // 2

        return {
            'base_health':      (c1['base_health']      + c2['base_health'])      // 2,
            'base_mana':        (c1['base_mana']         + c2['base_mana'])        // 2,
            'health_per_level': (c1['health_per_level']  + c2['health_per_level']) // 2,
            'inventory_slots':  max(c1['inventory_slots'], c2['inventory_slots']),
            'weapon_types':     c1['weapon_types'],   # first parent's weapon type
            'stat_growth':      avg_growth,
            'base_stats':       c1['base_stats'],     # used only in migration, safe fallback
        }

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
        
        config = self._base_class_config()
        old_max_inv = self.max_inventory
        
        self.max_inventory = config['inventory_slots'] + (self.level - 1) * GameConstants.INVENTORY_SLOTS_PER_LEVEL + (self.class_tier - 1) * GameConstants.INVENTORY_SLOTS_PER_TIER
        
        growth = config['stat_growth']
        for stat, bonus in growth.items():
            self.stats[stat] += bonus
        
        health_gain = config['health_per_level']
        self.max_health += health_gain
        self.health = self.max_health

        is_mage   = self.character_class == 'mage'
        is_paladin = self.character_class == 'paladin'
        if is_mage:
            self.max_mana += GameConstants.MANA_PER_LEVEL
            self.mana = self.max_mana
        elif is_paladin:
            self.mana = min(self.mana + 10, self.max_mana)  # Paladin regens 10 MP on level up

        logger.info(f"LEVEL UP: {self.name} reached level {self.level}. HP: {self.max_health}" + (f", MP: {self.max_mana}" if is_mage else ""))

        luck_gain  = config['stat_growth'].get('luck', 0)
        vit_gain   = config['stat_growth'].get('vitality', 0)
        faith_gain = config['stat_growth'].get('faith', 0)

        print(f"\n*** LEVEL UP! Now level {self.level}!")
        mana_str = f" | Mana +{GameConstants.MANA_PER_LEVEL} (now {self.max_mana})" if is_mage else \
                   f" | MP +10 (now {self.mana}/{self.max_mana})" if is_paladin else ""
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

    def can_upgrade_fusion(self) -> bool:
        """Fusion tier upgrade — available up to tier 10."""
        if not getattr(self, 'fusion_parents', None):
            return False
        if self.class_tier >= 10:
            return False
        required = GameConstants.FUSION_UPGRADE_LEVELS.get(self.class_tier + 1, 999)
        return self.level >= required

    def upgrade_fusion(self) -> bool:
        """Advance a fused class from tier 5–9 to the next tier (max 10)."""
        if not self.can_upgrade_fusion():
            return False
        self.class_tier += 1
        bonus = GameConstants.FUSION_TIER_STAT_BONUS
        # Distribute bonus evenly across primary stats
        for stat in ['strength', 'intelligence', 'agility', 'luck', 'vitality']:
            self.stats[stat] = self.stats.get(stat, 0) + bonus
        self.max_health += 20  # +20 max HP per fusion tier
        self.health = min(self.health + 20, self.max_health)
        return True

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
            if not fusion:
                return self.character_class.replace('_', ' ').title()
            base_name = fusion['name'].lower()
            tier_names = GameConstants.FUSION_CLASS_NAMES.get(base_name, {})
            return tier_names.get(self.class_tier, fusion['name'])
        tier_names = GameConstants.CLASS_NAMES.get(self.class_tier, {})
        return tier_names.get(self.character_class, self.character_class.replace('_', ' ').title())


    def upgrade_class(self) -> bool:
        """Upgrade class tier"""
        if not self.can_upgrade_class():
            return False
        
        old_tier = self.class_tier
        self.class_tier += 1
        self.rarity_boost += GameConstants.RARITY_BOOST_PER_TIER
        
        config = self._base_class_config()
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

        is_mage    = self.character_class == 'mage'
        is_paladin = self.character_class == 'paladin'
        if is_mage:
            self.max_mana = config['base_mana'] + (self.class_tier - 1) * 25 + (self.level - 1) * GameConstants.MANA_PER_LEVEL
            self.mana = self.max_mana
        elif is_paladin:
            self.mana = self.max_mana  # restore to full on tier upgrade

        logger.info(f"CLASS UPGRADE: {self.name} advanced from tier {old_tier} to {self.class_tier} ({self.get_class_title()})")

        title = self.get_class_title()
        article = "an" if title[0].lower() in "aeiou" else "a"
        print(f"\n*** CLASS UPGRADE! Now {article} {title}! (Tier {self.class_tier}/5)")
        hp_gain = self.max_health - old_health
        if is_mage:
            mana_gain = self.max_mana - old_mana
            print(f"All stats +5 | Health +{hp_gain} | Mana +{mana_gain}")
        elif is_paladin:
            print(f"All stats +5 | Health +{hp_gain} | MP restored to {self.max_mana}")
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
        """Store weapon in dedicated weapon slots (separate from item inventory)"""
        max_ws = getattr(self, 'max_weapon_slots', GameConstants.MAX_WEAPON_SLOTS)
        if len(self.inventory_weapons) >= max_ws:
            print(f"Weapon slots full! ({max_ws} max — sell or discard a weapon first)")
            return False
        self.inventory_weapons.append(weapon)
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
                choice = int(safe_input("\nSwap to: ")) - 1
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
            self.inventory_weapons.remove(target)
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
                name = td.get('name', t)
                desc = td.get('desc', '')
                # Cursed weapons also contribute a damage multiplier to the preview
                if td.get('effect') == 'cursed':
                    trait_mults.append(1 + td.get('damage_bonus', 0))
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

        max_ws = getattr(self, 'max_weapon_slots', GameConstants.MAX_WEAPON_SLOTS)
        print(f"\n  Inventory: {len(self.inventory)}/{self.max_inventory} "
              f"| Weapons: {len(self.inventory_weapons)}/{max_ws} "
              f"| Floor: {self.current_floor}/{GameConstants.NUM_FLOORS}")
        print(f"Bosses: {len(self.bosses_defeated)}/{GameConstants.NUM_FLOORS}")
        
        if self.wearables:
            stat_labels = {'strength':'STR','intelligence':'INT','agility':'AGI',
                          'luck':'LCK','vitality':'VIT','faith':'FTH','arcane':'ARC'}
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
            'mana': self.mana, 'max_mana': self.max_mana, 'inventory': [i for i in self.inventory if not i.startswith('WEAPON:')],
            'inventory_weapons': self.inventory_weapons, 'weapon': self.weapon, 'wearables': self.wearables,
            'max_inventory': self.max_inventory, 'current_floor': self.current_floor,
            'current_room': self.current_room, 'visited_rooms': list(self.visited_rooms),
            'bosses_defeated': self.bosses_defeated, 'rarity_boost': self.rarity_boost,
            'gold_coins': self.gold_coins, 'secret_room_unlocked': self.secret_room_unlocked,
            'special_items': self.special_items, 'unique_items_spawned': list(self.unique_items_spawned),
            'ng_plus': getattr(self, 'ng_plus', 0),
            'ng_world': getattr(self, 'ng_world', 'fractured_labyrinth'),
            'ng_world_queue': getattr(self, 'ng_world_queue', []),
            'item_hints_shown':   list(getattr(self, 'item_hints_shown', set())),
            'shop_visits':        getattr(self, 'shop_visits', 0),
            'save_version':       getattr(self, 'save_version', '7.6.5'),
            'status_effects':     getattr(self, 'status_effects', {}),
            'fusion_parents': list(getattr(self, 'fusion_parents', None) or []),
            'ng_weapon_scale': getattr(self, 'ng_weapon_scale', 1.0),
            'total_gold_earned': getattr(self, 'total_gold_earned', 0)
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Player':
        """Deserialize from save, migrating old saves to current version."""
        # Fusion classes (e.g. 'shadow_knight') are not in GameConstants.CLASSES so
        # __init__ can't resolve their config.  We construct with the first fusion
        # parent instead — all attributes are overwritten by the loop below anyway.
        saved_class = data['character_class']
        if saved_class not in GameConstants.CLASSES:
            fp = data.get('fusion_parents') or []
            init_class = fp[0] if fp and fp[0] in GameConstants.CLASSES else 'warrior'
        else:
            init_class = saved_class
        player = cls(data['name'], init_class)
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
        if not hasattr(player, 'ng_world_queue'):
            player.ng_world_queue = []   # old saves start fresh — queue builds on next NG+
        if not hasattr(player, 'shop_visits'):
            player.shop_visits = 1
        if not hasattr(player, 'max_weapon_slots'):
            player.max_weapon_slots = GameConstants.MAX_WEAPON_SLOTS
        # Migrate legacy WEAPON: labels — reconstruct any weapons that were
        # stored as labels but are missing from inventory_weapons
        legacy_labels = [i for i in player.inventory if i.startswith('WEAPON:')]
        if legacy_labels:
            existing_names = {w['name'] for w in player.inventory_weapons}
            for label in legacy_labels:
                wname = label[8:]
                if wname not in existing_names:
                    player.inventory_weapons.append({
                        'name': wname, 'damage': 0, 'rarity': 'common',
                        'type': 'melee', 'traits': [],
                    })
        # Strip the labels
        player.inventory = [i for i in player.inventory if not i.startswith('WEAPON:')]
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
        """Backfill stats and fix exploits from pre-7.7.0 saves."""
        config  = GameConstants.CLASSES.get(self.character_class, {})
        base    = config.get('base_stats', {})
        growth  = config.get('stat_growth', {})
        levels  = max(0, self.level - 1)
        migrated = []

        # ── Backfill any legitimately missing stat ───────────────────
        for stat, base_val in base.items():
            if stat not in self.stats:
                earned = base_val + growth.get(stat, 0) * levels
                self.stats[stat] = earned
                migrated.append(f"{stat.capitalize()} added → {earned}")

        # ── Add trait to equipped weapon if it has none ──────────────
        def _assign_trait(weapon):
            if weapon and not weapon.get('traits'):
                wtype = weapon.get('type', 'melee')
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

        # ── v7.7.0 migration ─────────────────────────────────────────
        save_ver = getattr(self, 'save_version', '0.0.0')
        if save_ver < '7.7.0':

            # Step 1: Enforce wearable stack cap retroactively
            # Cap: L<5=1, L<10=2, L<15=3, L15+=4 per item type
            lvl = self.level
            max_stack = GameConstants.get_wearable_stack_cap(lvl)
            from collections import Counter
            wearable_counts = Counter(w['item'] for w in self.wearables
                                      if not GameConstants.WEARABLE_ITEMS.get(w['item'], {}).get('cursed'))
            capped_wearables = []
            seen_counts = Counter()
            for w in self.wearables:
                item_name = w['item']
                is_cursed = GameConstants.WEARABLE_ITEMS.get(item_name, {}).get('cursed', False)
                if is_cursed:
                    capped_wearables.append(w)  # cursed items: no cap
                elif seen_counts[item_name] < max_stack:
                    capped_wearables.append(w)
                    seen_counts[item_name] += 1
                else:
                    migrated.append(f"Removed excess {item_name} (cap: {max_stack})")

            self.wearables = capped_wearables

            # Step 2: Recalculate stats from scratch using correct baseline
            # base + tier bonus + level growth (clean slate)
            tier_bonus = (self.class_tier - 1) * 5
            new_stats = {}
            for stat, base_val in base.items():
                new_stats[stat] = base_val + tier_bonus + growth.get(stat, 0) * levels

            # Step 3: Reapply only the capped wearables
            for w in self.wearables:
                s = w.get('stat')
                b = w.get('bonus', 0)
                if s in new_stats:
                    new_stats[s] += b
                elif s:
                    new_stats[s] = b

            # Step 4: Take the HIGHER of old vs new for each stat
            # (player gets the benefit of new scaling if it's better)
            for stat in new_stats:
                old_val = self.stats.get(stat, 0)
                new_val = new_stats[stat]
                self.stats[stat] = max(old_val, new_val)
                if new_val > old_val:
                    migrated.append(f"{stat.title()} {old_val} → {new_val}")

            # Step 5: Recalculate HP — take the higher of old vs new baseline
            base_hp = (config.get('base_health', 100) +
                       config.get('health_per_level', 10) * levels +
                       (self.class_tier - 1) * 10)
            if self.max_health < base_hp:
                self.max_health = base_hp
                self.health = min(self.health, self.max_health)
                migrated.append(f"Max HP updated to {base_hp}")

            self.save_version = '7.7.0'
            migrated.append(f"Migrated to v7.7.0 (L{self.level} T{self.class_tier})")

        if migrated:
            print(f"\n[Save migrated]")
            for m in migrated:
                print(f"  + {m}")


