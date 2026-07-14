"""
tests/test_validation.py
--------------------------
Pydantic sxemalariga qo'shilgan qattiq chegaralarni tekshiradi.
Bu testlar "noto'g'ri ma'lumot backend darajasida rad etiladi" degan
kafolatni saqlab turadi — frontend/bot qanday yozilishidan qat'iy nazar.
"""


def test_product_with_blank_name_is_rejected(client):
    resp = client.post("/inventory/products", json={"name": "   ", "unit": "dona"})
    assert resp.status_code == 422


def test_product_with_negative_price_is_rejected(client):
    resp = client.post("/inventory/products", json={
        "name": "Test mahsulot", "purchase_price": -100, "sale_price": 500,
    })
    assert resp.status_code == 422


def test_product_with_negative_initial_quantity_is_rejected(client):
    resp = client.post("/inventory/products", json={
        "name": "Test mahsulot", "quantity": -5,
    })
    assert resp.status_code == 422


def test_stock_in_with_zero_quantity_is_rejected(client):
    product = client.post("/inventory/products", json={"name": "Test"}).json()
    resp = client.post("/inventory/stock-in", json={
        "product_id": product["id"], "quantity": 0,
    })
    assert resp.status_code == 422


def test_stock_in_with_negative_quantity_is_rejected(client):
    product = client.post("/inventory/products", json={"name": "Test"}).json()
    resp = client.post("/inventory/stock-in", json={
        "product_id": product["id"], "quantity": -10,
    })
    assert resp.status_code == 422


def test_sale_with_zero_quantity_item_is_rejected(client):
    product = client.post("/inventory/products", json={
        "name": "Test", "sale_price": 1000, "quantity": 10,
    }).json()
    resp = client.post("/sales/", json={
        "items": [{"product_id": product["id"], "quantity": 0}]
    })
    assert resp.status_code == 422


def test_sale_with_empty_items_list_is_rejected_by_schema(client):
    """Pydantic darajasida ham (routerga yetib bormasdan) rad etilishi kerak."""
    resp = client.post("/sales/", json={"items": []})
    assert resp.status_code == 422
