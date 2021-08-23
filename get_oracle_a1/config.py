from functools import cache
from typing import Optional

from pydantic import BaseModel


class OCIUser(BaseModel):
    user: str
    key_content: Optional[str]
    key_file: Optional[str]
    fingerprint: str
    tenancy: str
    region: str

    class Config:
        frozen = True

    @property
    @cache
    def config(self) -> dict[str, str]:
        return self.dict()

    @property
    def compartment_id(self):
        return self.tenancy
