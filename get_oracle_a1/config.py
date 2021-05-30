from functools import cached_property

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
        keep_untouched = (cached_property,)

    @cached_property
    def config(self) -> dict[str, str]:
        return self.dict()

    @property
    def compartment_id(self):
        return self.tenancy
