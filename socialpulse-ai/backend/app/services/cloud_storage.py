from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import settings


def configured() -> bool:
	return bool(settings.supabase_url and settings.supabase_service_key)


def _auth_headers() -> dict[str, str]:
	if not configured():
		raise RuntimeError("Supabase Storage is not configured.")
	return {
		"apikey": settings.supabase_service_key,
		"Authorization": "Bearer " + settings.supabase_service_key,
	}


def _object_url(bucket: str, object_path: str) -> str:
	safe_bucket = quote(bucket, safe="")
	safe_path = quote(object_path.lstrip("/"), safe="/")
	return f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{safe_bucket}/{safe_path}"


def ensure_private_buckets() -> list[str]:
	"""Create the configured private buckets; intended for an explicit setup command."""
	headers = _auth_headers()
	created: list[str] = []
	for bucket in (settings.supabase_dataset_bucket, settings.supabase_report_bucket):
		response = httpx.get(
			f"{settings.supabase_url.rstrip('/')}/storage/v1/bucket/{quote(bucket, safe='')}",
			headers=headers,
			timeout=20.0,
		)
		if response.status_code == 200:
			if response.json().get("public") is True:
				raise RuntimeError(f"Storage bucket '{bucket}' must be private.")
			continue
		if response.status_code != 404:
			raise RuntimeError(f"Could not inspect Storage bucket '{bucket}': HTTP {response.status_code}.")
		response = httpx.post(
			f"{settings.supabase_url.rstrip('/')}/storage/v1/bucket",
			headers={**headers, "Content-Type": "application/json"},
			json={"id": bucket, "name": bucket, "public": False},
			timeout=20.0,
		)
		if response.status_code not in (200, 201, 409):
			raise RuntimeError(f"Could not create private Storage bucket '{bucket}': HTTP {response.status_code}.")
		created.append(bucket)
	return created


def upload_bytes(bucket: str, object_path: str, content: bytes, content_type: str) -> None:
	headers = _auth_headers()
	headers.update({"Content-Type": content_type, "x-upsert": "true"})
	response = httpx.post(_object_url(bucket, object_path), headers=headers, content=content, timeout=60.0)
	if response.status_code not in (200, 201):
		raise RuntimeError(f"Supabase Storage upload failed: HTTP {response.status_code}.")


def download_bytes(bucket: str, object_path: str) -> bytes:
	response = httpx.get(_object_url(bucket, object_path), headers=_auth_headers(), timeout=60.0)
	if response.status_code == 404:
		raise FileNotFoundError(object_path)
	if response.status_code >= 400:
		raise RuntimeError(f"Supabase Storage download failed: HTTP {response.status_code}.")
	return response.content


def delete_object(bucket: str, object_path: str) -> None:
	response = httpx.delete(
		f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{quote(bucket, safe='')}",
		headers={**_auth_headers(), "Content-Type": "application/json"},
		json={"prefixes": [object_path.lstrip("/")]},
		timeout=30.0,
	)
	if response.status_code not in (200, 204, 404):
		raise RuntimeError(f"Supabase Storage delete failed: HTTP {response.status_code}.")


def ensure_local_file(local_path: Path, storage_bucket: str, object_path: str) -> Path:
	resolved = local_path.resolve()
	if local_path.exists():
		return resolved
	if not configured():
		raise FileNotFoundError(object_path)
	content = download_bytes(storage_bucket, object_path)
	resolved.parent.mkdir(parents=True, exist_ok=True)
	resolved.write_bytes(content)
	return resolved
