"""
tests/test_hrms.py
--------------------
Xodim smenasi (clock-in/clock-out) va ruxsatlarni tekshiradi.
"""

from .conftest import other_company_headers


def _login(client, phone, password):
    resp = client.post("/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_clock_in_creates_open_shift(client):
    resp = client.post("/hrms/shifts/clock-in")
    assert resp.status_code == 200
    data = resp.json()
    assert data["clock_out"] is None
    assert data["duration_hours"] is None


def test_cannot_clock_in_twice_without_clocking_out(client):
    client.post("/hrms/shifts/clock-in")
    resp = client.post("/hrms/shifts/clock-in")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


def test_clock_out_closes_shift_and_computes_duration(client):
    client.post("/hrms/shifts/clock-in")
    resp = client.post("/hrms/shifts/clock-out")
    assert resp.status_code == 200
    data = resp.json()
    assert data["clock_out"] is not None
    assert data["duration_hours"] is not None
    assert data["duration_hours"] >= 0


def test_clock_out_without_open_shift_returns_404(client):
    resp = client.post("/hrms/shifts/clock-out")
    assert resp.status_code == 404


def test_employee_can_view_own_shifts(client):
    client.post("/hrms/shifts/clock-in")
    client.post("/hrms/shifts/clock-out")

    resp = client.get("/hrms/shifts/me")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_owner_can_view_all_shifts_but_cashier_cannot(client):
    # Owner (client) o'zi ham bir smena qilib qo'yadi
    client.post("/hrms/shifts/clock-in")
    client.post("/hrms/shifts/clock-out")

    # Sotuvchi qo'shiladi va o'z smenasini boshlaydi
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998966666601",
        "password": "parol123", "role": "cashier",
    })
    cashier_headers = _login(client, "+998966666601", "parol123")
    client.post("/hrms/shifts/clock-in", headers=cashier_headers)

    # Egasi barcha smenalarni ko'ra oladi (kamida 2 ta: o'zi + sotuvchi)
    resp = client.get("/hrms/shifts")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2

    # Sotuvchi esa "barchasi"ni ko'ra olmaydi
    resp = client.get("/hrms/shifts", headers=cashier_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_shifts_are_isolated_per_company(client):
    """1-kompaniyaning smenasi 2-kompaniya hisobotida ko'rinmasligi kerak."""
    client.post("/hrms/shifts/clock-in")
    client.post("/hrms/shifts/clock-out")

    other_headers = other_company_headers(client)
    resp = client.get("/hrms/shifts", headers=other_headers)
    assert resp.status_code == 200
    assert resp.json() == []
