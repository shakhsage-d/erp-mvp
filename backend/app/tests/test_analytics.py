"""
tests/test_analytics.py
--------------------------
Hisobotlar (kunlik savdo, top mahsulotlar, mehmonxona to'lilik foizi)
to'g'ri hisoblanayotganini tekshiradi.
"""


def _login(client, phone, password):
    resp = client.post("/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_daily_sales_analytics_reflects_sale(client):
    product = client.post("/inventory/products", json={
        "name": "Non", "sale_price": 3000, "quantity": 50,
    }).json()
    client.post("/sales/", json={"items": [{"product_id": product["id"], "quantity": 4}]})

    resp = client.get("/finance/analytics/daily-sales?days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert sum(d["total_income"] for d in data) == 12000


def test_cashier_cannot_view_daily_sales_analytics(client):
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998900111001",
        "password": "parol123", "role": "cashier",
    })
    cashier_headers = _login(client, "+998900111001", "parol123")

    resp = client.get("/finance/analytics/daily-sales", headers=cashier_headers)
    assert resp.status_code == 403


def test_top_products_analytics_orders_by_revenue(client):
    cheap = client.post("/inventory/products", json={
        "name": "Arzon", "sale_price": 1000, "quantity": 100,
    }).json()
    expensive = client.post("/inventory/products", json={
        "name": "Qimmat", "sale_price": 50000, "quantity": 100,
    }).json()

    client.post("/sales/", json={"items": [{"product_id": cheap["id"], "quantity": 1}]})
    client.post("/sales/", json={"items": [{"product_id": expensive["id"], "quantity": 1}]})

    resp = client.get("/sales/analytics/top-products?days=30&limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["product_name"] == "Qimmat"  # ko'proq daromad keltirgan birinchi bo'lishi kerak


def test_occupancy_analytics_computes_rate(client):
    client.post("/pms/rooms", json={"room_number": "1", "price_per_night": 100000})
    room2 = client.post("/pms/rooms", json={"room_number": "2", "price_per_night": 100000}).json()

    client.post("/pms/bookings", json={
        "room_id": room2["id"], "guest_name": "Mehmon", "nights": 1,
    })

    resp = client.get("/pms/analytics/occupancy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rooms"] == 2
    assert data["occupied_rooms"] == 1
    assert data["occupancy_rate"] == 50.0


def test_analytics_isolated_per_company(client):
    from .conftest import other_company_headers

    product = client.post("/inventory/products", json={
        "name": "Test", "sale_price": 5000, "quantity": 10,
    }).json()
    client.post("/sales/", json={"items": [{"product_id": product["id"], "quantity": 1}]})

    other_headers = other_company_headers(client)
    resp = client.get("/finance/analytics/daily-sales", headers=other_headers)
    assert resp.json() == []
