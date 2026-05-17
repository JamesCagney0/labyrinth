"""
LABYRINTH — Combat systems (DamageCalculator + CombatSystem)
"""
from __future__ import annotations
import random, json, os, logging
from typing import Dict, List, Optional, Set, Tuple, Any, TYPE_CHECKING, Callable
from difflib import get_close_matches
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

from constants import GameConstants, BossConfig
from weapons import WeaponSystem, WeaponComparison
from items import ItemHandler
from records import RecordsManager
if TYPE_CHECKING:
    from player import Player
    from room import Room

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
                    base_drops = ["health potion", "magic scroll", "ice crystal",
                                  "experience gem", "arcane pendant", "magic scroll"]
                else:
                    base_drops = ["health potion", "energy drink",
                                  "power ring", "swift boots", "experience gem",
                                  "armor piece", "swift boots", "experience gem"]

                # Filter out wearables the player is already capped on
                lvl = player.level
                max_stack = 1 if lvl < 5 else 2 if lvl < 10 else 3 if lvl < 15 else 4
                def _at_cap(item_name):
                    if item_name not in GameConstants.WEARABLE_ITEMS:
                        return False
                    if GameConstants.WEARABLE_ITEMS[item_name].get('cursed'):
                        return False
                    count = sum(1 for w in player.wearables if w['item'] == item_name)
                    return count >= max_stack

                drops = [d for d in base_drops if not _at_cap(d)]
                if not drops:
                    drops = [d for d in base_drops if d not in GameConstants.WEARABLE_ITEMS]
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

