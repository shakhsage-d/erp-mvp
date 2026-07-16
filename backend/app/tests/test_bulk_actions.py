"""
tests/test_bulk_actions.py
------------------------------
Bir nechta xodimni birga faolsizlantirishni tekshiradi.
"""


def _login(client, phone, password):
    resp = client.post("/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _add_employee(client, phone):
    return client.post("/auth/users", json={
        "full_name": "Xodim", "phone": phone, "password": "parol123", "role": "cashier",
    }).json()


def test_bulk_deactivate_multiple_employees(client):
    emp1 = _add_employee(client, "+998900999001")
    emp2 = _add_employee(client, "+998900999002")

    resp = client.post("/auth/users/bulk-deactivate", json={
        "user_ids": [emp1["id"], emp2["id"]],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["deactivated_count"] == 2
    assert data["skipped_ids"] == []

    for emp_phone in ["+998900999001", "+998900999002"]:
        login_resp = client.post("/auth/login", json={"phone": emp_phone, "password": "parol123"})
        assert login_resp.status_code == 401


def test_bulk_deactivate_skips_owner_and_self(client):
    users = client.get("/auth/users").json()
    owner = next(u for u in users if u["role"] == "owner")
    emp = _add_employee(client, "+998900999003")

    resp = client.post("/auth/users/bulk-deactivate", json={
        "user_ids": [owner["id"], emp["id"]],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["deactivated_count"] == 1
    assert owner["id"] in data["skipped_ids"]


def test_bulk_deactivate_writes_single_audit_entry(client):
    emp1 = _add_employee(client, "+998900999004")
    emp2 = _add_employee(client, "+998900999005")

    client.post("/auth/users/bulk-deactivate", json={"user_ids": [emp1["id"], emp2["id"]]})

    resp = client.get("/audit-log?search=bulk_deactivate")
    actions = [e["action"] for e in resp.json()["items"]]
    assert "employee.bulk_deactivate" in actions
    assert actions.count("employee.bulk_deactivate") == 1


def test_cashier_cannot_bulk_deactivate(client):
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998900999006",
        "password": "parol123", "role": "cashier",
    })
    emp2 = _add_employee(client, "+998900999007")
    cashier_headers = _login(client, "+998900999006", "parol123")

    resp = client.post(
        "/auth/users/bulk-deactivate", json={"user_ids": [emp2["id"]]},
        headers=cashier_headers,
    )
    assert resp.status_code == 403
