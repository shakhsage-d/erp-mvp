"""
tests/test_company_settings.py
----------------------------------
Kompaniya profilini ko'rish va tahrirlashni tekshiradi.
"""


def _login(client, phone, password):
    resp = client.post("/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_any_authenticated_user_can_view_company(client):
    resp = client.get("/auth/company")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Do'kon 1"


def test_owner_can_update_company_name(client):
    resp = client.patch("/auth/company", json={"name": "Yangilangan Do'kon Nomi"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Yangilangan Do'kon Nomi"

    resp = client.get("/auth/company")
    assert resp.json()["name"] == "Yangilangan Do'kon Nomi"


def test_owner_can_update_tax_id(client):
    resp = client.patch("/auth/company", json={"tax_id": "123456789"})
    assert resp.status_code == 200
    assert resp.json()["tax_id"] == "123456789"


def test_cashier_cannot_update_company(client):
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998900444001",
        "password": "parol123", "role": "cashier",
    })
    cashier_headers = _login(client, "+998900444001", "parol123")

    resp = client.patch(
        "/auth/company",
        json={"name": "Sotuvchi o'zgartirmoqchi"},
        headers=cashier_headers,
    )
    assert resp.status_code == 403


def test_cashier_can_still_view_company(client):
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998900444002",
        "password": "parol123", "role": "cashier",
    })
    cashier_headers = _login(client, "+998900444002", "parol123")

    resp = client.get("/auth/company", headers=cashier_headers)
    assert resp.status_code == 200


def test_company_update_writes_audit_entry(client):
    client.patch("/auth/company", json={"name": "Audit sinov"})
    resp = client.get("/audit-log?search=company")
    actions = [e["action"] for e in resp.json()["items"]]
    assert "company.update" in actions
