"""
LABYRINTH — Hall of Records (persistent cross-run stats)
"""
from __future__ import annotations
import json, os, logging

logger = logging.getLogger(__name__)

from constants import GameConstants

class RecordsManager:
    """Persists stats across all runs in saves/records.json"""
    PATH = os.path.join(GameConstants.SAVE_DIRECTORY, 'records.json')

    DEFAULTS = {
        'total_bosses_defeated': 0,
        'total_deaths':          0,
        'total_floors_cleared':  0,
        'runs_completed':        0,
        'best_floor_reached':    0,
        'void_walker_unlocked':  False,
        'adamus_impressed':      False,
        'first_clear_name':      None,
    }

    @classmethod
    def load(cls) -> dict:
        try:
            if os.path.exists(cls.PATH):
                with open(cls.PATH) as f:
                    data = json.load(f)
                # backfill any new keys
                for k, v in cls.DEFAULTS.items():
                    data.setdefault(k, v)
                return data
        except (json.JSONDecodeError, OSError, KeyError):
            pass
        return cls.DEFAULTS.copy()

    @classmethod
    def save(cls, records: dict) -> None:
        try:
            os.makedirs(GameConstants.SAVE_DIRECTORY, exist_ok=True)
            with open(cls.PATH, 'w') as f:
                json.dump(records, f, indent=2)
        except OSError:
            pass

    @classmethod
    def update(cls, **kwargs) -> dict:
        rec = cls.load()
        for k, v in kwargs.items():
            if k in ('total_bosses_defeated', 'total_deaths',
                     'total_floors_cleared', 'runs_completed'):
                rec[k] = rec.get(k, 0) + v
            elif k == 'best_floor_reached':
                rec[k] = max(rec.get(k, 0), v)
            else:
                rec[k] = v
        cls.save(rec)
        return rec

    @classmethod
    def display(cls) -> None:
        rec = cls.load()
        print("\n" + "═"*50)
        print("  ★  HALL OF RECORDS  ★")
        print("═"*50)
        print(f"  Bosses defeated (all runs) : {rec['total_bosses_defeated']}")
        print(f"  Floors cleared (all runs)  : {rec['total_floors_cleared']}")
        print(f"  Deaths (all runs)          : {rec['total_deaths']}")
        print(f"  Runs completed             : {rec['runs_completed']}")
        print(f"  Best floor reached         : {rec['best_floor_reached']}/10")
        if rec['first_clear_name']:
            print(f"  First clear by             : {rec['first_clear_name']}")
        print()
        if rec['void_walker_unlocked']:
            print("  ★ VOID WALKER UNLOCKED — available at character creation")
        else:
            print("  [ Beat the game to unlock the Void Walker class ]")
        print("═"*50)


