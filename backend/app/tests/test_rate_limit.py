"""
tests/test_rate_limit.py
---------------------------
Rate limiting haqiqatan ham ishlayotganini tekshiradi.
`create_product` endpointi 30/minute chegaraga ega — 31-so'rov
429 qaytarishi kerak.
"""


def test_exceeding_rate_limit_returns_429(client):
    last_status = None
    for _ in range(31):
        resp = client.post("/inventory/products", json={"name": "Sinov mahsuloti"})
        last_status = resp.status_code

    assert last_status == 429
    body = resp.json()
    assert body["error"]["code"] == "rate_limit_exceeded"
