def test_schema_endpoint_exposes_core_contracts(client):
    response = client.get("/schemas")
    assert response.status_code == 200
    body = response.json()
    assert "SystemState" in body
    assert "MegaRequest" in body
    assert "AIPlan" in body
    assert "HardwareReadinessResponse" in body
    assert "AcceptanceReport" in body
    assert "ExportBundle" in body
    assert "BackupBundle" in body
    assert "RestoreValidationResponse" in body
    assert "ProductReadinessResponse" in body
    assert "VersionResponse" in body
    assert "ErrorTaxonomy" in body
