from typing import Optional

from pydantic import BaseModel


class Command(BaseModel):
    class Config:
        allow_mutation = False
        orm_mode = True


class IncreaseResource(Command):
    instance_ocid: str
    target_ocpu: int
    target_memory: int


class CreateA1(Command):
    availability_domain: str
    display_name: str
    os_name: str
    os_version: Optional[str]
    subnet_id: Optional[str]
    target_ocpu: Optional[int]
    target_memory: Optional[int]


class ListAvailabilityDomain(Command):
    pass


class ListAvailableSubnet(Command):
    pass
