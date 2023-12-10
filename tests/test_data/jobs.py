from datetime import date

from pydantic import BaseModel, Field

from flask_typed import TypedResource


class JobResult(BaseModel):
    job_date: date = Field(alias="date")

    id: int
    success: bool


class JobsResource(TypedResource):

    def post(self, job_id: int, job_date: date) -> JobResult:
        """
        Retrieves user

        User can be queried with query parameters

        :param job_id: Job Type ID
        :param job_date: The date the job will be run for
        :return: Job result
        """

        return JobResult(
            id=job_id,
            date=job_date,
            success=True
        )
