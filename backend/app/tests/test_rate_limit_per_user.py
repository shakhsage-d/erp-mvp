"""
tests/test_rate_limit_per_user.py
-------------------------------------
Rate limit endi FOYDALANUVCHI bo'yicha ekanini tekshiradi — bitta
foydalanuvchi chegarasini "band qilib qo'yishi" ikkinchisiga
ta'sir qilmasligi kerak (garchi ikkalasi ham xuddi shu "IP"dan —
testlarda hammasi `testserver` — kirayotgan bo'lsa ham).
"""


def _login(client, phone, password):
    resp = client.post("/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_rate_limit_is_isolated_per_user(client):
    # 1-foydalanuvchi (egasi, standart `client`) o'z chegarasini to'ldiradi
    last_status = None
    for _ in range(31):
        resp = client.post("/inventory/products", json={"name": "Sinov"})
        last_status = resp.status_code
    assert last_status == 429

    # Yangi xodim (2-foydalanuvchi) qo'shamiz — u hali chegarasini
    # ishlatmagan, shuning uchun uning birinchi so'rovi muvaffaqiyatli
    # bo'lishi kerak, garchi 1-foydalanuvchi "IP" (testserver) allaqachon
    # bloklangan bo'lsa ham.
    client.post("/auth/users", json={
        "full_name": "Omborchi", "phone": "+998900222001",
        "password": "parol123", "role": "storekeeper",
    })
    storekeeper_headers = _login(client, "+998900222001", "parol123")

    resp = client.post(
        "/inventory/products",
        json={"name": "Boshqa xodim mahsuloti"},
        headers=storekeeper_headers,
    )
    assert resp.status_code == 200
