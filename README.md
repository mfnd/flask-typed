# flask-typed

A Flask extension for developing HTTP APIs using type annotations. Type annotations are used for the validation of requests and generating API documentation.

## Example

```python
from flask import Flask
from pydantic import BaseModel

from flask_typed import TypedResource, TypedAPI


class HelloResponse(BaseModel):

    message: str
    sender: str
    receiver: str


class HelloResource(TypedResource):

    def get(self, sender: str, receiver: str) -> HelloResponse:
        """
        Greets someone

        :param sender: Greeter
        :param receiver: The one being greeted
        :return: Greetings
        """
        return HelloResponse(
            message=f"Hello to {receiver} from {sender}!",
            sender=sender,
            receiver=receiver
        )


app = Flask(__name__)
api = TypedAPI(app, version="1.0", description="Greetings API")

api.add_resource(HelloResource, "/hello/<sender>")

if __name__ == "__main__":
    app.run()
```