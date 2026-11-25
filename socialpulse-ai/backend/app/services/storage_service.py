from pathlib import Path

import httpx

from app.core.config import settings


def storage_configured() -> bool:
	return bool(settings.supabase_url and settings.supabase_service_key)


def _headers() -> dict[str, str]:
	return {
		"apikey": settings.supabase_service_key,
		"Authorization": f"Bearer {settings.supabase_service_key}",
	}


def upload_bytes(path: str, content: bytes, content_type: str) -> bool:
	if not storage_configured():
		return False
	url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{settings.supabase_storage_bucket}/{path.lstrip('/')}"
	headers = _headers()
	headers["Content-Type"] = content_type
	response = httpx.post(url, headers=headers, content=content, timeout=30.0)
	if response.status_code not in (200, 201):
		raise RuntimeError(f"Supabase upload failed: {response.status_code}")
	return True


def download_bytes(path: str) -> bytes:
	if not storage_configured():
		raise FileNotFoundError(path)
	url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{settings.supabase_storage_bucket}/{path.lstrip('/')}"
	response = httpx.get(url, headers=_headers(), timeout=30.0)
	if response.status_code == 404:
		raise FileNotFoundError(path)
	if response.status_code >= 400:
		raise RuntimeError(f"Supabase download failed: {response.status_code}")
	return response.content


def ensure_local_file(local_path: Path, storage_path: str) -> Path:
	if local_path.exists():
		return local_path
	content = download_bytes(storage_path)
	local_path.parent.mkdir(parents=True, exist_ok=True)
	local_path.write_bytes(content)
	return local_path
