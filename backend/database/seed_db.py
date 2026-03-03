"""
seed_db.py — Just delegates to setup.init_db()
All seeding is now consolidated in setup.py.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.setup import init_db

if __name__ == "__main__":
    init_db()