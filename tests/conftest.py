import pytest
from flask import Flask

from flask_typed import TypedAPI
from tests.test_data.simple_user import UserResource


@pytest.fixture()
def test_app():
    app = Flask("test_app")
    api = TypedAPI(app)
    api.add_resource(UserResource, "/users")

    yield app


@pytest.fixture()
def client(test_app):
    return test_app.test_client()
