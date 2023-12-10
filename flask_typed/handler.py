import inspect
from inspect import isclass
from typing import Any, get_origin, Annotated, get_args, Type

import openapi_schema_pydantic as openapi
from flask import request, current_app
from pydantic import BaseModel

from flask_typed.docs.responses import ResponsesDocsBuilder
from flask_typed.docs.utils import Docstring
from .errors import HttpError
from .parameter import ParameterLocation, Parameter, ParameterValidationError, ValidationError
from .parsers import RequestParser
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
        self.request_parsers: dict[str, Type[RequestParser]] = {}

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

            if isclass(param_type) and issubclass(param_type, RequestParser):
                self.request_parsers[source_name] = param_type
                continue

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
        parameters = self.parameters
        parsers = self.request_parsers
        handler = self.handler
        resource_cls = self.resource_cls

        def perform_validation(kwargs) -> dict[str, Any]:
            validated_args = {}
            validation_errors = []

            for param in parameters:
                try:
                    validated_args[param.name] = param.validate(request, kwargs)
                except ParameterValidationError as e:
                    validation_errors.append(e)

            for name, parser in parsers.items():
                try:
                    validated_args[name] = parser.parse_request(request)
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
                response_value = handler(resource_cls(), **validated_args)
            except HttpError as e:
                return e.flask_response()

            if isinstance(response_value, BaseResponse):
                return response_value.flask_response()
            if isinstance(response_value, BaseModel):
                return current_app.response_class(
                    response=response_value.json(by_alias=True),
                    status=getattr(response_value.Config, "status_code", 200),
                    mimetype='application/json',
                )
            else:
                return response_value

        return validated

    def _get_parameter_description(self, param_name) -> str:
        return "" if self.docstring is None else self.docstring.get_parameter_description(param_name)
