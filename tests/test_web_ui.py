import json
from fie.web_ui import app


def test_transactions_endpoint():
    client = app.test_client()
    rv = client.get('/api/transactions')
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, list)


def test_summary_endpoint():
    client = app.test_client()
    rv = client.get('/api/summary')
    assert rv.status_code == 200
    j = rv.get_json()
    assert 'total_transactions' in j
