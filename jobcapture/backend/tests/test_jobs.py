def test_create_job(client):
    resp = client.post("/api/jobs", json={
        "company": "OpenAI",
        "title": "ML Engineer",
        "location": "San Francisco, CA",
        "source_site": "linkedin",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["company"] == "OpenAI"
    assert data["status"] == "active_batch"
    assert data["id"] is not None

def test_list_jobs_filtered(client):
    client.post("/api/jobs", json={"company": "A", "title": "Role A"})
    client.post("/api/jobs", json={"company": "B", "title": "Role B"})

    resp = client.get("/api/jobs?status=active_batch")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = client.get("/api/jobs?status=applied")
    assert resp.status_code == 200
    assert len(resp.json()) == 0

def test_delete_job(client):
    resp = client.post("/api/jobs", json={"company": "X", "title": "Y"})
    job_id = resp.json()["id"]

    resp = client.delete(f"/api/jobs/{job_id}")
    assert resp.status_code == 204

    resp = client.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 404

def test_update_job(client):
    resp = client.post("/api/jobs", json={"company": "X", "title": "Y"})
    job_id = resp.json()["id"]

    resp = client.patch(f"/api/jobs/{job_id}", json={"team": "Risk Team"})
    assert resp.status_code == 200
    assert resp.json()["team"] == "Risk Team"
