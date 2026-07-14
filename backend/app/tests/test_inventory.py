"""
tests/test_inventory.py
------------------------
WMS moduli uchun asosiy stsenariylar.
"""

from .conftest import other_company_headers


def test_create_and_list_product(client):
    """Mahsulot qo'shilsa, ro'yxatda ko'rinishi kerak."""
    resp = client.post("/inventory/products", json={
        "name": "Guruch",
        "unit": "kg",
        "purchase_price": 10000,
        "sale_price": 13000,
        "quantity": 0,
    })
    assert resp.status_code == 200
    product = resp.json()
    assert product["name"] == "Guruch"
    assert product["company_id"] == 1

    resp = client.get("/inventory/products")
    assert resp.status_code == 200
    products = resp.json()
    assert len(products) == 1
    assert products[0]["name"] == "Guruch"


def test_stock_in_increases_quantity(client):
    """Omborga kirim qilinsa, qoldiq ortishi kerak."""
    product = client.post("/inventory/products", json={
        "name": "Yog'", "unit": "l", "purchase_price": 15000,
        "sale_price": 20000, "quantity": 0,
    }).json()

    resp = client.post("/inventory/stock-in", json={
        "product_id": product["id"], "quantity": 50, "reason": "Yetkazib berildi",
    })
    assert resp.status_code == 200
    assert resp.json()["new_quantity"] == 50


def test_stock_in_unknown_product_returns_404(client):
    """Mavjud bo'lmagan mahsulotga kirim qilishga urinish 404 qaytarishi kerak."""
    resp = client.post("/inventory/stock-in", json={
        "product_id": 999, "quantity": 10,
    })
    assert resp.status_code == 404


def test_stock_in_blocks_cross_tenant_access(client):
    """
    MUHIM XAVFSIZLIK TESTI — aynan avval topilgan xatoning o'zi.
    1-kompaniya yaratgan mahsulotga, 2-kompaniya (begona) kirim qila
    OLMASLIGI kerak.
    """
    product = client.post("/inventory/products", json={
        "name": "Un", "unit": "kg", "purchase_price": 5000,
        "sale_price": 7000, "quantity": 0,
    }).json()

    # 2-kompaniya nomidan, 1-kompaniyaning mahsulotiga kirim qilishga urinish
    other_headers = other_company_headers(client)
    resp = client.post(
        "/inventory/stock-in",
        json={"product_id": product["id"], "quantity": 100},
        headers=other_headers,
    )
    assert resp.status_code == 404  # "topilmadi" — chunki bu kompaniyaga tegishli emas

    # 2-kompaniya bu mahsulotni ro'yxatda ham ko'rmasligi kerak
    resp = client.get("/inventory/products", headers=other_headers)
    assert resp.json() == []
