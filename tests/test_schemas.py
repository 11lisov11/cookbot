def test_schema_endpoint_exposes_core_contracts(client):
    response = client.get("/schemas")
    assert response.status_code == 200
    body = response.json()
    assert "SystemState" in body
    assert "MegaRequest" in body
    assert "AIPlan" in body
    assert "HardwareReadinessResponse" in body
