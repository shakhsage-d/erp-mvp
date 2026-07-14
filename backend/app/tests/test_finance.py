"""
tests/test_finance.py
-----------------------
FMS moduli — kirim/chiqim va xulosa hisobotlari.
"""


def test_summary_is_zero_when_no_transactions(client):
    resp = client.get("/finance/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_income"] == 0
    assert data["total_expense"] == 0
    assert data["net_profit"] == 0


def test_transactions_isolated_per_company(client):
    """1-kompaniyaning savdosidan tushgan pul, 2-kompaniyaning hisobotida
    KO'RINMASLIGI kerak."""
    product = client.post("/inventory/products", json={
        "name": "Sut", "unit": "dona", "purchase_price": 6000,
        "sale_price": 9000, "quantity": 20,
    }).json()
    client.post("/sales/", json={"items": [{"product_id": product["id"], "quantity": 2}]})

    own_summary = client.get("/finance/summary").json()
    assert own_summary["total_income"] == 2 * 9000

    other_summary = client.get("/finance/summary", headers={"X-Company-Id": "2"}).json()
    assert other_summary["total_income"] == 0
