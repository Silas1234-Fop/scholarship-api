"""
Import this as the very first import in every file.
It guarantees Python can always find db, scraper, browser etc.
regardless of how PyCharm or any other tool launches the script.
"""
import sys
import os

# Get the absolute path of the api/ folder (where this file lives)
_API_DIR = os.path.dirname(os.path.abspath(__file__))

# Insert at position 0 so it takes priority over everything else
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)

# Also set working directory to the api/ folder
os.chdir(_API_DIR)
