"""Safely copy SOCIALPULSE records from SQLite to an already migrated PostgreSQL database.

Dry-run is the default. Applying requires --apply and an explicit target URL via
--database-url or MIGRATION_DATABASE_URL. The source SQLite file is opened read-only.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import DateTime, Boolean, create_engine, inspect, text
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import Base  # noqa: E402
from app.models.dataset import DatasetActivation, DatasetRecord  # noqa: E402,F401
from app.models.system import ActivityRecord, NotificationRecord, ReportRecord  # noqa: E402,F401
from app.models.user import User  # noqa: E402,F401

SOURCE_TABLES = ("users", "dataset_records", "notifications", "activity_logs", "reports")
DESTINATION_TABLES = (*SOURCE_TABLES, "dataset_activations")
INITIAL_REVISION = "0001_initial"


def read_source(source_path: Path) -> tuple[dict[str, list[dict]], list[dict]]:
	if not source_path.is_file():
		raise FileNotFoundError(f"SQLite source database not found: {source_path}")
	uri = "file:" + quote(source_path.resolve().as_posix(), safe="/:\\") + "?mode=ro"
	connection = sqlite3.connect(uri, uri=True)
	connection.row_factory = sqlite3.Row
	try:
		names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
		missing = set(SOURCE_TABLES) - names
		if missing:
			raise RuntimeError("SQLite source is missing tables: " + ", ".join(sorted(missing)))
		violations = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")]
		if violations:
			raise RuntimeError(f"SQLite source contains foreign-key violations: {violations[:10]}")
		data = {
			table: [dict(row) for row in connection.execute(f'SELECT * FROM "{table}"')]
			for table in SOURCE_TABLES
		}
		duplicate_emails = [email for email, count in Counter(row["email"] for row in data["users"]).items() if count > 1]
		if duplicate_emails:
			raise RuntimeError("Duplicate user email addresses prevent migration: " + ", ".join(duplicate_emails))
		return data, violations
	finally:
		connection.close()


def active_dataset_rows(data: dict[str, list[dict]]) -> list[dict]:
	users = {row["id"] for row in data["users"]}
	active_by_user: dict[int, dict] = {}
	for row in data["dataset_records"]:
		owner_id = row.get("owner_id")
		if not row.get("is_active") or owner_id is None:
			continue
		if owner_id not in users:
			raise RuntimeError(f"Dataset {row['id']} references missing owner {owner_id}.")
		previous = active_by_user.get(owner_id)
		if previous is None or str(row.get("created_at", "")) > str(previous.get("created_at", "")):
			active_by_user[owner_id] = row
	return [
		{"user_id": owner_id, "dataset_id": row["id"], "updated_at": row["created_at"]}
		for owner_id, row in sorted(active_by_user.items())
	]


def normalize_postgres_url(url: str) -> str:
	if url.startswith("postgres://"):
		url = url.replace("postgres://", "postgresql+psycopg://", 1)
	parsed = make_url(url)
	if parsed.get_backend_name() != "postgresql":
		raise ValueError("Destination must be PostgreSQL; SQLite and other dialects are not accepted.")
	if parsed.drivername in ("postgres", "postgresql"):
		parsed = parsed.set(drivername="postgresql+psycopg")
	return parsed.render_as_string(hide_password=False)


def inspect_destination(connection) -> dict[str, int]:
	inspector = inspect(connection)
	table_names = set(inspector.get_table_names())
	missing = set(DESTINATION_TABLES) - table_names
	if missing:
		raise RuntimeError("Destination schema is missing tables; apply the reviewed Alembic migration first: " + ", ".join(sorted(missing)))
	if "alembic_version" not in table_names:
		raise RuntimeError("Destination has no Alembic revision. Run the reviewed migration before data transfer.")
	revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
	if revision != INITIAL_REVISION:
		raise RuntimeError(f"Destination revision must be {INITIAL_REVISION!r}; found {revision!r}.")
	counts = {
		table: int(connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one())
		for table in DESTINATION_TABLES
	}
	occupied = {table: count for table, count in counts.items() if count}
	if occupied:
		raise RuntimeError("Destination is not empty; refusing to merge or overwrite rows: " + json.dumps(occupied, sort_keys=True))
	return counts


def transfer(connection, data: dict[str, list[dict]]) -> dict[str, int]:
	inserted: dict[str, int] = {}
	for table_name in SOURCE_TABLES:
		table = Base.metadata.tables[table_name]
		rows = data[table_name]
		if rows:
			columns = {column.name: column for column in table.columns}
			prepared = []
			for row in rows:
				values = {key: value for key, value in row.items() if key in columns}
				for key, value in values.items():
					if value is not None and isinstance(columns[key].type, DateTime) and isinstance(value, str):
						values[key] = datetime.fromisoformat(value)
					elif value is not None and isinstance(columns[key].type, Boolean):
						values[key] = bool(value)
				prepared.append(values)
			connection.execute(table.insert(), prepared)
		inserted[table_name] = len(rows)

	activations = active_dataset_rows(data)
	table = Base.metadata.tables["dataset_activations"]
	if activations:
		connection.execute(table.insert(), activations)
	inserted["dataset_activations"] = len(activations)

	for table_name in ("users", "dataset_records", "notifications", "activity_logs", "reports"):
		connection.execute(
			text(
				f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
				f"COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {table_name}"
			)
		)

	actual = {
		table: int(connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one())
		for table in DESTINATION_TABLES
	}
	if actual != inserted:
		raise RuntimeError(f"Destination row-count verification failed: expected {inserted}, got {actual}.")
	return actual


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--source", type=Path, default=BACKEND_DIR / "socialpulse.db", help="Authoritative SQLite source (opened read-only).")
	parser.add_argument("--database-url", default=os.getenv("MIGRATION_DATABASE_URL"), help="Explicit PostgreSQL target; never inferred from DATABASE_URL.")
	parser.add_argument("--apply", action="store_true", help="Commit transfer into an empty PostgreSQL database. Default is dry-run.")
	parser.add_argument("--report-file", type=Path, help="Optional path to save the JSON migration report.")
	args = parser.parse_args()

	source_data, _ = read_source(args.source)
	source_counts = {table: len(source_data[table]) for table in SOURCE_TABLES}
	report = {
		"generated_at": datetime.now(timezone.utc).isoformat(),
		"source": str(args.source.resolve()),
		"source_open_mode": "read-only",
		"mode": "apply" if args.apply else "dry-run",
		"source_row_counts": source_counts,
		"derived_dataset_activations": len(active_dataset_rows(source_data)),
		"destination_row_counts": None,
		"destination_status": "not connected (no explicit migration target supplied)",
		"committed": False,
		"rollback_guidance": "On transfer failure the PostgreSQL transaction is rolled back. If a committed migration must be undone, restore the destination from a pre-migration PostgreSQL backup; keep the SQLite source and its backup unchanged.",
	}
	target_url = args.database_url
	if args.apply and not target_url:
		parser.error("--apply requires --database-url or MIGRATION_DATABASE_URL; the ordinary DATABASE_URL is intentionally ignored.")

	if target_url:
		engine = create_engine(normalize_postgres_url(target_url), pool_pre_ping=True)
		try:
			if args.apply:
				with engine.begin() as connection:
					inspect_destination(connection)
					report["destination_row_counts"] = transfer(connection, source_data)
				report["destination_status"] = "verified; transaction committed"
				report["committed"] = True
			else:
				with engine.connect() as connection:
					report["destination_row_counts"] = inspect_destination(connection)
				report["destination_status"] = "verified empty and at initial Alembic revision; no data written"
		finally:
			engine.dispose()

	output = json.dumps(report, indent=2, sort_keys=True)
	print(output)
	if args.report_file:
		args.report_file.parent.mkdir(parents=True, exist_ok=True)
		args.report_file.write_text(output + "\n", encoding="utf-8")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
