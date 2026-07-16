"""
tests/test_suppliers.py
--------------------------
Ta'minotchilar va xarid buyurtmalarining to'liq hayot sikli, va
WMS+FMS bilan chuqur integratsiyasini tekshiradi.
"""


def _login(client, phone, password):
    resp = client.post("/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_supplier(client, name="Ta'minotchi A"):
    return client.post("/suppliers", json={"name": name}).json()


def test_create_supplier(client):
    resp = client.post("/suppliers", json={
        "name": "Guruch Trade", "contact_person": "Aziz", "phone": "+998900000010",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Guruch Trade"


def test_create_purchase_order_does_not_affect_stock_yet(client):
    supplier = _make_supplier(client)
    product = client.post("/inventory/products", json={
        "name": "Guruch", "sale_price": 15000, "quantity": 10,
    }).json()

    resp = client.post("/purchase-orders", json={
        "supplier_id": supplier["id"],
        "items": [{"product_id": product["id"], "quantity": 50, "unit_price": 10000}],
    })
    assert resp.status_code == 200
    order = resp.json()
    assert order["status"] == "ordered"
    assert order["total_amount"] == 500000

    # Hali qabul qilinmagani uchun, ombor va moliya o'zgarmasligi kerak
    products = client.get("/inventory/products").json()["items"]
    assert products[0]["quantity"] == 10

    summary = client.get("/finance/summary").json()
    assert summary["total_expense"] == 0


def test_receiving_order_updates_stock_and_finance(client):
    supplier = _make_supplier(client)
    product = client.post("/inventory/products", json={
        "name": "Yog'", "sale_price": 20000, "quantity": 5,
    }).json()

    order = client.post("/purchase-orders", json={
        "supplier_id": supplier["id"],
        "items": [{"product_id": product["id"], "quantity": 30, "unit_price": 12000}],
    }).json()

    resp = client.post(f"/purchase-orders/{order['id']}/receive")
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"

    products = client.get("/inventory/products").json()["items"]
    assert products[0]["quantity"] == 35  # 5 + 30

    summary = client.get("/finance/summary").json()
    assert summary["total_expense"] == 360000  # 30 * 12000


def test_cannot_receive_order_twice(client):
    supplier = _make_supplier(client)
    product = client.post("/inventory/products", json={
        "name": "Sut", "sale_price": 8000, "quantity": 0,
    }).json()
    order = client.post("/purchase-orders", json={
        "supplier_id": supplier["id"],
        "items": [{"product_id": product["id"], "quantity": 10, "unit_price": 5000}],
    }).json()

    client.post(f"/purchase-orders/{order['id']}/receive")
    resp = client.post(f"/purchase-orders/{order['id']}/receive")
    assert resp.status_code == 409


def test_purchase_order_writes_audit_entry(client):
    supplier = _make_supplier(client)
    product = client.post("/inventory/products", json={
        "name": "Choy", "sale_price": 3000, "quantity": 0,
    }).json()
    order = client.post("/purchase-orders", json={
        "supplier_id": supplier["id"],
        "items": [{"product_id": product["id"], "quantity": 5, "unit_price": 2000}],
    }).json()
    client.post(f"/purchase-orders/{order['id']}/receive")

    resp = client.get("/audit-log?search=purchase_order")
    actions = [e["action"] for e in resp.json()["items"]]
    assert "purchase_order.receive" in actions


def test_storekeeper_can_manage_suppliers(client):
    client.post("/auth/users", json={
        "full_name": "Omborchi", "phone": "+998900777001",
        "password": "parol123", "role": "storekeeper",
    })
    storekeeper_headers = _login(client, "+998900777001", "parol123")

    resp = client.post(
        "/suppliers", json={"name": "Test Ta'minotchi"},
        headers=storekeeper_headers,
    )
    assert resp.status_code == 200


def test_cashier_cannot_manage_suppliers(client):
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998900777002",
        "password": "parol123", "role": "cashier",
    })
    cashier_headers = _login(client, "+998900777002", "parol123")

    resp = client.post(
        "/suppliers", json={"name": "Test"},
        headers=cashier_headers,
    )
    assert resp.status_code == 403


def test_suppliers_isolated_per_company(client):
    from .conftest import other_company_headers

    _make_supplier(client)
    other_headers = other_company_headers(client)
    resp = client.get("/suppliers", headers=other_headers)
    assert resp.json()["total"] == 0
