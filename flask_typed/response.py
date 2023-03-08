from typing import Generator, Any

import openapi_schema_pydantic as openapi
from flask import current_app, stream_with_context
from openapi_schema_pydantic.util import PydanticSchema
from pydantic import BaseModel


_pydantic_export_config_fields = [
    "include",
    "exclude",
    "by_alias",
    "exclude_unset",
    "exclude_defaults",
    "exclude_none"
]


class BaseResponseConfig:
    mime_type: str = "text/plain"
    status_code: int = 200


class BaseResponse:

    class ResponseConfig:
        pass

    def __init_subclass__(cls, **kwargs):
        response_config = cls.ResponseConfig
        cls._mime_type = getattr(response_config, "mime_type", BaseResponseConfig.mime_type)
        cls._status_code = getattr(response_config, "status_code", BaseResponseConfig.status_code)

    def flask_response(self):
        raise NotImplementedError

    @classmethod
    def schema(cls) -> openapi.Schema:
        return openapi.Schema(type="string")


class ModelResponse(BaseModel, BaseResponse):

    def __init_subclass__(cls, **kwargs):
        export_config = {}

        for field in _pydantic_export_config_fields:
            config = getattr(cls.ResponseConfig, field, ...)
            if config is not ...:
                export_config[field] = config

        cls._export_config = export_config

        super().__init_subclass__(**kwargs)

    def flask_response(self):
        return current_app.response_class(
            response=self.json(**self._export_config) if self._export_config else self.json(),
            mimetype=self._mime_type,
            status=self._status_code
        )

    @classmethod
    def schema(cls) -> openapi.Schema:
        return PydanticSchema(schema_class=cls)


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
