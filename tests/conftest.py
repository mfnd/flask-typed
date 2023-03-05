import pytest
from flask import Flask


@pytest.fixture()
def test_app():
    app = Flask("test_app")
    yield app


@pytest.fixture()
def client(test_app):
    return test_app.test_client()


@pytest.fixture
def docs(client):
    return client.get("/openapi").json
