from typing import Generator, ClassVar, TypedDict, NotRequired

import openapi_pydantic as openapi
from flask import current_app, stream_with_context
from openapi_pydantic.util import PydanticSchema
from pydantic import BaseModel, RootModel

_pydantic_export_config_fields = [
    "include",
    "exclude",
    "by_alias",
    "exclude_unset",
    "exclude_defaults",
    "exclude_none"
]


class JsonConfig(TypedDict):
    include: NotRequired[str | set[str]]
    exclude: NotRequired[str | set[str]]
    by_alias: NotRequired[bool]
    exclude_unset: NotRequired[bool]
    exclude_defaults: NotRequired[bool]
    exclude_none: NotRequired[bool]
    round_trip: NotRequired[bool]
    warnings: NotRequired[bool]


class BaseResponseConfig:
    mime_type: str = "text/plain"
    status_code: int = 200


class BaseResponse:

    mime_type: ClassVar[str] = "text/plain"
    status_code: ClassVar[int] = 200

    def flask_response(self):
        raise NotImplementedError

    @classmethod
    def schema(cls) -> openapi.Schema:
        raise NotImplementedError


class ModelResponse(BaseResponse):

    json_config: ClassVar[dict] = {}

    mime_type = "application/json"

    def __init_subclass__(cls: type[BaseModel], **kwargs):
        if not issubclass(cls, BaseModel):
            raise TypeError(f"Type {cls.__name__} should be subclass of {BaseModel} since it is a subclass of "
                            f"ModelResponse")

        super().__init_subclass__(**kwargs)

    def flask_response(self):
        return current_app.response_class(
            response=self.model_dump_json(**self.json_config),
            mimetype=self.mime_type,
            status=self.status_code
        )

    @classmethod
    def schema(cls) -> openapi.Schema:
        return PydanticSchema(schema_class=cls)


class BaseModelResponse(BaseModel, ModelResponse):
    pass


class RootModelResponse(RootModel, ModelResponse):
    pass


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

    @classmethod
    def schema(cls) -> openapi.Schema:
        return openapi.Schema(type="string")