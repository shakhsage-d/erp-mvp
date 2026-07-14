"""
tests/test_auth.py
--------------------
Ro'yxatdan o'tish, login va himoyalangan endpointlarga kirish huquqini
tekshiradi.
"""


def test_register_returns_token(client):
    """`client` fixture allaqachon ro'yxatdan o'tgan (conftest.py orqali) —
    shuning uchun bu yerda IKKINCHI, alohida ro'yxatdan o'tishni tekshiramiz."""
    resp = client.post("/auth/register", json={
        "company_name": "Yangi Kafe",
        "owner_full_name": "Aziz",
        "phone": "+998911111111",
        "password": "parol123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["company_name"] == "Yangi Kafe"
    assert data["role"] == "owner"


def test_register_with_duplicate_phone_is_rejected(client):
    client.post("/auth/register", json={
        "company_name": "Birinchi", "owner_full_name": "A",
        "phone": "+998922222222", "password": "parol123",
    })
    resp = client.post("/auth/register", json={
        "company_name": "Ikkinchi", "owner_full_name": "B",
        "phone": "+998922222222", "password": "boshqaparol",
    })
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


def test_login_with_correct_credentials_succeeds(client):
    client.post("/auth/register", json={
        "company_name": "Mening Do'konim", "owner_full_name": "Vali",
        "phone": "+998933333333", "password": "toGriParol1",
    })
    resp = client.post("/auth/login", json={
        "phone": "+998933333333", "password": "toGriParol1",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_with_wrong_password_is_rejected(client):
    client.post("/auth/register", json={
        "company_name": "Do'kon", "owner_full_name": "Vali",
        "phone": "+998944444444", "password": "toGriParol1",
    })
    resp = client.post("/auth/login", json={
        "phone": "+998944444444", "password": "notoGriParol",
    })
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_login_with_unknown_phone_is_rejected(client):
    resp = client.post("/auth/login", json={
        "phone": "+998900000000", "password": "harqanaqa",
    })
    assert resp.status_code == 401


def test_protected_endpoint_without_token_is_rejected(client):
    """Token yubormasdan himoyalangan endpointga murojaat qilish rad etilishi kerak."""
    resp = client.get("/inventory/products", headers={"Authorization": ""})
    assert resp.status_code in (401, 403)  # HTTPBearer yo'q tokenni odatda 403 deb belgilaydi


def test_protected_endpoint_with_garbage_token_is_rejected(client):
    resp = client.get(
        "/inventory/products",
        headers={"Authorization": "Bearer bu-token-emas-shunchaki-matn"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"
