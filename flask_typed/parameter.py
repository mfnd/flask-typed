from enum import IntEnum
from inspect import isclass
from types import UnionType, NoneType
from typing import Type, Any, get_origin, get_args, Sequence

import openapi_schema_pydantic as openapi
import pydantic
from openapi_schema_pydantic.util import PydanticSchema
from pydantic import BaseModel

from flask_typed.docs.utils import get_builtin_type
from .errors import HttpError


class ParameterLocation(IntEnum):
    PATH = 1
    QUERY = 2
    BODY = 3
    HEADER = 4


class Parameter:

    def __init__(
            self,
            name: str,
            location: ParameterLocation,
            param_type: Type,
            description: str,
            default_value: Any
    ):
        self.name = name
        self.location = location
        self.description = description
        self.is_optional = False
        self.type = param_type
        self.default_value = default_value

        self._init_types(param_type)
        self._init_validator(self.type, self.is_optional)

    def _init_types(self, param_type: Type):
        allow_none = False
        actual_type = None
        origin_type = get_origin(param_type)
        if origin_type is UnionType:
            for alternate_type in get_args(param_type):
                if alternate_type is NoneType:
                    allow_none = True
                    continue
                if actual_type is not None:
                    raise Exception("Multiple argument types are provided")
                actual_type = alternate_type
        else:
            actual_type = param_type

        self.type = actual_type

        if self.default_value is Ellipsis:
            self.is_optional = False
        else:
            self.is_optional = True

    def _init_validator(self, param_type, allow_none: bool):
        def validator(value):
            if value is None:
                if allow_none is True:
                    return None
                else:
                    raise ValueError("Parameter is not optional")

            if issubclass(param_type, BaseModel):
                return param_type.parse_obj(value)

            return param_type(value)

        self.validator = validator

    def validate(self, value):
        try:
            return self.validator(value)
        except pydantic.ValidationError as e:
            raise ParameterValidationError(self, errors=[e])
        except Exception as e:
            raise ParameterValidationError(self, errors=[str(e)])

    def to_openapi_parameters(self) -> list[openapi.Parameter]:
        location = self.location.name.lower()
        parameters = []
        if isclass(self.type) and issubclass(self.type, BaseModel):
            query_schema = self.type.schema_json()
            for name, prop in query_schema["properties"].items():
                parameters.append(
                    openapi.Parameter(
                        name=name,
                        param_in=location,
                        param_schema=openapi.Schema.parse_obj(prop)
                    )
                )
        else:
            openapi_type = get_builtin_type(self.type)
            if openapi_type is None:
                raise TypeError(f"Unsupported type for parameter '{self.name}': {self.type}")

            schema = openapi.Schema(type=openapi_type)
            if self.default_value is not Ellipsis:
                schema.default = self.default_value
            parameters.append(
                openapi.Parameter(
                    name=self.name,
                    description=self.description,
                    param_in=location,
                    param_schema=schema,
                    required=not self.is_optional
                )
            )
        return parameters

    def to_openapi_request_body(self) -> openapi.RequestBody:
        if isclass(self.type) and issubclass(self.type, BaseModel):
            schema = PydanticSchema(schema_class=self.type)
        else:
            openapi_type = get_builtin_type(self.type)
            if openapi_type is None:
                raise TypeError(f"Unsupported type for parameter '{self.name}': {self.type}")

            schema = openapi_type

        return openapi.RequestBody(
            content={
                "application/json": openapi.MediaType(
                    schema=schema
                )
            }
        )


def repr_pydantic_validation_error(err: pydantic.ValidationError) -> Sequence[str]:
    for error in err.errors():
        yield f"{error['msg']}: {'.'.join(error['loc'])}"


class ParameterValidationErrorModel(BaseModel):
    parameter: str
    location: str
    details: list[str]


class ParameterValidationError(Exception):

    def __init__(self, parameter: Parameter, errors: list[str | pydantic.ValidationError]):
        self.parameter = parameter
        self.errors = errors

    def to_model(self):
        details = []
        for error in self.errors:
            if isinstance(error, pydantic.ValidationError):
                details.extend(repr_pydantic_validation_error(error))
            else:
                details.append(error)

        return ParameterValidationErrorModel(
            parameter=self.parameter.name,
            location=self.parameter.location.name.lower(),
            details=details
        )


class ValidationError(HttpError):
    status_code = 422

    class ResponseModel(BaseModel):
        errors: list[ParameterValidationErrorModel]
