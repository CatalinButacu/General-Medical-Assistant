"""/user/chats — session CRUD, message append, per-user isolation, cascade delete."""

from __future__ import annotations


def test_anon_cannot_list(anon_client):
    r = anon_client.get("/user/chats")
    assert r.status_code == 401


def test_create_then_list(client):
    r = client.post("/user/chats", json={"title": "Headache"})
    assert r.status_code == 201
    sid = r.json()["id"]

    r = client.get("/user/chats")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["id"] == sid
    assert items[0]["title"] == "Headache"
    assert items[0]["message_count"] == 0


def test_append_messages_and_fetch_in_order(client):
    sid = client.post("/user/chats", json={}).json()["id"]
    client.post(f"/user/chats/{sid}/messages", json={"role": "user", "text": "Ma doare capul"})
    client.post(f"/user/chats/{sid}/messages", json={"role": "assistant", "text": "De cand?"})
    client.post(f"/user/chats/{sid}/messages", json={"role": "user", "text": "De 2 zile"})

    r = client.get(f"/user/chats/{sid}")
    assert r.status_code == 200
    msgs = r.json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
    assert msgs[0]["text"] == "Ma doare capul"


def test_first_user_message_auto_titles_session(client):
    sid = client.post("/user/chats", json={}).json()["id"]
    assert client.get("/user/chats").json()[0]["title"] is None

    client.post(f"/user/chats/{sid}/messages", json={"role": "user", "text": "Tuse seaca de o saptamana"})
    listing = client.get("/user/chats").json()
    assert listing[0]["title"] == "Tuse seaca de o saptamana"

    # A later user message must NOT overwrite the auto-generated title.
    client.post(f"/user/chats/{sid}/messages", json={"role": "user", "text": "Si febra"})
    assert client.get("/user/chats").json()[0]["title"] == "Tuse seaca de o saptamana"


def test_message_count_increments(client):
    sid = client.post("/user/chats", json={}).json()["id"]
    for i in range(3):
        client.post(f"/user/chats/{sid}/messages", json={"role": "user", "text": f"m{i}"})
    assert client.get("/user/chats").json()[0]["message_count"] == 3


def test_user_isolation(app, as_user):
    from fastapi.testclient import TestClient

    as_user("alice")
    alice = TestClient(app)
    sid = alice.post("/user/chats", json={"title": "alice's chat"}).json()["id"]

    as_user("bob")
    bob = TestClient(app)
    assert bob.get("/user/chats").json() == []
    assert bob.get(f"/user/chats/{sid}").status_code == 404
    assert bob.post(f"/user/chats/{sid}/messages", json={"role": "user", "text": "hi"}).status_code == 404
    assert bob.delete(f"/user/chats/{sid}").status_code == 404


def test_delete_cascades_messages(client):
    sid = client.post("/user/chats", json={}).json()["id"]
    client.post(f"/user/chats/{sid}/messages", json={"role": "user", "text": "x"})
    assert client.delete(f"/user/chats/{sid}").status_code == 204
    assert client.get(f"/user/chats/{sid}").status_code == 404
    assert client.get("/user/chats").json() == []


def test_message_role_validated(client):
    sid = client.post("/user/chats", json={}).json()["id"]
    r = client.post(f"/user/chats/{sid}/messages", json={"role": "system", "text": "x"})
    assert r.status_code == 422
