"""
tests/test_payroll.py
------------------------
HRMS<->FMS chuqur integratsiyasi: ish haqini smenalar asosida
avtomatik hisoblash va to'lash.
"""


def _login(client, phone, password):
    resp = client.post("/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _add_employee_with_rate(client, phone, rate):
    resp = client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": phone, "password": "parol123",
        "role": "cashier", "hourly_rate": rate,
    })
    assert resp.status_code == 200
    return resp.json()


def test_payroll_calculates_correct_amount(client):
    employee = _add_employee_with_rate(client, "+998900555001", rate=20000)
    cashier_headers = _login(client, "+998900555001", "parol123")

    client.post("/hrms/shifts/clock-in", headers=cashier_headers)
    client.post("/hrms/shifts/clock-out", headers=cashier_headers)

    resp = client.post(f"/hrms/payroll/pay/{employee['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["shifts_paid"] == 1
    assert data["hourly_rate"] == 20000
    assert data["total_amount"] == round(data["total_hours"] * 20000, 2)


def test_payroll_creates_finance_expense(client):
    employee = _add_employee_with_rate(client, "+998900555002", rate=15000)
    cashier_headers = _login(client, "+998900555002", "parol123")

    client.post("/hrms/shifts/clock-in", headers=cashier_headers)
    client.post("/hrms/shifts/clock-out", headers=cashier_headers)

    payroll = client.post(f"/hrms/payroll/pay/{employee['id']}").json()

    summary = client.get("/finance/summary").json()
    assert summary["total_expense"] == payroll["total_amount"]


def test_paid_shifts_are_not_paid_twice(client):
    employee = _add_employee_with_rate(client, "+998900555003", rate=10000)
    cashier_headers = _login(client, "+998900555003", "parol123")

    client.post("/hrms/shifts/clock-in", headers=cashier_headers)
    client.post("/hrms/shifts/clock-out", headers=cashier_headers)

    client.post(f"/hrms/payroll/pay/{employee['id']}")

    # Endi to'lanmagan smena qolmagani uchun rad etilishi kerak
    resp = client.post(f"/hrms/payroll/pay/{employee['id']}")
    assert resp.status_code == 409


def test_payroll_writes_audit_entry(client):
    employee = _add_employee_with_rate(client, "+998900555004", rate=10000)
    cashier_headers = _login(client, "+998900555004", "parol123")
    client.post("/hrms/shifts/clock-in", headers=cashier_headers)
    client.post("/hrms/shifts/clock-out", headers=cashier_headers)

    client.post(f"/hrms/payroll/pay/{employee['id']}")

    resp = client.get("/audit-log?search=payroll")
    actions = [e["action"] for e in resp.json()["items"]]
    assert "payroll.pay" in actions


def test_cashier_cannot_trigger_payroll(client):
    employee = _add_employee_with_rate(client, "+998900555005", rate=10000)
    cashier_headers = _login(client, "+998900555005", "parol123")
    client.post("/hrms/shifts/clock-in", headers=cashier_headers)
    client.post("/hrms/shifts/clock-out", headers=cashier_headers)

    resp = client.post(f"/hrms/payroll/pay/{employee['id']}", headers=cashier_headers)
    assert resp.status_code == 403


def test_payroll_fails_gracefully_with_no_unpaid_shifts(client):
    employee = _add_employee_with_rate(client, "+998900555006", rate=10000)
    resp = client.post(f"/hrms/payroll/pay/{employee['id']}")
    assert resp.status_code == 409
