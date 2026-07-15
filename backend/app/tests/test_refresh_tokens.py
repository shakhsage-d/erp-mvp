"""
tests/test_refresh_tokens.py
-------------------------------
Refresh token orqali yangi access token olish, tokenlarni "rotation"
qilish, va logout to'g'ri ishlayotganini tekshiradi.
"""


def _register(client, phone="+998911100001"):
    resp = client.post("/auth/register", json={
        "company_name": "Refresh Test", "owner_full_name": "Egasi",
        "phone": phone, "password": "parol123",
    })
    assert resp.status_code == 200
    return resp.json()


def test_register_returns_both_tokens(client):
    data = _register(client)
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_token_issues_new_access_token(client):
    data = _register(client, phone="+998911100002")
    resp = client.post("/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert resp.status_code == 200
    new_data = resp.json()
    assert "access_token" in new_data
    assert "refresh_token" in new_data
    # MUHIM xavfsizlik xossasi — refresh token har safar YANGILANISHI
    # (rotation) kerak. Access token esa bir xil soniyada yaratilgan
    # bo'lsa, mazmuni bir xil bo'lishi mumkin (bu muammo emas — JWT
    # baribir muddati tugagach avtomatik yaroqsiz bo'ladi).
    assert new_data["refresh_token"] != data["refresh_token"]


def test_old_refresh_token_cannot_be_reused_after_rotation(client):
    data = _register(client, phone="+998911100003")
    client.post("/auth/refresh", json={"refresh_token": data["refresh_token"]})

    # Eski (allaqachon ishlatilgan) refresh token endi ishlamasligi kerak
    resp = client.post("/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert resp.status_code == 401


def test_invalid_refresh_token_is_rejected(client):
    resp = client.post("/auth/refresh", json={"refresh_token": "bu-yolgon-token"})
    assert resp.status_code == 401


def test_new_access_token_from_refresh_actually_works(client):
    data = _register(client, phone="+998911100004")
    refreshed = client.post("/auth/refresh", json={"refresh_token": data["refresh_token"]}).json()

    resp = client.get(
        "/inventory/products",
        headers={"Authorization": f"Bearer {refreshed['access_token']}"},
    )
    assert resp.status_code == 200


def test_logout_revokes_refresh_token(client):
    data = _register(client, phone="+998911100005")
    resp = client.post("/auth/logout", json={"refresh_token": data["refresh_token"]})
    assert resp.status_code == 200

    # Chiqilgandan keyin shu refresh token bilan yangilab bo'lmasligi kerak
    resp = client.post("/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert resp.status_code == 401


def test_logout_with_unknown_token_does_not_error(client):
    """Xavfsizlik: noma'lum token bilan logout ham "muvaffaqiyatli" javob
    qaytarishi kerak — bu orqali tokenning bazada bor-yo'qligi haqida
    ma'lumot oshkor bo'lmaydi."""
    resp = client.post("/auth/logout", json={"refresh_token": "hech-qachon-mavjud-bolmagan"})
    assert resp.status_code == 200
