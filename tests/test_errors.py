def test_error_response_todo_item(client):
    res = client.post("/todo", json={
        "id": -1,
        "content": "do it",
        "due_time": "2022-02-22T22:20:22Z",
        "language": "en-US"
    })

    print(res.json)

    assert res.status_code == 400
    assert res.json["message"] == "Bad request"
