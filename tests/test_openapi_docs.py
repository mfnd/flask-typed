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


def test_status_code_with_pydantic_config(docs):
    get_op = docs["paths"]["/todo"]["get"]

    success_resp = get_op["responses"]["200"]
    assert success_resp["content"]["application/json"]["schema"]["$ref"] == "#/components/schemas/BlogPostListResponse"


def test_error_docs_with_docs_annotation(docs):
    get_op = docs["paths"]["/todo"]["get"]

    not_found_resp = get_op["responses"]["404"]
