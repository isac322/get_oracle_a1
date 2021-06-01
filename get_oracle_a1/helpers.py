from typing import Optional

from oci.core import ComputeClient
from oci.core.models import Instance, Shape, UpdateInstanceDetails, UpdateInstanceShapeConfigDetails
from oci.limits import LimitsClient

from get_oracle_a1.config import OCIUser
from get_oracle_a1.models import IncreaseStep, ResourceLimit

TARGET_SHAPE = 'VM.Standard.A1.Flex'


def find_target_instance(oci_user: OCIUser, display_name: str) -> Optional[Instance]:
    client = ComputeClient(config=oci_user.config)
    list_query = client.list_instances(oci_user.compartment_id)

    instance: Instance
    for instance in list_query.data:
        if instance.display_name == display_name:
            return instance

    return None


def get_instance(oci_user: OCIUser, ocid: str) -> Instance:
    client = ComputeClient(config=oci_user.config)
    return client.get_instance(instance_id=ocid).data


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


def increase_resource(oci_user: OCIUser, instance: Instance, step: IncreaseStep) -> None:
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


def find_target_shape(oci_user: OCIUser, shape: str) -> Optional[Shape]:
    compute_client = ComputeClient(config=oci_user.config)
    s: Shape
    for s in compute_client.list_shapes(oci_user.compartment_id).data:
        if s.shape == shape:
            return s
    return None


def calc_next_increase_step(
    oci_user: OCIUser, instance: Instance, target_ocpu: int, target_memory: int
) -> IncreaseStep:
    shape = find_target_shape(oci_user=oci_user, shape=TARGET_SHAPE)
    if shape is None:
        # TODO: custom exception
        raise RuntimeError(f'Failed to find shape {TARGET_SHAPE}')
    base_ocpu_step = shape.ocpu_options.min
    base_memory_step = shape.memory_options.default_per_ocpu_in_g_bs * base_ocpu_step

    resource_limit = get_res_limit(oci_user, instance.availability_domain)

    return IncreaseStep(
        ocpu=min(instance.shape_config.ocpus + base_ocpu_step, resource_limit.ocpu, target_ocpu),
        memory=min(
            instance.shape_config.memory_in_gbs + base_memory_step,
            resource_limit.memory,
            target_memory,
        ),
    )


def verify_instance_for_increasing(instance: Instance, resource_limit: ResourceLimit) -> None:
    if instance.shape != TARGET_SHAPE:
        # TODO: custom exception
        raise ValueError(f'{instance.shape} is not A1 Flex')

    if (
        instance.shape_config.ocpus >= resource_limit.ocpu
        and instance.shape_config.memory_in_gbs >= resource_limit.memory
    ):
        # TODO: custom exception
        raise ValueError('No room for resource extending')
