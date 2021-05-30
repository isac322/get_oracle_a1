from pydantic import BaseModel


class ResourceLimit(BaseModel):
    ocpu: int
    memory: int

    class Config:
        allow_mutation = False


class IncreaseStep(BaseModel):
    ocpu: int
    memory: int

    class Config:
        allow_mutation = False
