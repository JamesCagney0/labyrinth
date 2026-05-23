"""
LABYRINTH — Entry point
Run with: python main.py
"""
import sys, os, logging

# Pythonista-safe path setup
try:
    _here = os.path.dirname(os.path.abspath(__file__))
    if _here not in sys.path:
        sys.path.insert(0, _here)
except Exception:
    pass

# Pythonista-safe logging (no file writes)
try:
    logging.basicConfig(
        filename='game.log', level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        filemode='a'
    )
except Exception:
    logging.disable(logging.CRITICAL)  # silence all logging silently

from game import Game

def main():
    """Main entry point"""
    debug  = '--debug'  in sys.argv
    mature = '--mature' in sys.argv
    try:
        game = Game()
        if debug:
            game.debug_mode = True
            print("  [DEBUG MODE ENABLED]")
            print("  Commands: warp <floor> | give <item> | levelup <n> | fullheal | unlock | debugfuse | debugngplus [world]")
        if mature:
            game.mature_mode = True
        game.start_game()
    except KeyboardInterrupt:
        print("\n\nGame interrupted. Goodbye!")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        print("Please report this bug!")
    finally:
        sys.exit(0)

if __name__ == '__main__':
    main()
