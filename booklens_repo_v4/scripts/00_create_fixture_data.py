"""
Create an offline fixture dataset for testing the BookLens pipeline.

This does not replace live API collection. It exists so the full pipeline can
be verified without internet access.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", default="data/fixtures/book_fixture.csv")
    parser.add_argument("--out", default="data/raw/openlibrary_books.csv")
    args = parser.parse_args()

    fixture_path = Path(args.fixture)
    output_path = Path(args.out)
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture file not found: {fixture_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(fixture_path, output_path)
    print(f"Copied fixture dataset to {output_path}")


if __name__ == "__main__":
    main()
