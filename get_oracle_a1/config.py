from functools import cache

from pydantic import BaseSettings


class OCIUser(BaseSettings):
    user: str
    key_content: str
    fingerprint: str
    tenancy: str
    region: str

    class Config:
        env_prefix = 'oci_'
        frozen = True

    @property
    @cache
    def config(self) -> dict[str, str]:
        return self.dict()

    @property
    def compartment_id(self):
        return self.tenancy
