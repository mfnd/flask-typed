from pydantic import BaseModel


class HttpError(Exception):
    status_code: int = ...

    class ResponseModel(BaseModel):
        message: str | None = None

    def __init_subclass__(cls, **kwargs):
        if not issubclass(cls.ResponseModel, BaseModel):
            raise TypeError(f"ResponseModel should inherit pydantic BaseModel: {cls.__name__}")

    def __init__(self, status_code: int | None = None, **kwargs):
        cls = self.__class__
        self.status_code = cls.status_code if status_code is None else status_code
        self.response = cls.ResponseModel(**kwargs)

    def json(self):
        return self.response.json()

    @classmethod
    def schema(cls):
        return cls.ResponseModel.schema()


class InternalServerError(HttpError):
    status_code = 500

    class ResponseModel(BaseModel):
        message: str = "Internal server error"


class NotFoundError(HttpError):
    status_code = 404

    class ResponseModel(BaseModel):
        message: str = "Not found"
