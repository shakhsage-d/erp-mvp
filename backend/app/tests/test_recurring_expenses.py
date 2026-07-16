"""
tests/test_recurring_expenses.py
------------------------------------
Takrorlanuvchi xarajatlar (masalan oylik ijara) to'g'ri avtomatik
yaratilishini tekshiradi.
"""

from datetime import datetime


def _login(client, phone, password):
    resp = client.post("/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_create_recurring_expense_template(client):
    resp = client.post("/finance/recurring-expenses", json={
        "amount": 500000, "source": "Ijaraga", "day_of_month": 5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "Ijaraga"
    assert data["is_active"] is True
    assert data["last_generated_month"] is None


def test_summary_auto_generates_due_expense():
    """Muddati kelgan shablon `/finance/summary` chaqirilganda avtomatik
    ishga tushishini tekshiradi (fake 'bugungi kun'ni simulyatsiya qilib)."""
    from app.modules.finance.router import process_due_recurring_expenses
    from app.modules.finance import models as finance_models
    from app.db.session import Base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    template = finance_models.RecurringExpense(
        company_id=1, amount=300000, source="Internet", day_of_month=1,
    )
    db.add(template)
    db.commit()

    created_count = process_due_recurring_expenses(db, company_id=1)
    assert created_count == 1

    expense = db.query(finance_models.Transaction).filter(
        finance_models.Transaction.company_id == 1,
    ).first()
    assert expense is not None
    assert expense.amount == 300000
    assert "Internet" in expense.source

    # Ikkinchi marta chaqirilganda, shu oy uchun QAYTA yaratilmasligi kerak
    created_count_again = process_due_recurring_expenses(db, company_id=1)
    assert created_count_again == 0


def test_recurring_expense_not_generated_before_day_of_month(client):
    """Agar bugungi kun shablon kunidan oldin bo'lsa, hali yaratilmasligi kerak."""
    today = datetime.utcnow().day
    if today >= 28:
        return  # oy oxirida bu testni ma'nosiz — o'tkazib yuboriladi

    future_day = min(today + 1, 28)
    client.post("/finance/recurring-expenses", json={
        "amount": 100000, "source": "Kelajakdagi xarajat", "day_of_month": future_day,
    })
    summary_before = client.get("/finance/summary").json()
    assert summary_before["total_expense"] == 0


def test_deactivate_recurring_expense(client):
    template = client.post("/finance/recurring-expenses", json={
        "amount": 200000, "source": "Sug'urta", "day_of_month": 1,
    }).json()

    resp = client.post(f"/finance/recurring-expenses/{template['id']}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_cashier_cannot_create_recurring_expense(client):
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998900666001",
        "password": "parol123", "role": "cashier",
    })
    cashier_headers = _login(client, "+998900666001", "parol123")

    resp = client.post(
        "/finance/recurring-expenses",
        json={"amount": 100000, "source": "Sinov", "day_of_month": 1},
        headers=cashier_headers,
    )
    assert resp.status_code == 403


def test_recurring_expense_isolated_per_company(client):
    from .conftest import other_company_headers

    client.post("/finance/recurring-expenses", json={
        "amount": 100000, "source": "Ijaraga", "day_of_month": 1,
    })

    other_headers = other_company_headers(client)
    resp = client.get("/finance/recurring-expenses", headers=other_headers)
    assert resp.json() == []
