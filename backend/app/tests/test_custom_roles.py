"""
tests/test_custom_roles.py
------------------------------
Maxsus lavozim yaratish interfeysini tekshiradi — bu dinamik
ruxsatlar tizimining (Permission/Role/RolePermission) haqiqiy
sinovi: yangi lavozim, checkbox orqali tanlangan ruxsatlar bilan.
"""


def _login(client, phone, password):
    resp = client.post("/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_list_permissions_catalog(client):
    resp = client.get("/permissions")
    assert resp.status_code == 200
    codes = [p["code"] for p in resp.json()]
    assert "sales.create" in codes
    assert "finance.view" in codes


def test_list_roles_includes_defaults(client):
    resp = client.get("/roles")
    assert resp.status_code == 200
    names = [r["name"] for r in resp.json()]
    assert "owner" in names
    assert "cashier" in names
    assert "storekeeper" in names


def test_create_custom_role(client):
    resp = client.post("/roles", json={
        "name": "Katta sotuvchi",
        "permission_codes": ["sales.create", "inventory.manage"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Katta sotuvchi"
    assert data["is_custom"] is True
    assert set(data["permission_codes"]) == {"sales.create", "inventory.manage"}


def test_custom_role_appears_in_roles_list(client):
    client.post("/roles", json={
        "name": "Nazoratchi", "permission_codes": ["finance.view"],
    })
    resp = client.get("/roles")
    names = [r["name"] for r in resp.json()]
    assert "Nazoratchi" in names


def test_duplicate_custom_role_name_is_rejected(client):
    client.post("/roles", json={"name": "Nazoratchi2", "permission_codes": ["finance.view"]})
    resp = client.post("/roles", json={"name": "Nazoratchi2", "permission_codes": ["sales.create"]})
    assert resp.status_code == 409


def test_invalid_permission_code_is_rejected(client):
    resp = client.post("/roles", json={
        "name": "Xato lavozim", "permission_codes": ["mavjud.emas.ruxsat"],
    })
    assert resp.status_code == 409


def test_employee_can_be_assigned_custom_role(client):
    role = client.post("/roles", json={
        "name": "Katta sotuvchi", "permission_codes": ["sales.create", "inventory.manage"],
    }).json()

    resp = client.post("/auth/users", json={
        "full_name": "Vali", "phone": "+998900888001", "password": "parol123",
        "custom_role_id": role["id"],
    })
    assert resp.status_code == 200
    assert resp.json()["role"] == "Katta sotuvchi"


def test_employee_with_custom_role_gets_correct_permissions(client):
    role = client.post("/roles", json={
        "name": "Katta sotuvchi", "permission_codes": ["sales.create", "inventory.manage"],
    }).json()
    client.post("/auth/users", json={
        "full_name": "Vali", "phone": "+998900888002", "password": "parol123",
        "custom_role_id": role["id"],
    })
    headers = _login(client, "+998900888002", "parol123")

    # sales.create bor -> ruxsat berilishi kerak
    product = client.post("/inventory/products", json={
        "name": "Test", "sale_price": 1000, "quantity": 10,
    }).json()
    resp = client.post(
        "/sales/", json={"items": [{"product_id": product["id"], "quantity": 1}]},
        headers=headers,
    )
    assert resp.status_code == 200

    # finance.view YO'Q -> rad etilishi kerak
    resp = client.get("/finance/summary", headers=headers)
    assert resp.status_code == 403


def test_cashier_cannot_create_custom_roles(client):
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998900888003",
        "password": "parol123", "role": "cashier",
    })
    cashier_headers = _login(client, "+998900888003", "parol123")

    resp = client.post(
        "/roles", json={"name": "Sinov", "permission_codes": ["sales.create"]},
        headers=cashier_headers,
    )
    assert resp.status_code == 403


def test_custom_roles_isolated_per_company(client):
    from .conftest import other_company_headers

    client.post("/roles", json={"name": "Faqat 1-kompaniya", "permission_codes": ["sales.create"]})

    other_headers = other_company_headers(client)
    resp = client.get("/roles", headers=other_headers)
    names = [r["name"] for r in resp.json()]
    assert "Faqat 1-kompaniya" not in names
