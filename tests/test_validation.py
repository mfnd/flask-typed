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


def test_query_parameter_date(client):
    response = client.get("/users?join_date=2000-01-02")
    response_body = response.json
    assert response.status_code == 200
    assert response_body["id"] == 0
    assert response_body["name"] == "default"
    assert response_body["join_date"] == "2000-01-02"


def test_header_parameter_str(client):
    response = client.get("/todo", headers={"Accept-Language": "en-US"})
    response_body = response.json

    assert response.status_code == 200
    assert response_body["items"][0]["language"] == "en-US"


def test_header_parameter_validation_fail_missing(client):
    response = client.get("/todo")
    response_body = response.json

    assert response.status_code == 422

    print(response_body)

    errors = response_body["errors"]
    assert len(errors) == 1
    assert errors[0]["parameter"] == "Accept-Language"
    assert errors[0]["location"] == "header"


def test_path_parameter_date(client):
    response = client.post("/jobs/13/2000-01-02")
    response_body = response.json

    print(response_body)

    assert response.status_code == 200
    assert response_body["id"] == 13
    assert response_body["date"] == "2000-01-02"
    assert response_body["success"] is True
