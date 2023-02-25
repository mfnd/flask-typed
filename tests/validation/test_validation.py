def test_query_parameter(client):
    response = client.get("/users?user_id=123")
    response_body = response.json
    assert response.status_code == 200
    assert response_body["id"] == 123
    assert response_body["name"] == "default"


def test_query_parameter_int_validation_fail(client):
    response = client.get("/users?user_id=test")
    response_body = response.json

    assert response.status_code == 422

    errors = response_body["errors"]
    assert len(errors) == 1
    assert errors[0]["parameter"] == "user_id"
    assert errors[0]["location"] == "query"
