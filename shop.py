"""LABYRINTH — Shop (Adamus the Loyal)"""
from __future__ import annotations
import random, json, os, logging
from typing import Dict, List, Optional, Set, Tuple, Any, TYPE_CHECKING, Callable
from difflib import get_close_matches
from dataclasses import dataclass, field
if TYPE_CHECKING:
    from game import Game

logger = logging.getLogger(__name__)

from constants import GameConstants
from weapons import WeaponSystem, WeaponComparison
from records import RecordsManager


class ShopMixin:
    """Shop methods. Mixed into Game."""

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
            # Filter shop stock: remove wearables the player is already capped on
            lvl = self.player.level
            max_stack = 1 if lvl < 5 else 2 if lvl < 10 else 3 if lvl < 15 else 4
            def _shop_at_cap(item_name):
                if item_name not in GameConstants.WEARABLE_ITEMS:
                    return False
                if GameConstants.WEARABLE_ITEMS[item_name].get('cursed'):
                    return False
                count = sum(1 for w in self.player.wearables if w['item'] == item_name)
                return count >= max_stack
            cur_items = [(name, price, desc) for name, price, desc in items
                         if not _shop_at_cap(name)]


            print(f"\n  Stock: {tier_name}  |  {len(cur_items)} items available")
            for i, (name, price, desc) in enumerate(cur_items, 1):
                can_afford = "  " if self.player.gold_coins >= price else "✗ "
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
    
