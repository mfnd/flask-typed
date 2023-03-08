from collections import defaultdict
from inspect import isclass
from types import UnionType
from typing import get_origin, get_args, NamedTuple, Type

import openapi_schema_pydantic as openapi
from openapi_schema_pydantic.util import PydanticSchema
from pydantic import BaseModel

from flask_typed.errors import HttpError
from flask_typed.response import BaseResponse


class ResponseInfo(NamedTuple):
    schema: openapi.Schema
    description: str | None


class ResponsesDocsBuilder:

    def __init__(self, return_type, docstring, docs):
        self.responses = defaultdict(lambda: defaultdict(list))
        self.return_type = return_type
        self.docs = docs
        self.docstring = docstring

    def build(self) -> dict[str, openapi.Response]:
        origin_type = get_origin(self.return_type)
        if origin_type is UnionType:
            types = get_args(self.return_type)
        else:
            types = [self.return_type]

        for response_type in types:
            self._add_response(response_type)

        if self.docs:
            for error_model in self.docs.errors:
                self._add_response(error_model)

        return self._merge_responses()

    def _add_response(self, response_type):
        if isclass(response_type):
            description = self._get_return_description(response_type)
            if issubclass(response_type, BaseModel):
                status_code = getattr(response_type.Config, "status_code", 200)
                self.responses[status_code]["application/json"].append(
                    ResponseInfo(
                        schema=PydanticSchema(schema_class=response_type),
                        description=description
                    )
                )
            elif issubclass(response_type, BaseResponse):
                status_code = response_type.status_code
                mime_type = response_type.mime_type
                schema = response_type.schema()
                if not isinstance(schema, openapi.Schema):
                    raise TypeError(
                        f"Response type {response_type} extending BaseResponse"
                        f" does not implement schema() method properly: {schema}"
                    )

                self.responses[status_code][mime_type].append(
                    ResponseInfo(
                        schema=schema,
                        description=description
                    )
                )
            elif issubclass(response_type, HttpError):
                self.responses[response_type.status_code]["application/json"].append(
                    ResponseInfo(
                        schema=response_type.schema(),
                        description=description
                    )
                )
        else:
            description = self._get_return_description(response_type.__class__)
            if isinstance(response_type, HttpError):
                self.responses[response_type.status_code]["application/json"].append(
                    ResponseInfo(
                        schema=response_type.schema(),
                        description=description
                    )
                )

    def _merge_responses(self) -> dict[str, openapi.Response]:
        response_docs = {}
        for status_code, responses_with_status in self.responses.items():
            contents = {}
            description = None
            for mime_type, response_info_list in responses_with_status.items():
                if len(response_info_list) == 1:
                    schema = response_info_list[0].schema
                else:
                    schema = openapi.Schema(
                        oneOf=[response_info.schema for response_info in response_info_list]
                    )
                for response_info in response_info_list:
                    if description:
                        break
                    description = response_info.description

                contents[mime_type] = openapi.MediaType(schema=schema)

            # If no description is found for specific return type, use generic return docstring for successes
            if not description and 200 <= status_code < 300:
                description = self._get_return_description(None)

            response_docs[str(status_code)] = openapi.Response(
                description=description if description else "",
                content=contents
            )

        return response_docs

    def _get_return_description(self, return_type: Type | None) -> str | None:
        if self.docstring:
            key = return_type.__name__ if return_type is not None else None
            if returns := self.docstring.returns.get(key):
                return returns.description
            if raises := self.docstring.raises.get(key):
                return raises.description
        return None
