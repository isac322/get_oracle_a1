from typing import Optional

from oci.core import ComputeClient
from oci.core.models import (
    Instance,
    UpdateInstanceDetails,
    UpdateInstanceShapeConfigDetails,
)
from oci.limits import LimitsClient

from get_oracle_a1.config import OCIUser
from get_oracle_a1.models import ResourceLimit, IncreaseStep


def find_target_instance(oci_user: OCIUser, display_name: str) -> Optional[Instance]:
    client = ComputeClient(config=oci_user.config)
    list_query = client.list_instances(oci_user.compartment_id)

    instance: Instance
    for instance in list_query.data:
        if instance.display_name == display_name:
            return instance

    return None


def get_res_limit(oci_user: OCIUser, availability_domain: str) -> ResourceLimit:
    client = LimitsClient(config=oci_user.config)
    ocpu_res = client.list_limit_values(
        compartment_id=oci_user.compartment_id,
        service_name='compute',
        name='standard-a1-core-count',
        availability_domain=availability_domain,
    ).data
    if len(ocpu_res) != 1:
        raise RuntimeError('A1 is not available')
    memory_res = client.list_limit_values(
        compartment_id=oci_user.compartment_id,
        service_name='compute',
        name='standard-a1-memory-count',
        availability_domain=availability_domain,
    ).data
    if len(memory_res) != 1:
        raise RuntimeError('A1 is not available')

    return ResourceLimit(
        ocpu=ocpu_res[0].value,
        memory=memory_res[0].value,
    )


def increase_resource(
    oci_user: OCIUser, instance: Instance, step: IncreaseStep
) -> None:
    client = ComputeClient(config=oci_user.config)
    client.update_instance(
        instance_id=instance.id,
        update_instance_details=UpdateInstanceDetails(
            shape_config=UpdateInstanceShapeConfigDetails(
                ocpus=step.ocpu,
                memory_in_gbs=step.memory,
            )
        ),
    )


def check_a1_available(oci_user: OCIUser) -> bool:
    pass


def calc_next_increase_step(
    instance: Instance, resource_limit: ResourceLimit
) -> IncreaseStep:
    base_ocpu_step = 1
    base_memory_step = resource_limit.memory // resource_limit.ocpu

    return IncreaseStep(
        ocpu=min(instance.shape_config.ocpus + base_ocpu_step, resource_limit.ocpu),
        memory=min(
            instance.shape_config.memory_in_gbs + base_memory_step,
            resource_limit.memory,
        ),
    )


def verify_instance_for_increasing(
    instance: Instance, resource_limit: ResourceLimit
) -> None:
    if instance.shape != 'VM.Standard.A1.Flex':
        # TODO: custom exception
        raise ValueError(f'{instance.shape} is not A1 Flex')

    if (
        instance.shape_config.ocpus >= resource_limit.ocpu
        and instance.shape_config.memory_in_gbs >= resource_limit.memory
    ):
        # TODO: custom exception
        raise ValueError('No room for resource extending')
