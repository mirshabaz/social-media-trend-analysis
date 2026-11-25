from io import BytesIO
import uuid

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def auth_headers():
	email = f"qa-{uuid.uuid4().hex}@example.com"
	response = client.post("/api/auth/register", json={
		"email": email,
		"password": "SmokeTest123!",
		"full_name": "QA Smoke",
		"role": "QA Analyst",
		"organization": "SOCIALPULSE",
	})
	assert response.status_code == 201
	return {"Authorization": f"Bearer {response.json()['token']}"}


def test_database_and_core_analytics_endpoints():
	for path in [
		"/api/datasets", "/api/dataset", "/api/overview", "/api/trends",
		"/api/sentiment", "/api/engagement", "/api/platforms", "/api/hashtags",
		"/api/topics", "/api/time-analysis", "/api/anomalies", "/api/posts",
		"/api/insights", "/api/search?q=platform", "/api/notifications",
	]:
		response = client.get(path)
		assert response.status_code == 200, (path, response.text)


def test_authenticated_profile_search_assistant_and_reports():
	headers = auth_headers()

	me = client.get("/api/auth/me", headers=headers)
	assert me.status_code == 200

	profile = client.put("/api/auth/profile", headers=headers, json={
		"full_name": "QA Updated",
		"role": "Senior QA",
		"organization": "SOCIALPULSE QA",
		"bio": "Automated end-to-end audit",
	})
	assert profile.status_code == 200

	password = client.put("/api/auth/password", headers=headers, json={
		"current_password": "SmokeTest123!",
		"new_password": "UpdatedTest123!",
	})
	assert password.status_code == 200

	assistant = client.post("/api/assistant/query", headers=headers, json={
		"question": "Which platform has the highest engagement?"
	})
	assert assistant.status_code == 200
	assert assistant.json()["data"]["answer"]

	search = client.get("/api/search?q=instagram", headers=headers)
	assert search.status_code == 200

	for report_format in ("pdf", "xlsx", "csv", "json"):
		generated = client.post("/api/reports/generate", headers=headers, json={
			"report_type": "overall",
			"format": report_format,
			"title": f"QA {report_format} report",
		})
		assert generated.status_code == 200, generated.text
		report = generated.json()["report"]
		downloaded = client.get(f"/api/reports/{report['id']}/download", headers=headers)
		assert downloaded.status_code == 200
		assert len(downloaded.content) > 100


def test_upload_preview_clean_activate_switch_download_and_delete():
	headers = auth_headers()
	csv = (
		"post_id,platform,post_content,likes,shares,comments,author,timestamp\n"
		"QA1,Instagram,Launch day is exciting,10,2,1,Alice,2026-11-24\n"
		"QA2,LinkedIn,Revenue data is useful,20,5,3,Bob,2026-11-23\n"
		"QA2,LinkedIn,Revenue data is useful,20,5,3,Bob,2026-11-23\n"
		"QA3,Instagram,,7,1,0,Carol,2026-11-22\n"
	)

	preview = client.post("/api/upload/preview", headers=headers, files={
		"file": ("qa.csv", BytesIO(csv.encode("utf-8")), "text/csv")
	})
	assert preview.status_code == 200, preview.text

	uploaded = client.post("/api/upload", headers=headers, files={
		"file": ("qa.csv", BytesIO(csv.encode("utf-8")), "text/csv")
	}, data={"dataset_name": "QA Upload", "activate": "true"})
	assert uploaded.status_code == 200, uploaded.text
	dataset = uploaded.json()["dataset"]
	assert dataset["cleaned_row_count"] >= 2

	detail = client.get(f"/api/dataset/{dataset['id']}?limit=20", headers=headers)
	assert detail.status_code == 200

	activated = client.post(f"/api/dataset/{dataset['id']}/activate", headers=headers)
	assert activated.status_code == 200

	downloaded = client.get(f"/api/dataset/{dataset['id']}/download?cleaned=true", headers=headers)
	assert downloaded.status_code == 200
	assert b"post_id" in downloaded.content

	datasets = client.get("/api/datasets", headers=headers)
	assert datasets.status_code == 200

	deleted = client.delete(f"/api/dataset/{dataset['id']}", headers=headers)
	assert deleted.status_code == 200
