from typing import Generator

import openapi_schema_pydantic as openapi
from flask import current_app, stream_with_context


class BaseResponse:

    mime_type: str
    status_code: int

    def flask_response(self):
        raise NotImplementedError

    @classmethod
    def schema(cls) -> openapi.Schema:
        return openapi.Schema(type="string")


class Response(BaseResponse):

    def __init__(self, body: str):
        self._body = body

    def flask_response(self):
        return current_app.response_class(
            response=self._body,
            mimetype=self.mime_type,
            status=self.status_code
        )


class StreamingResponse(BaseResponse):
    status_code = 200
    mime_type = "text/plain"

    def __init__(self, generator: Generator, use_context=True):
        self._generator = generator
        self._use_context = use_context

    def flask_response(self):
        return current_app.response_class(
            response=stream_with_context(self._generator) if self._use_context else self._generator,
            mimetype=self.mime_type,
            status=self.status_code
        )
