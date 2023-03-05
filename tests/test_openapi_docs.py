import pytest
from flask import Flask

from flask_typed import TypedAPI
from tests.test_data.simple_user import UserResource
from tests.test_data.todo_resource import TodoListResource


@pytest.fixture()
def test_app():
    app = Flask("test_app")
    api = TypedAPI(app)
    api.add_resource(UserResource, "/users")
    api.add_resource(TodoListResource, "/todo")

    yield app


def test_simple_user_get_docs(docs):
    get_op = docs["paths"]["/users"]["get"]

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
