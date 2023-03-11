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


@pytest.fixture()
def client(test_app):
    return test_app.test_client()


@pytest.fixture
def docs(client):
    return client.get("/openapi").json
