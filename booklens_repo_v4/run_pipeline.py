"""
One-command runner for the BookLens data pipeline.

Demo mode verifies the full pipeline offline:
    python run_pipeline.py --mode demo

Live mode collects current metadata from public APIs:
    python run_pipeline.py --mode live --contact your_email@example.com --limit-per-subject 100
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("\n$ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["demo", "live"], default="demo")
    parser.add_argument("--contact", default=None, help="Required for live mode. Use your email for API contact headers.")
    parser.add_argument("--limit-per-subject", type=int, default=100)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--subjects", nargs="*", default=None)
    parser.add_argument("--skip-openlibrary-details", action="store_true")
    parser.add_argument("--use-google-books", action="store_true", help="Optional enrichment. Slower; may hit rate limits without an API key.")
    parser.add_argument("--google-api-key", default=None)
    parser.add_argument("--seed-title", default="The Hunger Games")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    if Path.cwd().resolve() != project_root:
        print(f"Changing working directory to {project_root}")
        import os
        os.chdir(project_root)

    py = sys.executable

    if args.mode == "demo":
        run([py, "scripts/00_create_fixture_data.py", "--out", "data/raw/openlibrary_books.csv"])
        input_for_clean = "data/raw/openlibrary_books.csv"
    else:
        if not args.contact:
            raise SystemExit("Live mode requires --contact your_email@example.com")

        collect_cmd = [
            py,
            "scripts/01_collect_openlibrary_search.py",
            "--contact",
            args.contact,
            "--limit-per-subject",
            str(args.limit_per_subject),
            "--page-size",
            str(args.page_size),
            "--out",
            "data/raw/openlibrary_books.csv",
        ]
        if args.subjects:
            collect_cmd.extend(["--subjects", *args.subjects])
        run(collect_cmd)

        if args.skip_openlibrary_details:
            input_for_clean = "data/raw/openlibrary_books.csv"
        else:
            run([
                py,
                "scripts/02_fetch_openlibrary_work_details.py",
                "--contact",
                args.contact,
                "--input",
                "data/raw/openlibrary_books.csv",
                "--out",
                "data/processed/books_openlibrary_enriched.csv",
                "--max-works",
                str(min(args.limit_per_subject * 3, 500)),
            ])
            input_for_clean = "data/processed/books_openlibrary_enriched.csv"

        if args.use_google_books:
            google_cmd = [
                py,
                "scripts/03_enrich_google_books.py",
                "--input",
                input_for_clean,
                "--out",
                "data/processed/books_enriched.csv",
                "--max-rows",
                str(min(args.limit_per_subject * 3, 500)),
            ]
            if args.google_api_key:
                google_cmd.extend(["--api-key", args.google_api_key])
            run(google_cmd)
            input_for_clean = "data/processed/books_enriched.csv"

    run([
        py,
        "scripts/04_clean_books.py",
        "--input",
        input_for_clean,
        "--out",
        "data/processed/books_clean.csv",
        "--top-tags-out",
        "data/processed/top_tags.csv",
        "--report-out",
        "data/processed/data_quality_report.txt",
    ])

    run([
        py,
        "scripts/05_recommendation_prototype.py",
        "--input",
        "data/processed/books_clean.csv",
        "--out",
        "data/processed/similar_books_sample.csv",
        "--seed-title",
        args.seed_title,
        "--top-k",
        "10",
    ])

    print("\nPipeline complete.")
    print("Key outputs:")
    print("- data/raw/openlibrary_books.csv")
    print("- data/processed/books_clean.csv")
    print("- data/processed/top_tags.csv")
    print("- data/processed/data_quality_report.txt")
    print("- data/processed/similar_books_sample.csv")


if __name__ == "__main__":
    main()
