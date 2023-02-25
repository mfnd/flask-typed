from pydantic import BaseModel

from flask_typed import TypedResource


class User(BaseModel):

    id: int
    name: str
    age: int


class UserCreateBody(BaseModel):

    name: str
    age: int


class UserResource(TypedResource):

    def get(
            self,
            user_id: int | None = None,
            name: str | None = None,
            age_gt: int | None = None
    ) -> User:
        """
        Retrieves user

        User can be queried with query parameters

        :param user_id: User ID
        :param name: First name
        :param age_gt: Age
        :return: User details
        """

        return User(
            id=user_id if user_id else 0,
            name=name if name else "default",
            age=10 if age_gt and age_gt < 10 else 5
        )

    def post(self, user: UserCreateBody) -> User:
        """
        Creates a user

        :param user: User details
        :return: Created user object
        """

        return User(
            id=0,
            name=user.name,
            age=user.age
        )
