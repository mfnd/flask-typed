import json
from typing import Type

from flask import Flask, render_template_string
from openapi_schema_pydantic import OpenAPI, Info
from openapi_schema_pydantic.util import construct_open_api_with_schema_class

from flask_typed.docs.utils import redoc_template
from .typed_resource import BoundResource, TypedResource


def join_path(path1: str, path2: str) -> str:
    return f"{path1.rstrip('/')}/{path2.lstrip('/')}"


class TypedBlueprint:

    def __init__(self):
        self.resources = {}

    def add_resource(self, resource: Type[TypedResource], path: str):
        self.resources[path] = resource


class TypedAPI:

    def __init__(
            self,
            app: Flask | None = None,
            version: str = "v0.0.1",
            description: str = "",
            openapi_path: str = "/openapi",
            docs_path: str = "/docs"
     ):
        self.app = app
        self.docs = OpenAPI(
            info=Info(
                title=description,
                version=version
            ),
            paths={}
        )
        self.resources: dict[str, BoundResource] = {}
        self.openapi_path = openapi_path
        self.docs_path = docs_path

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        if app is None:
            raise ValueError("No valid Flask instance is provided")
        self.app = app
        for url, resource in self.resources.items():
            self._register_resource(resource)

        def get_openapi_schema():
            return self.get_openapi_schema()

        def redoc():
            return render_template_string(
                redoc_template,
                api_doc_url=self.openapi_path
            )

        app.add_url_rule(self.docs_path, view_func=redoc)
        app.add_url_rule(self.openapi_path, view_func=get_openapi_schema)

    def add_resource(self, resource: Type[TypedResource], path: str):
        if path in self.resources:
            raise Exception(f"URL is already registered: {path}")
        bound_resource = resource.bind(path)
        self.resources[path] = bound_resource
        self.docs.paths[bound_resource.path.openapi_path] = bound_resource.generate_path_item()

        if self.app is not None:
            self._register_resource(bound_resource)

    def register_blueprint(self, blueprint: TypedBlueprint, url_prefix: str = ""):
        for path, resource in blueprint.resources.items():
            full_path = join_path(url_prefix, path)
            self.add_resource(resource, full_path)

    def _register_resource(self, bound_resource: BoundResource):
        for method, handler in bound_resource.methods.items():
            self.app.add_url_rule(
                bound_resource.path.path,
                bound_resource.resource_cls.__name__.lower() + method,
                handler.get_handler(),
                methods=[method],
                provide_automatic_options=False
            )

    def get_openapi_schema(self):
        open_api = construct_open_api_with_schema_class(self.docs)
        return json.loads(open_api.json(by_alias=True, exclude_none=True))
