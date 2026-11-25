"""
Controlled promotion and rollback of approved artifacts.

    python -m mlops.promote rl status
    python -m mlops.promote rl promote <version> --by <name>
    python -m mlops.promote rag rollback [--to <version>] --by <name>
"""

import argparse
import json
import sys

from mlops.common import manifest as mf
from mlops.common.storage import read_json


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("kind", choices=sorted(mf.MANIFEST_TYPES))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    p = sub.add_parser("promote")
    p.add_argument("version")
    p.add_argument("--by", required=True)
    r = sub.add_parser("rollback")
    r.add_argument("--to", default=None)
    r.add_argument("--by", required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "promote":
            mf.promote(args.kind, args.version, args.by)
        elif args.command == "rollback":
            mf.rollback(args.kind, args.by, args.to)
    except mf.ManifestError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    pointer = mf.latest_path(args.kind)
    print(json.dumps(read_json(pointer) if pointer.exists() else None, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
