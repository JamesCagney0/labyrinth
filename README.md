# LABYRINTH
### A 10-Floor Text Dungeon RPG — v7.7.0

> *The Dungeon Does Not Forgive. Will You?*

---

## Overview

LABYRINTH is a single-player text-based dungeon RPG written in Python. Descend 10 floors of a shifting dungeon, fight enemies and bosses, upgrade your character through 5 class tiers, and uncover the lore of what the dungeon actually is. Survive long enough and you'll unlock New Game Plus — five distinct worlds, harder enemies, and a class fusion system that pushes progression to Tier 10.

---

## Requirements

- Python 3.8+
- No external dependencies

---

## Running the Game

```bash
cd labyrinth
python main.py
```

**Flags:**
```bash
python main.py --debug    # Enable debug commands (warp, give, levelup, fullheal)
python main.py --mature   # Enable mature content (opt-in only)
```

---

## Character Classes

Six playable classes, each with distinct stat growth, weapon types, and a unique boss ability:

| Class | HP/Lvl | Identity | Boss Ability |
|---|---|---|---|
| **Warrior** | +15 | High HP, melee, steady scaling | Titan Strike |
| **Mage** | +8 | Fragile, arcane power, mana system | Arcane Nova |
| **Rogue** | +12 | Highest crit rate, stealth weapons | Shadow Step |
| **Paladin** | +13 | Holy melee, Smite costs mana | Divine Smite |
| **Berserker** | +18 | Tankiest class, rage scales with missing HP | Berserker Rage |
| **Void Walker** *(unlock)* | +7 | 2.5× crits, vampiric heals, Phase | Phase |

Void Walker unlocks after your first game clear.

Each class has 5 tiers with unique titles:
- Tier upgrades at **Level 6, 10, 14, 18**
- Tier 5 unlocks Class Fusion in New Game Plus

---

## Class Fusion (New Game Plus)

At Tier 5 in NG+, any two classes can be fused into one of **15 unique fusion classes**. Each fusion has:
- Averaged parent stats + a unique bonus
- A passive that applies in all combat
- A unique boss ability
- 5 additional prestige tiers (T6–T10) with unique titles, capping at a **Mythic** title

Example fusions: Void Phantom (Rogue + Void Walker), War Incarnate (Warrior + Berserker), Reality Sorcerer (Mage + Void Walker)

---

## Combat

**Regular combat:** Turn-based, one action per turn. Enemies have unique behaviours — some regenerate HP, some resist damage, some inflict status effects, some buff allies.

**Boss combat:** Full action menu — Attack, Class Ability, Defend, Heal, Swap Weapon. Each boss has a named special attack and a pre-fight monologue.

**Status effects:** Bleed (8 dmg/turn, 3 turns), Poison (6 dmg/turn, 4 turns), Weaken (75% damage, 2 turns). Effects tick between rooms.

---

## Weapons & Loot

Weapons have **rarities** (Common → Mythic) and up to 3 **traits** from a pool of 13 including Bleeding, Vampiric, Holy, Void, Executioner, Berserker, Precise, and more. Each trait has a passive combat effect.

Floor rarity caps apply in early floors — Common/Uncommon on F1–F2, Rare cap on F3–F4. Boss drops are uncapped.

---

## Items

**Healing:** Health potion, Vitality tonic, Elixir of life, Ultimate health potion, Magic scroll

**Conditional consumables:** Elixir of Desperation (heals 60% of missing HP), Void Tonic (converts next hit to MP), Berserker's Draught (heals 40% of fight damage), Antidote (clears status), Battle Tincture (+30% damage, 3 turns)

**Wearables:** Passive stat bonuses. Stack cap scales with level (1 copy at L1-4, up to 4 copies at L15+). Cursed wearables give large bonuses with a cost.

**Quest items:** Torch, Rusty Key, Bone Key, Demon Seal, Crystal Shard, Void Essence, Primordial Rune, Ancient Medallion — each unlocks a secret room when used in the right place.

---

## Special Rooms

| Room | Key Item | Reward |
|---|---|---|
| Hidden Alcove | Torch | Secret treasure |
| Locked Vault | Rusty Key | Gold + items |
| Bone Crypt | Bone Key | XP + rare items |
| Demon Gate | Demon Seal | Power ring + healing |
| Crystal Chamber | Crystal Shard | +3 all stats, +20 HP |
| Void Tear | Void Essence | +5 INT, +3 LCK, +300 XP |
| Primordial Monument | Primordial Rune | +2 all stats, +30 HP |
| Sacred Shrine | Ancient Medallion | +50 HP, +4 STR/VIT, rarity boost |
| Forgotten Game Room | — | Gambler's d20 (DnD easter egg) |

---

## The Shop (Adamus the Loyal)

Available at each floor's start room. Buy items scaled to your floor, sell stored weapons for gold. Adamus has 15 rotating insults. He acknowledges you exactly once after your first game clear — and never again.

---

## New Game Plus

Beating the Reality Breaker triggers a full NG+ transition. One of 5 themed worlds is randomly selected:

- **The Fractured Labyrinth** — reality is breaking down
- **The Drowned Kingdom** — submerged ruins, coral, and drowned soldiers
- **The Ashen Wastes** — scorched world, fire and ash
- **The Mechanical Depths** — clockwork dungeon, constructs and automata
- **The Plague Cathedral** — corrupted holy ground, pestilence

Each world has 19 unique enemies, 10 unique bosses, distinct room templates, and a unique title screen. NG+ is harder than the base game — HP scales +40% per cycle, damage +20%.

---

## Lore

