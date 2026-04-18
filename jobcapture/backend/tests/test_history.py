def _create_and_finish_batch(client):
    """Helper: create jobs and finish batch so history entries exist."""
    client.post("/api/jobs", json={"company": "A", "title": "R1", "description": "JD"})
    client.post("/api/jobs", json={"company": "B", "title": "R2", "description": "JD"})
    client.post("/api/batches/finish")

def test_list_history(client):
    _create_and_finish_batch(client)
    resp = client.get("/api/history")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

def test_list_history_with_outcome_filter(client):
    _create_and_finish_batch(client)
    history = client.get("/api/history").json()
    client.patch(f"/api/history/{history[0]['id']}", json={"outcome": "interviewing"})

    resp = client.get("/api/history?outcome=interviewing")
    assert len(resp.json()) == 1

def test_update_history_outcome(client):
    _create_and_finish_batch(client)
    history = client.get("/api/history").json()
    entry_id = history[0]["id"]

    resp = client.patch(f"/api/history/{entry_id}", json={"outcome": "offered"})
    assert resp.status_code == 200
    assert resp.json()["outcome"] == "offered"
