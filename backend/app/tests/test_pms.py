"""
tests/test_pms.py
--------------------
Xonalar, bronlar, va checkout'ning FMS bilan chuqur integratsiyasini
tekshiradi.
"""

from .conftest import other_company_headers


def _login(client, phone, password):
    resp = client.post("/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_room(client, price=500000):
    return client.post("/pms/rooms", json={
        "room_number": "101", "room_type": "standard", "price_per_night": price,
    }).json()


def test_create_room(client):
    resp = client.post("/pms/rooms", json={
        "room_number": "205", "room_type": "lyuks", "price_per_night": 900000,
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "available"


def test_booking_marks_room_occupied(client):
    room = _make_room(client)
    resp = client.post("/pms/bookings", json={
        "room_id": room["id"], "guest_name": "Aziz Karimov",
        "guest_phone": "+998900000010", "nights": 3,
    })
    assert resp.status_code == 200
    booking = resp.json()
    assert booking["total_price"] == 500000 * 3
    assert booking["status"] == "active"

    room_after = client.get("/pms/rooms").json()[0]
    assert room_after["status"] == "occupied"


def test_cannot_book_already_occupied_room(client):
    room = _make_room(client)
    client.post("/pms/bookings", json={
        "room_id": room["id"], "guest_name": "Birinchi mehmon", "nights": 1,
    })
    resp = client.post("/pms/bookings", json={
        "room_id": room["id"], "guest_name": "Ikkinchi mehmon", "nights": 1,
    })
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


def test_checkout_frees_room_and_creates_income(client):
    """MUHIM: checkout — bitta amalda bron yopilishi, xona bo'shashi VA
    moliyaga kirim yozilishini tekshiradi (chuqur integratsiya)."""
    room = _make_room(client, price=400000)
    booking = client.post("/pms/bookings", json={
        "room_id": room["id"], "guest_name": "Mehmon", "nights": 2,
    }).json()

    resp = client.post(f"/pms/bookings/{booking['id']}/checkout")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "checked_out"
    assert data["check_out"] is not None

    # Xona yana bo'sh bo'lishi kerak
    room_after = client.get("/pms/rooms").json()[0]
    assert room_after["status"] == "available"

    # Moliyaga avtomatik kirim yozilgan bo'lishi kerak
    summary = client.get("/finance/summary").json()
    assert summary["total_income"] == 400000 * 2


def test_double_checkout_is_rejected(client):
    room = _make_room(client)
    booking = client.post("/pms/bookings", json={
        "room_id": room["id"], "guest_name": "Mehmon", "nights": 1,
    }).json()
    client.post(f"/pms/bookings/{booking['id']}/checkout")

    resp = client.post(f"/pms/bookings/{booking['id']}/checkout")
    assert resp.status_code == 409


def test_receptionist_can_manage_pms_but_not_finance(client):
    client.post("/auth/users", json={
        "full_name": "Resepshin", "phone": "+998977777701",
        "password": "parol123", "role": "receptionist",
    })
    reception_headers = _login(client, "+998977777701", "parol123")

    resp = client.post(
        "/pms/rooms",
        json={"room_number": "301", "price_per_night": 300000},
        headers=reception_headers,
    )
    assert resp.status_code == 200

    resp = client.get("/finance/summary", headers=reception_headers)
    assert resp.status_code == 403


def test_cashier_cannot_manage_pms(client):
    client.post("/auth/users", json={
        "full_name": "Sotuvchi", "phone": "+998977777702",
        "password": "parol123", "role": "cashier",
    })
    cashier_headers = _login(client, "+998977777702", "parol123")

    resp = client.post(
        "/pms/rooms",
        json={"room_number": "401", "price_per_night": 300000},
        headers=cashier_headers,
    )
    assert resp.status_code == 403


def test_rooms_are_isolated_per_company(client):
    _make_room(client)
    other_headers = other_company_headers(client)
    resp = client.get("/pms/rooms", headers=other_headers)
    assert resp.status_code == 200
    assert resp.json() == []
