"""
LABYRINTH — Core constants and aggregator
Imports data from sub-modules and re-exports through GameConstants.
"""
from __future__ import annotations
import random, json, os, logging
from typing import Dict, List, Optional, Set, Tuple, Any, TYPE_CHECKING, Callable
from difflib import get_close_matches
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

from items_data   import ItemsData
from enemies_data import EnemiesData
from weapons_data import WeaponsData
from lore_data    import LoreData
from world_data   import WorldData


class GameConstants(ItemsData, EnemiesData, WeaponsData, LoreData, WorldData):
    """
    Central constants hub. Inherits all data from focused sub-modules:
      ItemsData    — healing, wearables, shop, actionable, quest items
      EnemiesData  — enemies, floor themes, weaknesses, behaviours, status effects
      WeaponsData  — rarities, types, materials, traits, golden gun
      LoreData     — floor lore, boss intros, journals, NG+ title screens
      WorldData    — NG+ worlds, fusion classes, fusion tier names/levels
    """

    # ── Core game parameters ──────────────────────────────────────
    VERSION = "7.6.5"
    SAVE_FILE = "savegame.json"
    SAVE_DIRECTORY = "saves"
    MAX_SAVE_SLOTS = 5
    

    NUM_FLOORS = 10
    MIN_ROOMS_PER_FLOOR = 10
    MAX_ROOMS_PER_FLOOR = 15
    
    # Class definitions with enhanced inventory

    # ── Character classes ─────────────────────────────────────────
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

    # ── Combat parameters ─────────────────────────────────────────
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

    # ── get_fusion helper ─────────────────────────────────────────
    @classmethod
    def get_fusion(cls, class1: str, class2: str):
        """Return fusion data for two classes, checking both orderings."""
        key = (class1.lower(), class2.lower())
        return cls.FUSION_CLASSES.get(key) or cls.FUSION_CLASSES.get((key[1], key[0]))


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
