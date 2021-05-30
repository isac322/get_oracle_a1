from oci.core.models import Instance
from pydantic import BaseModel


class Command(BaseModel):
    class Config:
        allow_mutation = False
        orm_mode = True


class IncreaseResource(Command):
    display_name: str
    target_ocpu: int
    target_memory: int
