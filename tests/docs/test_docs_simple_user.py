import pytest


@pytest.fixture
def path_item_docs(client):
    docs = client.get("/openapi").json
    return docs["paths"]["/users"]


def test_simple_user_get_docs(path_item_docs):
    get_op = path_item_docs["get"]

    assert get_op["summary"] == "Retrieves user"
    assert get_op["description"] == "User can be queried with query parameters"

    parameters = {param["name"]: param for param in get_op["parameters"]}

    assert parameters["user_id"]["description"] == "User ID"
    assert parameters["user_id"]["schema"]["type"] == "integer"
    assert parameters["user_id"]["in"] == "query"

    assert parameters["name"]["description"] == "First name"
    assert parameters["name"]["schema"]["type"] == "string"
    assert parameters["name"]["in"] == "query"

    success_resp = get_op["responses"]["200"]
    assert success_resp["description"] == "User details"
    assert success_resp["content"]["application/json"]["schema"]["$ref"] == "#/components/schemas/User"

