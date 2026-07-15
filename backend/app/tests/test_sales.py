"""
tests/test_sales.py
--------------------
Savdo moduli — WMS va FMS integratsiyasining eng muhim sinovi.
"""

from .conftest import other_company_headers


def _make_product(client, quantity=100):
    return client.post("/inventory/products", json={
        "name": "Choy", "unit": "dona", "purchase_price": 8000,
        "sale_price": 12000, "quantity": quantity,
    }).json()


def test_sale_reduces_stock_and_creates_income(client):
    """Sotuv: ombor qoldig'i kamayishi VA moliyaga kirim yozilishi kerak — bitta amalda."""
    product = _make_product(client, quantity=100)

    resp = client.post("/sales/", json={
        "items": [{"product_id": product["id"], "quantity": 5}]
    })
    assert resp.status_code == 200
    sale = resp.json()
    assert sale["total_amount"] == 5 * 12000

    # Ombor kamaydimi?
    products = client.get("/inventory/products").json()["items"]
    assert products[0]["quantity"] == 95

    # Moliyaga kirim yozildimi?
    summary = client.get("/finance/summary").json()
    assert summary["total_income"] == 5 * 12000


def test_sale_fails_if_not_enough_stock(client):
    """Omborda yetarli mahsulot bo'lmasa, sotuv rad etilishi va HECH NARSA
    o'zgarmasligi kerak (yarim bajarilgan tranzaksiya qolmasligi)."""
    product = _make_product(client, quantity=3)

    resp = client.post("/sales/", json={
        "items": [{"product_id": product["id"], "quantity": 10}]
    })
    assert resp.status_code == 400

    # Muvaffaqiyatsiz urinishdan keyin ombor o'zgarmagan bo'lishi kerak
    products = client.get("/inventory/products").json()["items"]
    assert products[0]["quantity"] == 3

    # Va moliyaga ham noto'g'ri kirim yozilmagan bo'lishi kerak
    summary = client.get("/finance/summary").json()
    assert summary["total_income"] == 0


def test_sale_blocks_cross_tenant_product(client):
    """1-kompaniyaning mahsulotini 2-kompaniya "sotib" ololmasligi kerak."""
    product = _make_product(client, quantity=50)

    resp = client.post(
        "/sales/",
        json={"items": [{"product_id": product["id"], "quantity": 1}]},
        headers=other_company_headers(client),
    )
    assert resp.status_code == 404

    # 1-kompaniyaning ombori o'zgarmagan bo'lishi kerak
    products = client.get("/inventory/products").json()["items"]
    assert products[0]["quantity"] == 50
