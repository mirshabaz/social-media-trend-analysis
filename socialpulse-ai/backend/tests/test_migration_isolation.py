import asyncio
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.dataset import DatasetActivation, DatasetRecord
from app.models.system import ReportRecord
from app.models.user import User
from app.services import cloud_storage
from app.services.dataset_service import activate_dataset, delete_dataset, get_active_dataset_record, upload_dataset
from app.services.report_service import delete_report, get_report


@pytest.fixture

def db_session():
	engine = create_engine(
		"sqlite://",
		connect_args={"check_same_thread": False},
		poolclass=StaticPool,
	)

	@event.listens_for(engine, "connect")
	def enable_foreign_keys(connection, _):
		connection.execute("PRAGMA foreign_keys=ON")

	Base.metadata.create_all(engine)
	with Session(engine) as session:
		yield session
	engine.dispose()


def make_user(db: Session, email: str) -> User:
	user = User(
		email=email,
		full_name=email.split("@")[0],
		password_hash="test-hash",
		is_active=True,
	)
	db.add(user)
	db.commit()
	db.refresh(user)
	return user


def make_dataset(db: Session, owner_id: int, name: str) -> DatasetRecord:
	record = DatasetRecord(
		name=name,
		original_filename=f"{name}.csv",
		stored_filename=f"{name}-original.csv",
		cleaned_filename=f"{name}-cleaned.csv",
		row_count=1,
		cleaned_row_count=1,
		column_count=1,
		duplicate_count=0,
		missing_value_count=0,
		invalid_record_count=0,
		status="ready",
		column_mapping_json="{}",
		cleaning_summary_json="{}",
		is_bundled=False,
		is_active=False,
		owner_id=owner_id,
	)
	db.add(record)
	db.commit()
	db.refresh(record)
	return record


def test_two_users_upload_and_activate_independently(db_session, monkeypatch, tmp_path):
	user_a = make_user(db_session, "a@example.test")
	user_b = make_user(db_session, "b@example.test")
	monkeypatch.setattr("app.services.dataset_service.DATA_DIR", tmp_path)
	monkeypatch.setattr("app.services.dataset_service.ensure_bundled_dataset", lambda _: None)
	monkeypatch.setattr("app.services.dataset_service.settings.supabase_url", "")
	monkeypatch.setattr("app.services.dataset_service.settings.supabase_service_key", "")

	async def upload(user_id: int, name: str):
		raw = f"post_id,post_content,likes\n{name},A useful social update,2\n".encode()
		file = UploadFile(filename=f"{name}.csv", file=BytesIO(raw))
		return await upload_dataset(db_session, file, owner_id=user_id, dataset_name=name)

	dataset_a = asyncio.run(upload(user_a.id, "dataset-a"))
	dataset_b = asyncio.run(upload(user_b.id, "dataset-b"))
	activate_dataset(db_session, dataset_a.id, user_id=user_a.id)

	assert get_active_dataset_record(db_session, user_id=user_a.id).id == dataset_a.id
	assert get_active_dataset_record(db_session, user_id=user_b.id).id == dataset_b.id
	assert db_session.get(DatasetActivation, user_a.id).dataset_id == dataset_a.id
	assert db_session.get(DatasetActivation, user_b.id).dataset_id == dataset_b.id


def test_user_cannot_activate_or_delete_another_users_dataset(db_session, monkeypatch, tmp_path):
	owner = make_user(db_session, "owner@example.test")
	other = make_user(db_session, "other@example.test")
	record = make_dataset(db_session, owner.id, "private")
	monkeypatch.setattr("app.services.dataset_service.DATA_DIR", tmp_path)

	with pytest.raises(HTTPException) as activate_error:
		activate_dataset(db_session, record.id, user_id=other.id)
	assert activate_error.value.status_code == 403

	with pytest.raises(HTTPException) as delete_error:
		delete_dataset(db_session, record.id, user_id=other.id)
	assert delete_error.value.status_code == 403
	assert db_session.get(DatasetRecord, record.id) is not None


def test_report_download_and_delete_access_is_owner_scoped(db_session, tmp_path, monkeypatch):
	owner = make_user(db_session, "report-owner@example.test")
	other = make_user(db_session, "report-other@example.test")
	report = ReportRecord(
		user_id=owner.id,
		dataset_name="private dataset",
		report_type="overall",
		format="json",
		filename="private.json",
		title="Private report",
		summary_json="{}",
	)
	db_session.add(report)
	db_session.commit()
	db_session.refresh(report)

	with pytest.raises(HTTPException) as access_error:
		get_report(db_session, report.id, user_id=other.id)
	assert access_error.value.status_code == 403

	with pytest.raises(HTTPException) as delete_error:
		delete_report(db_session, report.id, user_id=other.id)
	assert delete_error.value.status_code == 403
	assert db_session.get(ReportRecord, report.id) is not None


def test_storage_local_fallback_and_private_recovery(tmp_path, monkeypatch):
	local = tmp_path / "already-local.csv"
	local.write_text("local", encoding="utf-8")
	monkeypatch.setattr(cloud_storage.settings, "supabase_url", "")
	monkeypatch.setattr(cloud_storage.settings, "supabase_service_key", "")
	assert cloud_storage.ensure_local_file(local, "private", "already-local.csv") == local

	missing = tmp_path / "recovered.csv"
	monkeypatch.setattr(cloud_storage.settings, "supabase_url", "https://example.invalid")
	monkeypatch.setattr(cloud_storage.settings, "supabase_service_key", "server-only-test-key")
	monkeypatch.setattr(cloud_storage, "download_bytes", lambda *_: b"cloud-content")
	assert cloud_storage.ensure_local_file(missing, "private", "recovered.csv") == missing
	assert missing.read_bytes() == b"cloud-content"
