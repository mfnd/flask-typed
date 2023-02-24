import inspect
import json
from inspect import isclass
from types import FunctionType
from typing import Any

import openapi_schema_pydantic as openapi
from flask import request, current_app
from pydantic import BaseModel

from .docs_utils import Docstring
from .errors import HttpError
from .response import Response
from .parameter import ParameterLocation, Parameter, ParameterValidationError, ValidationError


def get_parameter_defaults(func: FunctionType):
    defaults_len = len(func.__defaults__)
    for arg_name, arg_default in zip(func.__code__.co_varnames[-defaults_len:], func.__defaults__):
        pass


class HttpHandler:

    def __init__(self, path, resource_cls, handler):
        self.resource_cls = resource_cls
        self.path = path
        self.handler = handler
        docstring = getattr(handler, "__doc__", None)
        self.docstring = Docstring(docstring) if docstring else None
        self.docs_metadata = getattr(handler, "docs_metadata", None)
        self.response = None
        self.parameters: list[Parameter] = []
        self.path_parameters = {}
        self.query_parameters = {}
        self.body_param = None

        self._process_annotations()

    def _process_annotations(self):
        handler_signature = inspect.signature(self.handler)
        for parameter in handler_signature.parameters.values():
            if parameter.name == "self":
                continue

            param_type = parameter.annotation
            if param_type is None:
                raise TypeError(f"No type annotation is provided for parameter: {parameter.name}")

            if isclass(param_type) and issubclass(param_type, BaseModel):
                location = ParameterLocation.BODY
            elif parameter.name in self.path.path_parameters:
                location = ParameterLocation.PATH
            else:
                location = ParameterLocation.QUERY

            match parameter.default:
                case parameter.empty:
                    default_value = ...
                case other:
                    default_value = other

            parameter = Parameter(
                name=parameter.name,
                location=location,
                param_type=param_type,
                description=self._get_parameter_description(parameter.name),
                default_value=default_value
            )

            self.parameters.append(parameter)
            match parameter.location:
                case ParameterLocation.PATH:
                    self.path_parameters[parameter.name] = parameter
                case ParameterLocation.QUERY:
                    self.query_parameters[parameter.name] = parameter
                case ParameterLocation.BODY:
                    self.body_param = parameter

        self.response = Response.from_type(
            handler_signature.return_annotation,
            self.docs_metadata,
            self._get_return_description()
        )

    def generate_operation(self) -> openapi.Operation:
        doc_parameters = []
        request_body = None
        for param in self.parameters:
            match param.location:
                case ParameterLocation.QUERY | ParameterLocation.PATH:
                    doc_parameters.extend(param.to_openapi_parameters())
                case ParameterLocation.BODY:
                    request_body = param.to_openapi_request_body()

        responses = self.response.to_openapi_responses()

        return openapi.Operation(
            parameters=doc_parameters,
            responses=responses,
            requestBody=request_body,
            summary=self.docstring.short_description if self.docstring else "",
            description=self.docstring.long_description if self.docstring else "",
        )

    def get_handler(self):
        path_params = self.path_parameters
        query_params = self.query_parameters
        body_param = self.body_param
        handler = self.handler
        resource_cls = self.resource_cls

        def perform_validation(kwargs) -> dict[str, Any]:
            validated_args = {}
            validation_errors = []
            for name, param in path_params.items():
                val = kwargs.get(name)
                try:
                    validated_args[name] = param.validate(val)
                except ParameterValidationError as e:
                    validation_errors.append(e)

            for name, param in query_params.items():
                val = request.args.get(name)
                try:
                    validated_args[name] = param.validate(val)
                except ParameterValidationError as e:
                    validation_errors.append(e)

            if body_param:
                try:
                    validated_args[body_param.name] = body_param.validate(
                        json.loads(request.data)
                    )
                except ParameterValidationError as e:
                    validation_errors.append(e)

            if validation_errors:
                raise ValidationError(errors=[
                    err.to_model() for err in validation_errors
                ])

            return validated_args

        def validated(*_args, **kwargs):
            try:
                validated_args = perform_validation(kwargs)
            except HttpError as e:
                return current_app.response_class(
                    response=e.json(),
                    status=e.status_code,
                    mimetype='application/json',
                )

            try:
                response_value = handler(resource_cls, **validated_args)
            except HttpError as e:
                return current_app.response_class(
                    response=e.json(),
                    status=e.status_code,
                    mimetype='application/json',
                )

            if isinstance(response_value, BaseModel):
                return current_app.response_class(
                    response=response_value.json(),
                    status=200,
                    mimetype='application/json',
                )
            else:
                return response_value

        return validated

    def _get_parameter_description(self, param_name) -> str:
        return "" if self.docstring is None else self.docstring.get_parameter_description(param_name)

    def _get_return_description(self) -> str:
        if self.docstring:
            return self.docstring.returns.description
        return ""
