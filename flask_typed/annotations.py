from typing import TypeVar, Annotated

from flask_typed.parameter import ParameterLocation

_T = TypeVar("T")

Query = Annotated[_T, ParameterLocation.QUERY]
Path = Annotated[_T, ParameterLocation.PATH]
Header = Annotated[_T, ParameterLocation.HEADER]
