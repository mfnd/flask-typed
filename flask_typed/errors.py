from abc import ABC

import openapi_pydantic as openapi
from flask import current_app
from pydantic import BaseModel

from http import HTTPStatus
from .response import BaseResponse


class BaseHttpError(Exception, BaseResponse, ABC):
    pass


class HttpError(BaseHttpError):
    mime_type = "application/json"

    class ResponseModel(BaseModel):
        message: str | None = None

    def __init_subclass__(cls, **kwargs):
        if not issubclass(cls.ResponseModel, BaseModel):
            raise TypeError(
                f"ResponseModel should inherit pydantic BaseModel: {cls.__name__}"
            )

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
        return self.response.model_dump_json()

    @classmethod
    def schema(cls) -> openapi.Schema:
        return openapi.Schema.model_validate(cls.ResponseModel.model_json_schema())


class MessageHttpError(HttpError):
    message: str = "Error"

    def __init_subclass__(cls, **kwargs):
        class ResponseModel(BaseModel):
            message: str | None = cls.message

        cls.ResponseModel = ResponseModel


class BadRequestError(HttpError):
    status_code = HTTPStatus.BAD_REQUEST
    message = "Bad request"


class NotFoundError(HttpError):
    status_code = HTTPStatus.NOT_FOUND
    message = "Not found"


class InternalServerError(HttpError):
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    message = "Internal server error"


class TooManyRequestsError(HttpError):
    status_code = HTTPStatus.TOO_MANY_REQUESTS
    message = "Internal server error"


class MethodNotAllowedError(HttpError):
    status_code = HTTPStatus.METHOD_NOT_ALLOWED
    message = "Method not allowed"


class ConflictError(HttpError):
    status_code = HTTPStatus.CONFLICT
    message = "Conflict"


class UnsupportedMediaTypeError(HttpError):
    status_code = HTTPStatus.UNSUPPORTED_MEDIA_TYPE
    message = "Unsupported media type"
