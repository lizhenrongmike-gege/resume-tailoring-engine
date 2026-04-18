def test_finish_batch(client):
    client.post("/api/jobs", json={"company": "A", "title": "R1", "description": "JD1"})
    client.post("/api/jobs", json={"company": "B", "title": "R2", "description": "JD2"})

    resp = client.post("/api/batches/finish")
    assert resp.status_code == 200
    data = resp.json()
    assert data["jobs_count"] == 2
    assert data["batch_id"] is not None
    assert data["export_ready"] is True

    # Jobs should now be 'applied', not 'active_batch'
    resp = client.get("/api/jobs?status=active_batch")
    assert len(resp.json()) == 0

    resp = client.get("/api/jobs?status=applied")
    assert len(resp.json()) == 2

def test_finish_empty_batch(client):
    resp = client.post("/api/batches/finish")
    assert resp.status_code == 400

def test_export_batch_jds(client):
    client.post("/api/jobs", json={
        "company": "TestCo",
        "title": "Eng",
        "description": "Build things",
        "application_url": "https://test.com",
        "location": "Remote",
    })
    client.post("/api/batches/finish")

    resp = client.get("/api/export/batch_jds")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
