"""Upload existing local dataset and report artifacts to private Supabase Storage.

This is dry-run by default. Use --apply only after configuring service credentials and
creating/verifying the two private buckets with the explicit storage setup command.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.services.cloud_storage import configured, ensure_private_buckets, upload_bytes  # noqa: E402

DATA_DIR = PROJECT_ROOT / "dataset_uploads"
REPORTS_DIR = PROJECT_ROOT / "reports"


def collect_objects(database_path: Path) -> list[tuple[str, str, Path, str]]:
	if not database_path.is_file():
		raise FileNotFoundError(f"SQLite metadata database not found: {database_path}")
	uri = database_path.resolve().as_uri() + "?mode=ro"
	connection = sqlite3.connect(uri, uri=True)
	try:
		datasets = connection.execute(
			"SELECT stored_filename, cleaned_filename FROM dataset_records"
		).fetchall()
		reports = connection.execute("SELECT filename, format FROM reports").fetchall()
	finally:
		connection.close()

	objects: dict[tuple[str, str], tuple[str, str, Path, str]] = {}
	for stored_filename, cleaned_filename in datasets:
		for filename in (stored_filename, cleaned_filename):
			if not filename:
				raise RuntimeError("Dataset metadata contains an empty file reference.")
			path = (DATA_DIR / filename).resolve()
			if not path.is_relative_to(DATA_DIR.resolve()):
				raise RuntimeError(f"Dataset path escapes its storage directory: {filename!r}")
			objects[(settings.supabase_dataset_bucket, filename)] = (
				settings.supabase_dataset_bucket, filename, path, "text/csv"
			)
	for filename, file_format in reports:
		if not filename:
			raise RuntimeError("Report metadata contains an empty file reference.")
		path = (REPORTS_DIR / filename).resolve()
		if not path.is_relative_to(REPORTS_DIR.resolve()):
			raise RuntimeError(f"Report path escapes its storage directory: {filename!r}")
		content_types = {
			"pdf": "application/pdf",
			"csv": "text/csv",
			"xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
			"json": "application/json",
		}
		objects[(settings.supabase_report_bucket, filename)] = (
			settings.supabase_report_bucket,
			filename,
			path,
			content_types.get(str(file_format).lower(), "application/octet-stream"),
		)
	return list(objects.values())


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--database", type=Path, default=BACKEND_DIR / "socialpulse.db", help="Authoritative SQLite source; opened read-only.")
	parser.add_argument("--apply", action="store_true", help="Upload all referenced files to private Storage buckets. Default is dry-run.")
	args = parser.parse_args()

	objects = collect_objects(args.database)
	missing = [str(path) for _, _, path, _ in objects if not path.is_file()]
	result = {
		"generated_at": datetime.now(timezone.utc).isoformat(),
		"mode": "apply" if args.apply else "dry-run",
		"source_database": str(args.database.resolve()),
		"source_open_mode": "read-only",
		"dataset_bucket": settings.supabase_dataset_bucket,
		"report_bucket": settings.supabase_report_bucket,
		"referenced_files": len(objects),
		"missing_files": missing,
		"uploaded_files": 0,
		"committed": False,
	}

	if args.apply:
		if not configured():
			parser.error("--apply requires SUPABASE_URL and SUPABASE_SERVICE_KEY.")
		if missing:
			raise RuntimeError("Refusing partial upload; referenced files are missing: " + ", ".join(missing))
		ensure_private_buckets()
		for bucket, object_path, local_path, content_type in objects:
			upload_bytes(bucket, object_path, local_path.read_bytes(), content_type)
		result["uploaded_files"] = len(objects)
		result["committed"] = True
		result["status"] = "all referenced local files uploaded to the configured private buckets"
	else:
		result["status"] = "no files uploaded; pass --apply after verifying credentials and private buckets"

	print(json.dumps(result, indent=2, sort_keys=True))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
