from pydantic import BaseModel


class ProjectSchema(BaseModel):
    id: str
    key: str
    name: str
