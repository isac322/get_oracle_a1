from pydantic import BaseModel


class Command(BaseModel):
    class Config:
        allow_mutation = False
        orm_mode = True


class IncreaseResource(Command):
    instance_ocid: str
    target_ocpu: int
    target_memory: int
