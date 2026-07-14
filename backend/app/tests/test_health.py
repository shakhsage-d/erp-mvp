"""
tests/test_health.py
----------------------
`/health` endpointi baza bilan ulanishni HAQIQATAN HAM tekshirayotganini
tasdiqlaydi (shunchaki "status: ok" qaytarib qo'ya qolmasligi kerak).
"""


def test_health_check_reports_database_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["checks"]["database"] == "ok"
