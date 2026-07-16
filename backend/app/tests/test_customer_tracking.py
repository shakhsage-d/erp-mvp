"""
tests/test_customer_tracking.py
-----------------------------------
Yengil mijoz kuzatuvi (ixtiyoriy) va "eng faol mijozlar" hisobotini
tekshiradi.
"""


def test_sale_with_customer_info_is_saved(client):
    product = client.post("/inventory/products", json={
        "name": "Non", "sale_price": 3000, "quantity": 20,
    }).json()

    resp = client.post("/sales/", json={
        "items": [{"product_id": product["id"], "quantity": 2}],
        "customer_name": "Aziz Karimov",
        "customer_phone": "+998900123456",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["customer_name"] == "Aziz Karimov"
    assert data["customer_phone"] == "+998900123456"


def test_sale_without_customer_info_still_works(client):
    product = client.post("/inventory/products", json={
        "name": "Sut", "sale_price": 5000, "quantity": 10,
    }).json()

    resp = client.post("/sales/", json={
        "items": [{"product_id": product["id"], "quantity": 1}],
    })
    assert resp.status_code == 200
    assert resp.json()["customer_name"] is None


def test_top_customers_ranks_by_total_spent(client):
    product = client.post("/inventory/products", json={
        "name": "Choy", "sale_price": 10000, "quantity": 100,
    }).json()

    # Kichik xaridor
    client.post("/sales/", json={
        "items": [{"product_id": product["id"], "quantity": 1}],
        "customer_name": "Kichik Xaridor", "customer_phone": "+998900000001",
    })
    # Katta xaridor (ikki marta xarid qilgan)
    client.post("/sales/", json={
        "items": [{"product_id": product["id"], "quantity": 5}],
        "customer_name": "Katta Xaridor", "customer_phone": "+998900000002",
    })
    client.post("/sales/", json={
        "items": [{"product_id": product["id"], "quantity": 5}],
        "customer_name": "Katta Xaridor", "customer_phone": "+998900000002",
    })

    resp = client.get("/sales/analytics/top-customers")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["customer_phone"] == "+998900000002"
    assert data[0]["purchase_count"] == 2
    assert data[0]["total_spent"] == 100000


def test_sales_without_customer_phone_excluded_from_top_customers(client):
    product = client.post("/inventory/products", json={
        "name": "Test", "sale_price": 5000, "quantity": 10,
    }).json()
    client.post("/sales/", json={"items": [{"product_id": product["id"], "quantity": 1}]})

    resp = client.get("/sales/analytics/top-customers")
    assert resp.json() == []
