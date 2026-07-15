"""
tests/test_pagination.py
---------------------------
Sahifalash va qidiruv to'g'ri ishlayotganini tekshiradi.
"""


def test_products_pagination(client):
    for i in range(25):
        client.post("/inventory/products", json={"name": f"Mahsulot {i}", "sale_price": 1000})

    resp = client.get("/inventory/products?page=1&page_size=10")
    body = resp.json()
    assert body["total"] == 25
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["total_pages"] == 3
    assert len(body["items"]) == 10

    resp = client.get("/inventory/products?page=3&page_size=10")
    body = resp.json()
    assert len(body["items"]) == 5  # oxirgi sahifada 5 ta qolgan


def test_products_search_by_name(client):
    client.post("/inventory/products", json={"name": "Qora choy", "sale_price": 1000})
    client.post("/inventory/products", json={"name": "Yashil choy", "sale_price": 1000})
    client.post("/inventory/products", json={"name": "Guruch", "sale_price": 1000})

    resp = client.get("/inventory/products?search=choy")
    body = resp.json()
    assert body["total"] == 2
    names = {item["name"] for item in body["items"]}
    assert names == {"Qora choy", "Yashil choy"}


def test_products_page_size_cannot_exceed_max(client):
    resp = client.get("/inventory/products?page_size=500")
    assert resp.status_code == 422


def test_transactions_pagination_and_search(client):
    product = client.post("/inventory/products", json={
        "name": "Konfet", "sale_price": 5000, "quantity": 100,
    }).json()
    for _ in range(3):
        client.post("/sales/", json={"items": [{"product_id": product["id"], "quantity": 1}]})

    resp = client.get("/finance/transactions?page=1&page_size=2")
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2

    resp = client.get("/finance/transactions?search=Sale")
    assert resp.json()["total"] == 3
