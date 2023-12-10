import json
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
from .parsers import QueryParser, HeaderParser
from .validators import VALIDATORS


class ParameterLocation(IntEnum):
    PATH = 1
    QUERY = 2
    BODY = 3
    HEADER = 4


class Parameter:

    def __init__(
            self,
            name: str,
            source: str,
            location: ParameterLocation,
            param_type: Type,
            description: str,
            default_value: Any,
    ):
        self.name = name
        self.source = source
        self.location = location
        self.description = description
        self.is_optional = False
        self.type = param_type
        self.default_value = default_value

        self._init_types(param_type)
        self._init_data_getter()
        self._init_validator(self.type)

    def _init_types(self, param_type: Type):
        actual_type = None
        origin_type = get_origin(param_type)
        if origin_type is UnionType:
            for alternate_type in get_args(param_type):
                if alternate_type is NoneType:
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

    def _init_data_getter(self):
        match self.location:
            case ParameterLocation.QUERY:
                def get_query_param(request, _path_params):
                    return request.args.get(self.source)
                self.get_data = get_query_param
            case ParameterLocation.HEADER:
                def get_header_param(request, _path_params):
                    return request.headers.get(self.source)
                self.get_data = get_header_param
            case ParameterLocation.PATH:
                def get_path_param(_request, path_params):
                    return path_params.get(self.source)
                self.get_data = get_path_param
            case ParameterLocation.BODY:
                def get_body_param(request, _path_params):
                    return request.data
                self.get_data = get_body_param
            case _:
                raise ValueError(f"Invalid parameter location: {self.location}")

    def _init_validator(self, param_type):
        if issubclass(param_type, BaseModel):
            def model_validator(value):
                return param_type.parse_obj(
                    json.loads(value)
                )
            self.validator = model_validator
        elif validator := VALIDATORS.get(param_type):
            self.validator = validator
        else:
            self.validator = param_type

    def validate(self, request, path_params):
        value = self.get_data(request, path_params)
        if value is None:
            if self.is_optional is True:
                return self.default_value
            else:
                raise ParameterValidationError(self, errors=["Parameter is not optional"])
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
        elif isclass(self.type) and issubclass(self.type, (QueryParser, HeaderParser)):
            parameters.extend(self.type.schema())
        else:
            schema = get_builtin_type(self.type)
            if schema is None:
                raise TypeError(f"Unsupported type for parameter '{self.name}': {self.type}")

            if self.default_value is not Ellipsis:
                schema.default = self.default_value
            parameters.append(
                openapi.Parameter(
                    name=self.source,
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
            schema = get_builtin_type(self.type)
            if schema is None:
                raise TypeError(f"Unsupported type for parameter '{self.name}': {self.type}")

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
            parameter=self.parameter.source,
            location=self.parameter.location.name.lower(),
            details=details
        )


class ValidationError(HttpError):
    status_code = 422

    class ResponseModel(BaseModel):
        errors: list[ParameterValidationErrorModel]
