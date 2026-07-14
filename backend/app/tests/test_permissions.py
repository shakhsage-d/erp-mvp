"""
tests/test_permissions.py
----------------------------
Xodim qo'shish va rol-asosidagi ruxsatlarni tekshiradi:
egasi (owner) hamma narsani qila oladi, sotuvchi (cashier) esa
moliyaviy ma'lumotga kira olmaydi va yangi xodim qo'sha olmaydi.
"""


def _login(client, phone, password):
    resp = client.post("/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_owner_can_add_employee(client):
    resp = client.post("/auth/users", json={
        "full_name": "Sotuvchi Vali", "phone": "+998955555501",
        "password": "sotuvchi123", "role": "cashier",
    })
    assert resp.status_code == 200
    assert resp.json()["role"] == "cashier"


def test_owner_can_list_employees(client):
    client.post("/auth/users", json={
        "full_name": "Omborchi", "phone": "+998955555502",
        "password": "parol123", "role": "storekeeper",
    })
    resp = client.get("/auth/users")
    assert resp.status_code == 200
    roles = [u["role"] for u in resp.json()]
    assert "owner" in roles
    assert "storekeeper" in roles


def test_cashier_cannot_add_employee(client):
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998955555503",
        "password": "parol123", "role": "cashier",
    })
    cashier_headers = _login(client, "+998955555503", "parol123")

    resp = client.post(
        "/auth/users",
        json={"full_name": "Yana biri", "phone": "+998955555504", "password": "parol123", "role": "cashier"},
        headers=cashier_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_cashier_cannot_view_finance_summary(client):
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998955555505",
        "password": "parol123", "role": "cashier",
    })
    cashier_headers = _login(client, "+998955555505", "parol123")

    resp = client.get("/finance/summary", headers=cashier_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_cashier_can_still_make_sales(client):
    """Rol cheklovi faqat moliyaviy HISOBOTGA tegishli — sotuvchi baribir
    sotuv qila olishi kerak, chunki bu uning ish vazifasi."""
    product = client.post("/inventory/products", json={
        "name": "Non", "sale_price": 3000, "quantity": 10,
    }).json()
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998955555506",
        "password": "parol123", "role": "cashier",
    })
    cashier_headers = _login(client, "+998955555506", "parol123")

    resp = client.post(
        "/sales/",
        json={"items": [{"product_id": product["id"], "quantity": 1}]},
        headers=cashier_headers,
    )
    assert resp.status_code == 200


def test_cashier_cannot_manage_inventory(client):
    """Sotuvchi mahsulot qo'sha yoki ombor kirimi qila olmasligi kerak —
    bu omborchining vazifasi."""
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998955555507",
        "password": "parol123", "role": "cashier",
    })
    cashier_headers = _login(client, "+998955555507", "parol123")

    resp = client.post(
        "/inventory/products",
        json={"name": "Yangi mahsulot", "sale_price": 1000},
        headers=cashier_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_storekeeper_can_manage_inventory(client):
    """Omborchi mahsulot qo'sha va ombor kirimi qila olishi kerak."""
    client.post("/auth/users", json={
        "full_name": "Omborchi", "phone": "+998955555508",
        "password": "parol123", "role": "storekeeper",
    })
    storekeeper_headers = _login(client, "+998955555508", "parol123")

    resp = client.post(
        "/inventory/products",
        json={"name": "Kartoshka", "sale_price": 4000, "quantity": 20},
        headers=storekeeper_headers,
    )
    assert resp.status_code == 200


def test_storekeeper_cannot_make_sale(client):
    """Omborchi sotuv qila olmasligi kerak — bu sotuvchining vazifasi."""
    product = client.post("/inventory/products", json={
        "name": "Sabzi", "sale_price": 2000, "quantity": 15,
    }).json()
    client.post("/auth/users", json={
        "full_name": "Omborchi", "phone": "+998955555509",
        "password": "parol123", "role": "storekeeper",
    })
    storekeeper_headers = _login(client, "+998955555509", "parol123")

    resp = client.post(
        "/sales/",
        json={"items": [{"product_id": product["id"], "quantity": 1}]},
        headers=storekeeper_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"
