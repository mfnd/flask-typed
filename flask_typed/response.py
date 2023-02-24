from http.client import HTTPException
from inspect import isclass
from types import UnionType, NoneType
from typing import Type, get_origin, get_args

import openapi_schema_pydantic as openapi
from openapi_schema_pydantic.util import PydanticSchema

from .docs_utils import DocsMetadata
from .errors import HttpError


class Response:

    def __init__(
            self,
            return_type: Type,
            success_models: list[Type],
            error_models: dict[int, Type],
            is_body_optional: bool,
            description: str
    ):
        self.return_type = return_type
        self.success_models = success_models
        self.error_models = error_models
        self.is_body_optional = is_body_optional
        self.description = description

    @staticmethod
    def from_type(return_type, docs: DocsMetadata, description: str = ""):
        success_models = []
        error_models = {}
        allow_none = False

        origin_type = get_origin(return_type)
        if origin_type is UnionType:
            types = get_args(return_type)
        else:
            types = [return_type]

        for response_type in types:
            if response_type is NoneType:
                allow_none = True
            elif isclass(response_type) and issubclass(response_type, HTTPException):
                error_models[response_type.status_code] = response_type
            else:
                success_models.append(response_type)

        if docs:
            for error in docs.errors:
                error_models[error.status_code] = error

        return Response(
            return_type=return_type,
            success_models=success_models,
            error_models=error_models,
            is_body_optional=allow_none,
            description=description
        )

    def to_openapi_responses(self) -> dict[str, openapi.Response]:
        responses = {}
        match self.success_models:
            case models if len(self.success_models) > 1:
                schema = openapi.Schema(
                    oneOf=[PydanticSchema(schema_class=model) for model in models]
                )
            case [model]:
                schema = PydanticSchema(schema_class=model)
            case _:
                raise TypeError(f"Invalid return type: {self.return_type}")

        responses["200"] = openapi.Response(
            description=self.description,
            content={
                "application/json": openapi.MediaType(
                    schema=schema
                )
            }
        )

        for status_code, error_model in self.error_models.items():
            if (isclass(error_model) and issubclass(error_model, HttpError)) or isinstance(error_model,
                                                                                           HttpError):
                responses[str(status_code)] = openapi.Response(
                    description="",
                    content={
                        "application/json": openapi.MediaType(
                            schema=error_model.schema()
                        )
                    }
                )

        return responses
