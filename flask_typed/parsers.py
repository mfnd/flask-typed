from abc import ABC
from typing import TypeVar

import openapi_schema_pydantic as openapi
from flask import Request
from werkzeug.datastructures import MultiDict, Headers

T = TypeVar("T")


class RequestParser(ABC):

    @classmethod
    def parse_request(cls, request: Request) -> 'Self':
        raise NotImplementedError


class QueryParser(RequestParser, ABC):

    @classmethod
    def parse(cls, args: MultiDict[str, str]) -> 'Self':
        raise NotImplementedError

    @classmethod
    def schema(cls) -> list[openapi.Parameter]:
        raise NotImplementedError

    @classmethod
    def parse_request(cls, request: Request) -> 'Self':
        return cls.parse(request.args)


class HeaderParser(RequestParser, ABC):

    @classmethod
    def parse(cls, header: Headers) -> 'Self':
        raise NotImplementedError

    @classmethod
    def schema(cls) -> list[openapi.Parameter]:
        raise NotImplementedError

    @classmethod
    def parse_request(cls, request: Request) -> 'Self':
        return cls.parse(request.headers)


class BodyParser(RequestParser, ABC):

    @classmethod
    def parse(cls, data: bytes) -> 'Self':
        raise NotImplementedError

    @classmethod
    def schema(cls) -> openapi.RequestBody:
        raise NotImplementedError

    @classmethod
    def parse_request(cls, request: Request) -> 'Self':
        return cls.parse(request.data)
