"""
tests/test_expenses.py
--------------------------
Xarajatlarni qo'lda kiritish (FMS'ning yetishmayotgan qismi) to'g'ri
ishlayotganini tekshiradi.
"""


def _login(client, phone, password):
    resp = client.post("/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_owner_can_create_expense(client):
    resp = client.post("/finance/expenses", json={
        "amount": 500000, "source": "Ijaraga - iyul oyi",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "expense"
    assert data["amount"] == 500000
    assert data["source"] == "Ijaraga - iyul oyi"


def test_expense_reduces_net_profit(client):
    product = client.post("/inventory/products", json={
        "name": "Choy", "sale_price": 10000, "quantity": 10,
    }).json()
    client.post("/sales/", json={"items": [{"product_id": product["id"], "quantity": 5}]})  # +50000

    client.post("/finance/expenses", json={"amount": 20000, "source": "Kommunal"})

    summary = client.get("/finance/summary").json()
    assert summary["total_income"] == 50000
    assert summary["total_expense"] == 20000
    assert summary["net_profit"] == 30000


def test_expense_appears_in_transactions_list(client):
    client.post("/finance/expenses", json={"amount": 15000, "source": "Ofis buyumlari"})
    resp = client.get("/finance/transactions")
    sources = [t["source"] for t in resp.json()["items"]]
    assert "Ofis buyumlari" in sources


def test_expense_writes_audit_entry(client):
    client.post("/finance/expenses", json={"amount": 30000, "source": "Ish haqi"})
    resp = client.get("/audit-log?search=expense")
    actions = [e["action"] for e in resp.json()["items"]]
    assert "expense.create" in actions


def test_cashier_cannot_create_expense(client):
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998900333001",
        "password": "parol123", "role": "cashier",
    })
    cashier_headers = _login(client, "+998900333001", "parol123")

    resp = client.post(
        "/finance/expenses",
        json={"amount": 10000, "source": "Sinov"},
        headers=cashier_headers,
    )
    assert resp.status_code == 403


def test_negative_expense_amount_is_rejected(client):
    resp = client.post("/finance/expenses", json={"amount": -5000, "source": "Xato"})
    assert resp.status_code == 422


def test_expense_with_blank_source_is_rejected(client):
    resp = client.post("/finance/expenses", json={"amount": 5000, "source": ""})
    assert resp.status_code == 422
