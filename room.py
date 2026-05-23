"""
LABYRINTH — Room
"""
from __future__ import annotations
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

from constants import GameConstants

class Room:
    """Dungeon room"""
    def __init__(self, name: str, description: str, floor: int,
                 items: List[str] = None, exits: Dict[str, str] = None,
                 enemies: List[str] = None, atmosphere: str = ""):
        self.name = name
        self.description = description
        self.floor = floor
        self.items = items or []
        self.exits = exits or {}
        self.enemies = enemies or []
        self.visited = False
        self.atmosphere = atmosphere
    
    def describe(self) -> None:
        """Show room description"""
        if not self.visited:
            print(f"\n{self.description}")
            if self.atmosphere:
                print(f"{self.atmosphere}")
            self.visited = True
        else:
            print(f"\nYou are in {self.name}")
            if 'adamus' in self.atmosphere.lower() or 'merchant' in self.atmosphere.lower():
                print("A merchant is here. Use 'shop' to trade.")
        
        if self.enemies:
            print(f"\n*** ENEMIES:")
            for enemy in self.enemies:
                info = GameConstants.ENEMIES.get(enemy.lower())
                if not info:
                    # Check all NG+ world enemy pools
                    for world_data in GameConstants.NG_PLUS_WORLDS.values():
                        info = world_data['enemies'].get(enemy.lower())
                        if info:
                            break
                if info:
                    print(f"  - {enemy}: {info['desc']}")
                else:
                    print(f"  - {enemy}")
        
        if self.items:
            print(f"\nItems: {', '.join(self.items)}")
        if self.exits:
            formatted = []
            for d in self.exits.keys():
                if d == 'secret':
                    pass  # Never reveal secret exits in room description
                elif d == 'out':
                    formatted.append('OUT (back)')
                else:
                    formatted.append(d)
            print(f"Exits: {', '.join(formatted)}")


