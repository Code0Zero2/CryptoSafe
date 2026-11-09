import sys
from pathlib import Path

# Ensure src is on python path
src_path = Path(__file__).resolve().parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from cryptosafe.app import main

if __name__ == "__main__":
    sys.exit(main())

