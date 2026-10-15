import os
import sys

# Garantisce che la radice del repo sia importabile (import routes.*) in locale e in CI.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
