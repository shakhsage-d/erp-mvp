"""
tests/test_transaction_filters.py
-------------------------------------
Tranzaksiyalar uchun kengaytirilgan filtrlarni (sana oralig'i, tur)
tekshiradi.
"""

from datetime import datetime, timedelta


def test_filter_by_type_income(client):
    client.post("/finance/expenses", json={"amount": 10000, "source": "Xarajat"})
    product = client.post("/inventory/products", json={
        "name": "Test", "sale_price": 5000, "quantity": 10,
    }).json()
    client.post("/sales/", json={"items": [{"product_id": product["id"], "quantity": 1}]})

    resp = client.get("/finance/transactions?type=income")
    data = resp.json()
    assert all(t["type"] == "income" for t in data["items"])
    assert data["total"] == 1


def test_filter_by_type_expense(client):
    client.post("/finance/expenses", json={"amount": 10000, "source": "Xarajat"})
    product = client.post("/inventory/products", json={
        "name": "Test", "sale_price": 5000, "quantity": 10,
    }).json()
    client.post("/sales/", json={"items": [{"product_id": product["id"], "quantity": 1}]})

    resp = client.get("/finance/transactions?type=expense")
    data = resp.json()
    assert all(t["type"] == "expense" for t in data["items"])
    assert data["total"] == 1


def test_filter_by_date_range_excludes_out_of_range(client):
    client.post("/finance/expenses", json={"amount": 10000, "source": "Bugungi xarajat"})

    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    resp = client.get(f"/finance/transactions?date_from={tomorrow}")
    assert resp.json()["total"] == 0

    today = datetime.utcnow().strftime("%Y-%m-%d")
    resp = client.get(f"/finance/transactions?date_from={today}")
    assert resp.json()["total"] == 1


def test_filter_by_date_to_includes_today(client):
    client.post("/finance/expenses", json={"amount": 10000, "source": "Xarajat"})

    today = datetime.utcnow().strftime("%Y-%m-%d")
    resp = client.get(f"/finance/transactions?date_to={today}")
    assert resp.json()["total"] == 1

    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    resp = client.get(f"/finance/transactions?date_to={yesterday}")
    assert resp.json()["total"] == 0
