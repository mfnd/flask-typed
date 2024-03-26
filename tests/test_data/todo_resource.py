from datetime import datetime

import openapi_pydantic as openapi
from pydantic import BaseModel
from werkzeug.datastructures import MultiDict

from flask_typed import TypedResource, docs, NotFoundError, BadRequestError
from flask_typed.annotations import Header
from flask_typed.parsers import QueryParser


class BlogPost(BaseModel):

    id: int
    content: str
    due_time: datetime
    language: str


class BlogPostListResponse(BaseModel):

    count: int
    items: list[BlogPost]

    model_config = {"status_code": 200}


class BlogPostCreateRequest(BaseModel):
    content: str
    due_time: datetime


class BlogPostListQuery(QueryParser):

    def __init__(self, date_begin: datetime, date_end: datetime):
        self.date_begin = date_begin
        self.date_end = date_end

    @classmethod
    def parse(cls, args: MultiDict[str, str]):
        date_begin = datetime(2000, 1, 1)
        date_end = datetime.now()
        if date_after := args.get("after"):
            date_begin = datetime.strptime(date_after, "%Y-%m-%d")
        if date_before := args.get("before"):
            date_end = datetime.strptime(date_before, "%Y-%m-%d")

        return BlogPostListQuery(date_begin, date_end)

    @classmethod
    def schema(cls) -> list[openapi.Parameter]:
        return [
            openapi.Parameter(
                name=name,
                param_in="query",
                param_schema=openapi.Schema(type="string", format="date"),
                required=False
            ) for name in ["after", "before"]
        ]


class TodoListResource(TypedResource):

    @docs(errors=[NotFoundError])
    def get(self, query: BlogPostListQuery, accept_language: Header[str]) -> BlogPostListResponse:
        """
        Todo List Resource

        :return TodoListResponse: Todo List
        :return TodoItem: Todo Item
        :raises NotFoundError: No todo item has been found
        """
        return BlogPostListResponse(
            count=2,
            items=[
                BlogPost(
                    id=1,
                    content="Write tests",
                    due_time=datetime(1990, 10, 10),
                    language=accept_language
                ),
                BlogPost(
                    id=2,
                    content="Write more tests",
                    due_time=datetime(1990, 10, 11),
                    language=accept_language
                )
            ],
        )

    @docs(errors=[BadRequestError])
    def post(self, new_item: BlogPost) -> int:
        """
        Create new Todo item

        :return int: Created item id
        :raises BadRequestError: Failed to create new item
        """
        if new_item.id < 0:
            raise BadRequestError

        return new_item.id
