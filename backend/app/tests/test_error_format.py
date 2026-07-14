"""
tests/test_error_format.py
----------------------------
Bu testlar barcha modullar uchun XATO JAVOBI FORMATI bir xilligini
"qulflab" qo'yadi. Kelajakda yangi modul (HRMS, PMS) qo'shilganda ham,
xato javobi shu formatda bo'lishi kerak:

    {"error": {"code": "...", "message": "..."}}
"""


def test_not_found_error_has_standard_shape(client):
    resp = client.post("/inventory/stock-in", json={"product_id": 999, "quantity": 1})
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "not_found"
    assert "message" in body["error"]


def test_insufficient_stock_error_has_structured_details(client):
    product = client.post("/inventory/products", json={
        "name": "Shakar", "unit": "kg", "purchase_price": 9000,
        "sale_price": 12000, "quantity": 2,
    }).json()

    resp = client.post("/sales/", json={
        "items": [{"product_id": product["id"], "quantity": 10}]
    })
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "insufficient_stock"
    # Frontend/bot uchun tayyor, tuzilgan ma'lumot — matnni tahlil qilish shart emas
    assert body["error"]["available"] == 2
    assert body["error"]["requested"] == 10


def test_empty_sale_request_has_standard_shape(client):
    resp = client.post("/sales/", json={"items": []})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "empty_request"


def test_pydantic_validation_error_has_standard_shape(client):
    """Majburiy maydon yuborilmasa (masalan 'name' yo'q), FastAPI'ning
    o'zi ko'targan validatsiya xatosi ham bir xil formatda bo'lishi kerak."""
    resp = client.post("/inventory/products", json={"unit": "kg"})  # "name" yo'q
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "validation_error"
    assert "fields" in body["error"]