- **Floor entry text** on every descent
- **Boss monologues** before each fight
- **5 discoverable journals** from Researcher Varek (floors 2, 4, 5, 7, 9) — piece together why the dungeon exists and what the Reality Breaker actually is

---

## Hall of Records

Persistent cross-run stats: bosses defeated, deaths, floors cleared, runs completed, best floor, first clear. Accessible from the main menu.

---

## Save System

5 save slots, JSON format. Automatic migration — old saves load and update to the current version. Saves store exact room names, items, and exits so reloading always returns you to precisely where you left off.

---

## Commands

```
Movement:    n/s/e/w/up/down   go <dir>
Combat:      fight / f         fightall / fa
Inventory:   inventory / i     take <item>     takeall
             equip <item>      discard <item>  use <item>    switch
Character:   stats / s         upgrade         fuse
World:       look / l          map / m         shop
Game:        save              quit / q        help / h      help all
```

---

## Debug Mode (`--debug`)

```
warp <floor>         Teleport to any floor
give <item>          Add item (routes through normal pickup)
give gold <amount>   Add gold directly
levelup <n>          Set target level
fullheal             Restore HP and MP
unlock voidwalker    Unlock Void Walker class
debugfuse <c1> <c2>  Force class fusion at T5
```

---

## Changelog

### v7.7.0 — Balance, Polish & Architecture
- Full scaling overhaul: XP curve, boss HP/damage, enemy XP all redesigned for target level per floor
- NG+ cycle damage/HP split — HP scales +40%/cycle, damage only +20%
- Floor rarity caps: F1-F2 max Uncommon, F3-F4 max Rare
- Tier upgrade levels pushed to L6/10/14/18 (was L4/8/12/16)
- Save migration: recalibrates old saves to new baseline, enforces wearable cap, strips unknown stats
- Separate weapon inventory slots (10 max), no longer competing with item slots
- `safe_input()` wrapper across all files — EOF-safe for piped/headless environments
- Debug flag `--debug` with warp, give, levelup, fullheal, unlock, debugfuse
- `--mature` opt-in flag for mature content
- Map spoiler fix — unexplored rooms show as `???`
- Shop Leave pinned to `0` — invariant across all floor tiers
- `fight` auto-selects when only one enemy present
- First shop visit uses neutral greeting, quips start on second visit
- Consume-on-pickup items (gold, XP gems) bypass full inventory check

### v7.6.5 — Modularisation Pass 2 + Bug Fixes
- `game.py` split into 6 focused mixins: actions, shop, save_load, ng_plus, dungeon, game
- `constants.py` split into 6 data modules: items_data, enemies_data, weapons_data, lore_data, world_data, constants
- Package: 22 files, ~8,700 lines
- Separate weapon slots — weapons no longer compete with item inventory
- Wearable stack cap gated by level
- All special room double-triggers fixed (Demon Gate, Bone Crypt, Crystal Chamber, etc.)
- Boss weapon pools extended to all 6 classes (Paladin, Berserker, Void Walker were missing)
- Paladin mana regen in boss combat (+8 MP/turn)
- Smite rebalanced for early floors
- MAGIC_MULTIPLIERS fixed (was dict, caused TypeError on magic attacks)
- shop.py buy display fixed — items were silently not printing
- Save files now store exact room name/description — no random regeneration on load

### v7.6.0 — Modularisation Pass 1
- Split from single 7,400-line file into modular package
- 14 initial modules, all imports resolved

### v7.5.2 — Combat Depth, Lore & Items
- 15 enemy behaviour patterns (regen, resistance, status inflict, buff-others)
- Player status effects: Bleed, Poison, Weaken — tick between rooms
- Conditional consumables: Elixir of Desperation, Void Tonic, Berserker's Draught, Antidote, Battle Tincture
- Cursed wearables with meaningful tradeoffs
- Floor entry text (all 10 floors), boss intro monologues
- 5 discoverable Varek journals with lore arc
- Class fusion tier progression T6-T10 with unique titles, caps at Mythic T10
- Forgotten Game Room (DnD easter egg with Welventier campaign lore)

### v7.5.0 — Code Architecture
- `fight_boss` refactored from 425 lines into focused helpers
- `use_special_item` refactored from 344-line if/elif chain into dispatch table
- All inline imports moved to module level

### v7.0.2 — Quality of Life
- Item hint system — wrong-room use gives location hints
- Legacy save compatibility for pre-NG+ saves
- NG+ weapon warning system with keep/discard options
- Shop sell feature with Adamus rarity reactions
- Weapon swap during boss fights
- Switch weapon fix for weapons without labels

### v7.0.1 — Balance & Bug Fixes
- Enemy HP raised ~35% across board
- Weapon scaling bug fixed (double rarity multiplication)
- Boss weapon hard damage caps on all 10 floors
- upgrade_class stat preservation fix

### v7.0.0 — New Game Plus
- 5 NG+ worlds with unique enemies, bosses, room templates
- Void Walker class (unlocks after first clear)
- Class Fusion system (15 combinations, available at T5 in NG+)
- Hall of Records (persistent cross-run stats)
- Adamus one-time acknowledgment after game clear
- NG+ cycle difficulty scaling
- NG+ weapon audit system

### v6.9.0 — Base Game Complete
- 6 character classes with 5-tier progression
- 10-floor dungeon with procedural generation
- Turn-based boss combat with class abilities
- Weapon rarity system (7 tiers), trait system (13 traits)
- Special rooms and quest items
- Compass-style map with depth arrows
- 5 save slots with migration
- Adamus the Loyal shop

---

*Built with Python. No external dependencies. Runs on Pythonista (iOS) and any Python 3.8+ environment.*
