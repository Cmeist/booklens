from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import modal


APP_NAME = "booklens-data-jobs"
REMOTE_ROOT = Path("/root/booklens")
SECRET_NAME = "booklens-secrets"

app = modal.App(APP_NAME)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_pyproject("pyproject.toml")
    .add_local_dir("scripts", remote_path=str(REMOTE_ROOT / "scripts"))
)


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required in the Modal secret {SECRET_NAME}.")
    return value


@app.function(
    image=image,
    secrets=[modal.Secret.from_name(SECRET_NAME)],
    timeout=60 * 60,
)
def refresh_openlibrary(
    *,
    limit_total: int = 120,
    limit_per_subject: int = 15,
    subjects_csv: str | None = None,
    sleep_seconds: float = 0.25,
    enrich_google_books: bool = True,
) -> dict[str, Any]:
    import sys

    sys.path.insert(0, str(REMOTE_ROOT))

    from scripts.collect_openlibrary import collect_books, parse_subjects
    from scripts.enrich_google_books import PROCESSED_DIR, enrich_books
    from scripts.enrich_openlibrary_pages import enrich_openlibrary_pages
    from scripts.enrich_openlibrary_ratings import enrich_openlibrary_ratings
    from scripts.run_pipeline import RAW_DIR, run_pipeline
    from scripts.seed_supabase import load_csv_source, seed_supabase

    if limit_total < 1:
        raise ValueError("limit_total must be at least 1.")
    if limit_per_subject < 1:
        raise ValueError("limit_per_subject must be at least 1.")

    contact = require_env("BOOKLENS_CONTACT_EMAIL")
    require_env("SUPABASE_DB_URL")
    if enrich_google_books:
        require_env("GOOGLE_BOOKS_API_KEY")

    subjects = parse_subjects(subjects_csv)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = RAW_DIR / "openlibrary_books.csv"
    books = collect_books(
        contact=contact,
        subjects=subjects,
        limit_per_subject=limit_per_subject,
        limit_total=limit_total,
        sleep_seconds=sleep_seconds,
    )
    books.to_csv(raw_path, index=False)

    run_pipeline(use_openlibrary=True, input_path=None)

    ratings_stats = enrich_openlibrary_ratings(
        input_path=PROCESSED_DIR / "books_clean.csv",
        output_path=PROCESSED_DIR / "books_clean.csv",
        report_path=PROCESSED_DIR / "openlibrary_ratings_report.txt",
        contact=contact,
        limit=None,
        sleep_seconds=sleep_seconds,
        overwrite=False,
    )
    ratings_summary = {
        "searched": ratings_stats.searched,
        "filled": ratings_stats.filled,
        "already_present": ratings_stats.already_present,
        "missing": ratings_stats.missing,
        "api_errors": ratings_stats.api_errors,
    }

    enrichment_summary: dict[str, Any] | None = None
    pages_input = PROCESSED_DIR / "books_clean.csv"
    if enrich_google_books:
        enrichment_report_path = PROCESSED_DIR / "google_books_enrichment_report.txt"
        enrichment_stats = enrich_books(
            input_path=PROCESSED_DIR / "books_clean.csv",
            output_path=PROCESSED_DIR / "books_enriched.csv",
            report_path=enrichment_report_path,
            limit=None,
            sleep_seconds=sleep_seconds,
        )
        enrichment_summary = {
            "searched": enrichment_stats.searched,
            "matched": enrichment_stats.matched,
            "skipped_weak": enrichment_stats.skipped_weak,
            "unmatched": enrichment_stats.unmatched,
            "api_errors": enrichment_stats.api_errors,
            "isbns_added": enrichment_stats.isbns_added,
            "ratings_improved": enrichment_stats.fields_improved.get("rating_count", 0),
        }
        pages_input = PROCESSED_DIR / "books_enriched.csv"

    pages_stats = enrich_openlibrary_pages(
        input_path=pages_input,
        output_path=pages_input,
        report_path=PROCESSED_DIR / "openlibrary_pages_report.txt",
        contact=contact,
        limit=None,
        sleep_seconds=sleep_seconds,
    )
    pages_summary = {
        "searched": pages_stats.searched,
        "filled": pages_stats.filled,
        "already_present": pages_stats.already_present,
        "missing": pages_stats.missing,
        "api_errors": pages_stats.api_errors,
    }

    seeded_books, recommendations = load_csv_source()
    seed_supabase(seeded_books, recommendations, mode="csv")

    return {
        "collected_rows": len(books),
        "seeded_books": len(seeded_books),
        "recommendations": len(recommendations),
        "ratings": ratings_summary,
        "pages": pages_summary,
        "enrichment": enrichment_summary,
    }


@app.function(image=image)
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "app": APP_NAME}


@app.local_entrypoint()
def main(
    limit_total: int = 120,
    limit_per_subject: int = 15,
    subjects_csv: str = "",
    enrich_google_books: bool = True,
) -> None:
    result = refresh_openlibrary.remote(
        limit_total=limit_total,
        limit_per_subject=limit_per_subject,
        subjects_csv=subjects_csv or None,
        enrich_google_books=enrich_google_books,
    )
    print(result)
