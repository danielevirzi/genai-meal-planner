from __future__ import annotations

import argparse
import sys

from api.database import SessionLocal, init_db
from api.yaml_import import IngredientCatalogImportError, import_ingredient_catalog_file


def main() -> int:
    parser = argparse.ArgumentParser(description="GenAI meal planner utilities")
    subparsers = parser.add_subparsers(dest="command")

    import_yaml_parser = subparsers.add_parser(
        "import-yaml",
        help="Import an ingredient catalog YAML file into the database",
    )
    import_yaml_parser.add_argument("file_path", help="Path to the YAML file to import")

    args = parser.parse_args()
    if args.command != "import-yaml":
        parser.print_help()
        return 0

    try:
        init_db(seed_data=False)
        with SessionLocal() as db:
            summary = import_ingredient_catalog_file(db, args.file_path)
        print(summary.model_dump_json(indent=2))
        return 0
    except IngredientCatalogImportError as exc:
        print(f"YAML import failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
