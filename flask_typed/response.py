from collections import defaultdict
from inspect import isclass
from types import UnionType, NoneType
from typing import Type, get_origin, get_args

import openapi_schema_pydantic as openapi
from openapi_schema_pydantic.util import PydanticSchema
from pydantic import BaseModel

from .docs_utils import DocsMetadata, Docstring
from .errors import HttpError


class Response:

    def __init__(
            self,
            return_type: Type,
            success_models: dict[int, list[Type]],
            error_models: dict[int, Type],
            is_body_optional: bool,
            docstring: Docstring
    ):
        self.return_type = return_type
        self.success_models = success_models
        self.error_models = error_models
        self.is_body_optional = is_body_optional
        self.docstring = docstring

    @staticmethod
    def from_type(return_type, docstring: Docstring, docs: DocsMetadata):
        success_models = defaultdict(list)
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
            elif isclass(response_type):
                if issubclass(response_type, HttpError):
                    error_models[response_type.status_code] = response_type
                elif issubclass(response_type, BaseModel):
                    status_code = getattr(response_type.Config, "status_code", 200)
                    success_models[status_code].append(response_type)
            else:
                success_models[200].append(response_type)

        if docs:
            for error in docs.errors:
                error_models[error.status_code] = error

        return Response(
            return_type=return_type,
            success_models=success_models,
            error_models=error_models,
            is_body_optional=allow_none,
            docstring=docstring
        )

    def to_openapi_responses(self) -> dict[str, openapi.Response]:
        responses = {}

        for status_code, response_models in self.success_models.items():
            match response_models:
                case models if len(response_models) > 1:
                    schema = openapi.Schema(
                        oneOf=[PydanticSchema(schema_class=model) for model in models]
                    )
                case [model]:
                    schema = PydanticSchema(schema_class=model)
                case _:
                    raise TypeError(f"Invalid return type: {self.return_type}")

            responses[str(status_code)] = openapi.Response(
                description=self._get_return_description(),
                content={
                    "application/json": openapi.MediaType(
                        schema=schema
                    )
                }
            )

        for status_code, error_model in self.error_models.items():
            if isclass(error_model) and issubclass(error_model, HttpError):
                name = error_model.__name__
            elif isinstance(error_model, HttpError):
                name = error_model.__class__.__name__
            else:
                raise ValueError(f"Invalid error value/class is provided: {error_model}")

            description = ""
            if self.docstring and name in self.docstring.raises:
                description = self.docstring.raises[name].description

            responses[str(status_code)] = openapi.Response(
                description=description,
                content={
                    "application/json": openapi.MediaType(
                        schema=error_model.schema()
                    )
                }
            )

        return responses

    def _get_return_description(self) -> str:
        if self.docstring:
            return self.docstring.returns.description
        return ""
