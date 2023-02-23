import re

import openapi_schema_pydantic as openapi
from flask.views import http_method_funcs

from .handler import HttpHandler

_PATH_REGEX = re.compile("<(?:(?P<converter>[A-Za-z_]\\w*):)?(?P<name>[A-Za-z_]\\w*)>")


def parse_path_for_parameters(path) -> dict[str, str]:
    m = _PATH_REGEX.findall(path)
    return {name: converter for converter, name in m}


def convert_to_openapi_format(path) -> str:
    return _PATH_REGEX.sub("{\\g<name>}", path)


class Path:

    def __init__(self, path: str):
        self.path = path
        self.path_parameters = parse_path_for_parameters(path)
        self.openapi_path = convert_to_openapi_format(path)


class BoundResource:

    def __init__(self, resource_cls, path: Path, methods: dict[str, HttpHandler]):
        self.resource_cls = resource_cls
        self.path = path
        self.methods = methods

    def generate_path_item(self) -> openapi.PathItem:
        docs = openapi.PathItem()
        for method, handler in self.methods.items():
            operation = handler.generate_operation()
            setattr(docs, method.lower(), operation)
        return docs


class TypedResource:

    @classmethod
    def bind(cls, path: str) -> BoundResource:
        path = Path(path)
        methods = {}
        for method in http_method_funcs:
            if handler_method := getattr(cls, method, None):
                handler = HttpHandler(path, cls, handler_method)
                methods[method.upper()] = handler

        return BoundResource(
            resource_cls=cls,
            path=path,
            methods=methods
        )
