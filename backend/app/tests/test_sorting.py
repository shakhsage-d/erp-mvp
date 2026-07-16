"""
tests/test_sorting.py
------------------------
Ustunlar bo'yicha saralashni tekshiradi.
"""


def test_products_sort_by_sale_price_ascending(client):
    client.post("/inventory/products", json={"name": "Qimmat", "sale_price": 50000})
    client.post("/inventory/products", json={"name": "Arzon", "sale_price": 1000})
    client.post("/inventory/products", json={"name": "O'rtacha", "sale_price": 10000})

    resp = client.get("/inventory/products?sort_by=sale_price&sort_order=asc")
    names = [p["name"] for p in resp.json()["items"]]
    assert names == ["Arzon", "O'rtacha", "Qimmat"]


def test_products_sort_by_sale_price_descending(client):
    client.post("/inventory/products", json={"name": "Qimmat", "sale_price": 50000})
    client.post("/inventory/products", json={"name": "Arzon", "sale_price": 1000})

    resp = client.get("/inventory/products?sort_by=sale_price&sort_order=desc")
    names = [p["name"] for p in resp.json()["items"]]
    assert names[0] == "Qimmat"


def test_products_sort_by_name_alphabetically(client):
    client.post("/inventory/products", json={"name": "Zebra"})
    client.post("/inventory/products", json={"name": "Apple"})

    resp = client.get("/inventory/products?sort_by=name&sort_order=asc")
    names = [p["name"] for p in resp.json()["items"]]
    assert names == ["Apple", "Zebra"]


def test_invalid_sort_column_falls_back_to_default(client):
    """Ruxsat etilmagan ustun nomi so'ralsa, xato bermasdan standart
    saralashga qaytishi kerak (xavfsizlik: ixtiyoriy SQL ustun kiritilmasin)."""
    client.post("/inventory/products", json={"name": "Test1"})
    client.post("/inventory/products", json={"name": "Test2"})

    resp = client.get("/inventory/products?sort_by=hashed_password&sort_order=asc")
    assert resp.status_code == 200  # xato bermaydi, shunchaki e'tiborsiz qoldiradi


def test_transactions_sort_by_amount(client):
    client.post("/finance/expenses", json={"amount": 5000, "source": "Kichik"})
    client.post("/finance/expenses", json={"amount": 500000, "source": "Katta"})

    resp = client.get("/finance/transactions?sort_by=amount&sort_order=asc")
    sources = [t["source"] for t in resp.json()["items"]]
    assert sources[0] == "Kichik"
