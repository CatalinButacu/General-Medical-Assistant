"""End-to-end tests for /user/profile and /user/cabinet via FastAPI TestClient.

Covers the auth boundary and the per-user data-isolation invariant — these
are the two things a recruiter would worry about most.
"""

from __future__ import annotations

import os

# Required env vars for med_assist.auth.jwt to import without raising.
# Tests override the dependency itself so the actual values don't matter.
os.environ.setdefault("AUTH0_DOMAIN", "test.example.auth0.com")
os.environ.setdefault("AUTH0_AUDIENCE", "https://test-api")


# ───────────────── auth boundary ─────────────────


def test_profile_get_anonymous_returns_401(anon_client):
    resp = anon_client.get("/user/profile")
    assert resp.status_code == 401


def test_cabinet_get_anonymous_returns_401(anon_client):
    resp = anon_client.get("/user/cabinet")
    assert resp.status_code == 401


# ───────────────── profile round-trip ─────────────────


def test_profile_get_when_empty_returns_default(client):
    resp = client.get("/user/profile")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == "default-test-user"
    assert body["allergies"] == []
    assert body["onboarded"] in (False, None)


def test_profile_put_then_get_returns_what_was_saved(client):
    payload = {
        "name": "Catalin",
        "age": 28,
        "gender": "male",
        "isPregnant": False,
        "allergies": ["penicilină"],
        "conditions": ["gastrită"],
        "medications": [],
        "onboarded": True,
    }
    resp = client.put("/user/profile", json=payload)
    assert resp.status_code == 200
    saved = resp.json()
    assert saved["name"] == "Catalin"
    assert saved["allergies"] == ["penicilină"]

    resp2 = client.get("/user/profile")
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "Catalin"
    assert resp2.json()["onboarded"] is True


# ───────────────── cabinet CRUD ─────────────────


def test_cabinet_post_then_get_lists_the_item(client):
    create = client.post(
        "/user/cabinet",
        json={
            "name": "Paracetamol",
            "generic_name": "Paracetamolum",
            "dosage": "500mg",
            "item_type": "tablet",
            "quantity": 20,
            "expiration_date": "2027-12-31",
            "notes": None,
        },
    )
    assert create.status_code == 201
    item_id = create.json()["id"]
    assert item_id

    listed = client.get("/user/cabinet")
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    assert items[0]["name"] == "Paracetamol"
    assert items[0]["expiration_date"] == "2027-12-31"


def test_cabinet_put_updates_an_item(client):
    create = client.post("/user/cabinet", json={
        "name": "Nurofen", "quantity": 1, "expiration_date": "2027-06-30"
    })
    item_id = create.json()["id"]

    updated = client.put(f"/user/cabinet/{item_id}", json={
        "name": "Nurofen Forte", "quantity": 24, "expiration_date": "2027-06-30"
    })
    assert updated.status_code == 200
    assert updated.json()["name"] == "Nurofen Forte"
    assert updated.json()["quantity"] == 24


def test_cabinet_delete_removes_the_item(client):
    create = client.post("/user/cabinet", json={
        "name": "Algocalmin", "quantity": 1, "expiration_date": "2027-01-01"
    })
    item_id = create.json()["id"]

    delete = client.delete(f"/user/cabinet/{item_id}")
    assert delete.status_code == 204

    listed = client.get("/user/cabinet")
    assert listed.json() == []


# ───────────────── per-user data isolation (the security invariant) ─────────────────


def test_user_cannot_read_other_users_cabinet(app, as_user):
    """User A's items must NOT appear in user B's cabinet listing."""
    from fastapi.testclient import TestClient

    as_user("alice")
    alice = TestClient(app)
    alice.post("/user/cabinet", json={
        "name": "Alice's medicine", "quantity": 1, "expiration_date": "2027-01-01"
    })

    as_user("bob")
    bob = TestClient(app)
    bob_items = bob.get("/user/cabinet").json()
    assert bob_items == []


def test_user_cannot_delete_other_users_cabinet_item(app, as_user):
    """User A creates an item; user B tries to DELETE it by id and gets 404."""
    from fastapi.testclient import TestClient

    as_user("alice")
    alice = TestClient(app)
    create = alice.post("/user/cabinet", json={
        "name": "Alice's medicine", "quantity": 1, "expiration_date": "2027-01-01"
    })
    alice_item_id = create.json()["id"]

    as_user("bob")
    bob = TestClient(app)
    delete = bob.delete(f"/user/cabinet/{alice_item_id}")
    assert delete.status_code == 404

    # Confirm Alice's item still exists
    as_user("alice")
    alice2 = TestClient(app)
    listed = alice2.get("/user/cabinet").json()
    assert len(listed) == 1


def test_profiles_are_scoped_per_user(app, as_user):
    """Two users save different profiles; each reads their own."""
    from fastapi.testclient import TestClient

    as_user("alice")
    TestClient(app).put("/user/profile", json={
        "name": "Alice", "allergies": ["penicilină"], "conditions": [], "medications": [],
    })

    as_user("bob")
    TestClient(app).put("/user/profile", json={
        "name": "Bob", "allergies": ["aspirină"], "conditions": [], "medications": [],
    })

    as_user("alice")
    alice_profile = TestClient(app).get("/user/profile").json()
    assert alice_profile["name"] == "Alice"
    assert alice_profile["allergies"] == ["penicilină"]
