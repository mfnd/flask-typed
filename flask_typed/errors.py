from abc import ABC

import openapi_schema_pydantic as openapi
from flask import current_app
from pydantic import BaseModel

from .response import BaseResponse


class BaseHttpError(Exception, BaseResponse, ABC):
    pass


class HttpError(BaseHttpError):
    mime_type = "application/json"

    class ResponseModel(BaseModel):
        message: str | None = None

    def __init_subclass__(cls, **kwargs):
        if not issubclass(cls.ResponseModel, BaseModel):
            raise TypeError(f"ResponseModel should inherit pydantic BaseModel: {cls.__name__}")

    def __init__(self, status_code: int | None = None, **kwargs):
        cls = self.__class__
        self.status_code = cls.status_code if status_code is None else status_code
        self.response = cls.ResponseModel(**kwargs)

    def flask_response(self):
        return current_app.response_class(
            response=self.json(),
            status=self.status_code,
            mimetype=self.mime_type,
        )

    def json(self) -> str:
        return self.response.json()

    @classmethod
    def schema(cls) -> openapi.Schema:
        return openapi.Schema.parse_obj(cls.ResponseModel.schema())


class MessageHttpError(HttpError):
    message: str = "Error"

    def __init_subclass__(cls, **kwargs):
        class ResponseModel(BaseModel):
            message: str | None = cls.message

        cls.ResponseModel = ResponseModel


class BadRequestError(MessageHttpError):
    status_code = 400
    message = "Bad request"


class NotFoundError(HttpError):
    status_code = 404
    message = "Not found"


class InternalServerError(HttpError):
    status_code = 500
    message = "Internal server error"
