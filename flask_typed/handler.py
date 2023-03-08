import inspect
import json
from inspect import isclass
from typing import Any, get_origin, Annotated, get_args

import openapi_schema_pydantic as openapi
from flask import request, current_app
from pydantic import BaseModel

from flask_typed.docs.utils import Docstring
from .errors import HttpError
from .parameter import ParameterLocation, Parameter, ParameterValidationError, ValidationError
from flask_typed.docs.responses import ResponsesDocsBuilder
from .response import BaseResponse


class HttpHandler:

    def __init__(self, path, resource_cls, handler):
        self.resource_cls = resource_cls
        self.path = path
        self.handler = handler
        docstring = getattr(handler, "__doc__", None)
        self.docstring = Docstring(docstring) if docstring else None
        self.docs_metadata = getattr(handler, "docs_metadata", None)
        self.responses = None
        self.parameters: list[Parameter] = []
        self.path_parameters = {}
        self.query_parameters = {}
        self.header_parameters = {}
        self.body_param = None

        self._process_annotations()

    def _process_annotations(self):
        handler_signature = inspect.signature(self.handler)
        for parameter in handler_signature.parameters.values():
            if parameter.name == "self":
                continue

            source_name = parameter.name
            param_type = parameter.annotation
            if param_type is None:
                raise TypeError(f"No type annotation is provided for parameter: {parameter.name}")

            if get_origin(param_type) == Annotated:
                metadata = get_args(param_type)
                param_type = metadata[0]
                location = metadata[1]

                if location == ParameterLocation.HEADER:
                    source_name = "-".join(
                        s.capitalize() for s in parameter.name.split("_")
                    )
                if len(metadata) > 2:
                    source_name = metadata[2]

            elif isclass(param_type) and issubclass(param_type, BaseModel):
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
                source=source_name,
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
                case ParameterLocation.HEADER:
                    self.header_parameters[parameter.name] = parameter
                case ParameterLocation.BODY:
                    self.body_param = parameter

        self.responses = ResponsesDocsBuilder(
            return_type=handler_signature.return_annotation,
            docstring=self.docstring,
            docs=self.docs_metadata
        ).build()

    def generate_operation(self) -> openapi.Operation:
        doc_parameters = []
        request_body = None
        for param in self.parameters:
            match param.location:
                case ParameterLocation.QUERY | ParameterLocation.PATH | ParameterLocation.HEADER:
                    doc_parameters.extend(param.to_openapi_parameters())
                case ParameterLocation.BODY:
                    request_body = param.to_openapi_request_body()

        return openapi.Operation(
            parameters=doc_parameters,
            responses=self.responses,
            requestBody=request_body,
            summary=self.docstring.short_description if self.docstring else "",
            description=self.docstring.long_description if self.docstring else "",
        )

    def get_handler(self):
        path_params = self.path_parameters
        query_params = self.query_parameters
        header_params = self.header_parameters
        body_param = self.body_param
        handler = self.handler
        resource_cls = self.resource_cls

        def perform_validation(kwargs) -> dict[str, Any]:
            validated_args = {}
            validation_errors = []
            for name, param in path_params.items():
                val = kwargs.get(param.source)
                try:
                    validated_args[name] = param.validate(val)
                except ParameterValidationError as e:
                    validation_errors.append(e)

            for name, param in query_params.items():
                val = request.args.get(param.source)
                try:
                    validated_args[name] = param.validate(val)
                except ParameterValidationError as e:
                    validation_errors.append(e)

            for name, param in header_params.items():
                val = request.headers.get(param.source)
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
                return e.flask_response()

            try:
                response_value = handler(resource_cls, **validated_args)
            except HttpError as e:
                return e.flask_response()

            if isinstance(response_value, BaseResponse):
                return response_value.flask_response()
            if isinstance(response_value, BaseModel):
                return current_app.response_class(
                    response=response_value.json(),
                    status=getattr(response_value.Config, "status_code", 200),
                    mimetype='application/json',
                )
            else:
                return response_value

        return validated

    def _get_parameter_description(self, param_name) -> str:
        return "" if self.docstring is None else self.docstring.get_parameter_description(param_name)
