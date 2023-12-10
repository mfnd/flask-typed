import builtins
from datetime import date, datetime, time
from typing import Type
from uuid import UUID

import docstring_parser
import openapi_schema_pydantic as openapi

from flask_typed.errors import HttpError

_builtin_openapi_map = {
    builtins.bool: openapi.Schema(type="boolean"),
    builtins.str: openapi.Schema(type="string"),
    builtins.int: openapi.Schema(type="integer"),
    builtins.float: openapi.Schema(type="number"),
    datetime: openapi.Schema(type="string", format="date-time"),
    date: openapi.Schema(type="string", format="date"),
    time: openapi.Schema(type="string", format="time"),
    UUID: openapi.Schema(type="string", format="uuid"),
}


def get_builtin_type(ty: Type) -> openapi.Schema | None:
    if schema := _builtin_openapi_map.get(ty):
        return schema.copy()
    return None


class DocsMetadata:

    def __init__(
            self,
            errors: list[HttpError | Type[HttpError]] | None = None
    ):
        self.errors = errors if errors is not None else []


def docs(
        errors: list[HttpError | Type[HttpError]] | None = None
):
    def docs_decorator(func):
        func.docs_metadata = DocsMetadata(
            errors=errors
        )
        return func

    return docs_decorator


class Docstring:

    def __init__(self, docstring: str):
        docstring = docstring_parser.parse(docstring)
        self.short_description = docstring.short_description
        self.long_description = docstring.long_description
        self.params = {param.arg_name: param for param in docstring.params}
        self.returns = {returns.type_name: returns for returns in docstring.many_returns}
        self.raises = {exception.type_name: exception for exception in docstring.raises}

    def get_parameter_description(self, name: str) -> str:
        if parameter := self.params.get(name):
            return parameter.description
        return ""


redoc_template = """
<!DOCTYPE html>
<html>
  <head>
    <title>Redoc</title>
    <!-- needed for adaptive design -->
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">

    <!--
    Redoc doesn't change outer page styles
    -->
    <style>
      body {
        margin: 0;
        padding: 0;
      }
    </style>
  </head>
  <body>
    <redoc spec-url='{{ api_doc_url }}'></redoc>
    <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"> </script>
  </body>
</html>
"""