"""Dictionary adapter usable by any editor, without an MCP installation."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crawler.taiwanese_dictionary import lookup_taiwanese

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python3 scripts/lookup_taiwanese.py WORD')
    print(json.dumps(lookup_taiwanese(sys.argv[1]), ensure_ascii=False, indent=2))
