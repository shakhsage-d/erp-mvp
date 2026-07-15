"""
tests/test_employee_management.py
------------------------------------
Xodimni tahrirlash va faolsizlantirish/qayta faollashtirishni tekshiradi.
"""


def _login(client, phone, password):
    resp = client.post("/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _add_employee(client, phone="+998977000001", role="cashier"):
    resp = client.post("/auth/users", json={
        "full_name": "Test Xodim", "phone": phone, "password": "parol123", "role": role,
    })
    assert resp.status_code == 200
    return resp.json()


def test_owner_can_update_employee_name_and_role(client):
    employee = _add_employee(client)
    resp = client.patch(f"/auth/users/{employee['id']}", json={
        "full_name": "Yangilangan Ism", "role": "storekeeper",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Yangilangan Ism"
    assert data["role"] == "storekeeper"


def test_updating_phone_to_existing_one_is_rejected(client):
    emp1 = _add_employee(client, phone="+998977000002")
    _add_employee(client, phone="+998977000003")

    resp = client.patch(f"/auth/users/{emp1['id']}", json={"phone": "+998977000003"})
    assert resp.status_code == 409


def test_cannot_update_owner_via_employee_endpoint(client):
    # 1-user (owner) o'zining id'sini bilish uchun /auth/users orqali topamiz
    users = client.get("/auth/users").json()
    owner = next(u for u in users if u["role"] == "owner")

    resp = client.patch(f"/auth/users/{owner['id']}", json={"full_name": "Yangi"})
    assert resp.status_code == 403


def test_deactivate_employee_prevents_login(client):
    employee = _add_employee(client, phone="+998977000004")

    resp = client.post(f"/auth/users/{employee['id']}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # Endi shu xodim login qila olmasligi kerak
    login_resp = client.post("/auth/login", json={
        "phone": "+998977000004", "password": "parol123",
    })
    assert login_resp.status_code == 401


def test_reactivate_employee_restores_login(client):
    employee = _add_employee(client, phone="+998977000005")
    client.post(f"/auth/users/{employee['id']}/deactivate")

    resp = client.post(f"/auth/users/{employee['id']}/reactivate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True

    login_resp = client.post("/auth/login", json={
        "phone": "+998977000005", "password": "parol123",
    })
    assert login_resp.status_code == 200


def test_cannot_deactivate_self(client):
    users = client.get("/auth/users").json()
    owner = next(u for u in users if u["role"] == "owner")

    resp = client.post(f"/auth/users/{owner['id']}/deactivate")
    assert resp.status_code == 403


def test_cashier_cannot_deactivate_employees(client):
    employee = _add_employee(client, phone="+998977000006")
    other_employee = _add_employee(client, phone="+998977000007")

    cashier_headers = _login(client, "+998977000006", "parol123")
    resp = client.post(
        f"/auth/users/{other_employee['id']}/deactivate",
        headers=cashier_headers,
    )
    assert resp.status_code == 403
