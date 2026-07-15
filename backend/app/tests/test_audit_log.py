"""
tests/test_audit_log.py
--------------------------
Audit tarixi to'g'ri yozilayotganini va faqat egasi ko'ra olishini
tekshiradi.
"""


def _login(client, phone, password):
    resp = client.post("/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_creating_employee_writes_audit_entry(client):
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998988000001",
        "password": "parol123", "role": "cashier",
    })

    resp = client.get("/audit-log")
    body = resp.json()
    actions = [e["action"] for e in body["items"]]
    assert "employee.create" in actions


def test_sale_writes_audit_entry_with_details(client):
    product = client.post("/inventory/products", json={
        "name": "Choy", "sale_price": 5000, "quantity": 10,
    }).json()
    client.post("/sales/", json={"items": [{"product_id": product["id"], "quantity": 2}]})

    resp = client.get("/audit-log?search=sale")
    body = resp.json()
    assert body["total"] >= 1
    assert "10000" in body["items"][0]["details"]  # 2 * 5000


def test_deactivate_and_reactivate_both_logged(client):
    employee = client.post("/auth/users", json={
        "full_name": "Omborchi", "phone": "+998988000002",
        "password": "parol123", "role": "storekeeper",
    }).json()

    client.post(f"/auth/users/{employee['id']}/deactivate")
    client.post(f"/auth/users/{employee['id']}/reactivate")

    resp = client.get("/audit-log")
    actions = [e["action"] for e in resp.json()["items"]]
    assert "employee.deactivate" in actions
    assert "employee.reactivate" in actions


def test_cashier_cannot_view_audit_log(client):
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998988000003",
        "password": "parol123", "role": "cashier",
    })
    cashier_headers = _login(client, "+998988000003", "parol123")

    resp = client.get("/audit-log", headers=cashier_headers)
    assert resp.status_code == 403


def test_audit_log_isolated_per_company(client):
    from .conftest import other_company_headers

    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998988000004",
        "password": "parol123", "role": "cashier",
    })

    other_headers = other_company_headers(client)
    resp = client.get("/audit-log", headers=other_headers)
    assert resp.json()["total"] == 0
