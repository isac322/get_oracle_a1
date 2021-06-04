from collections import Iterable, Sequence
from functools import cache
from pathlib import Path
from typing import Optional

from oci.core import ComputeClient, VirtualNetworkClient
from oci.core.models import (
    CreateVnicDetails,
    Image,
    Instance,
    InstanceSourceViaImageDetails,
    LaunchInstanceDetails,
    LaunchInstanceShapeConfigDetails,
    Shape,
    Subnet,
    UpdateInstanceDetails,
    UpdateInstanceShapeConfigDetails,
)
from oci.identity import IdentityClient
from oci.identity.models import AvailabilityDomain
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


@cache
def list_availability_domain(oci_user: OCIUser) -> Sequence[AvailabilityDomain]:
    client = IdentityClient(oci_user.config)
    return client.list_availability_domains(oci_user.compartment_id).data


@cache
def get_a1_res_limit(oci_user: OCIUser, availability_domain: str) -> ResourceLimit:
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


@cache
def check_a1_available(oci_user: OCIUser, availability_domain: str) -> bool:
    return find_target_shape(oci_user=oci_user, shape=TARGET_SHAPE, availability_domain=availability_domain) is not None


@cache
def find_target_shape(oci_user: OCIUser, shape: str, availability_domain: str) -> Optional[Shape]:
    client = ComputeClient(config=oci_user.config)
    s: Shape
    for s in client.list_shapes(oci_user.compartment_id, availability_domain=availability_domain).data:
        if s.shape == shape:
            return s
    return None


def calc_next_increase_step(
    oci_user: OCIUser, instance: Instance, target_ocpu: int, target_memory: int
) -> IncreaseStep:
    shape = find_target_shape(oci_user=oci_user, shape=TARGET_SHAPE, availability_domain=instance.availability_domain)
    if shape is None:
        # TODO: custom exception
        raise RuntimeError(f'Failed to find shape {TARGET_SHAPE}')

    base_ocpu_step = shape.ocpu_options.min
    base_memory_step = shape.memory_options.default_per_ocpu_in_g_bs * base_ocpu_step

    resource_limit = get_a1_res_limit(oci_user, instance.availability_domain)

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


def get_image(oci_user: OCIUser, os_name: str, os_version: Optional[str]) -> Optional[Image]:
    client = ComputeClient(config=oci_user.config)
    images: Sequence[Image] = sorted(
        client.list_images(
            oci_user.compartment_id,
            shape=TARGET_SHAPE,
            operating_system=os_name,
            operating_system_version=os_version,
        ).data,
        key=lambda i: i.operating_system_version,
        reverse=True,
    )
    if len(images) == 0:
        return None
    else:
        return images[0]


def create_a1(
    oci_user: OCIUser,
    availability_domain: str,
    target_ocpu: int,
    target_memory: int,
    image: Image,
    display_name: str,
    subnet_id: str,
    boot_volume_size: Optional[float],
    ssh_authorized_keys: Path,
) -> Instance:
    client = ComputeClient(config=oci_user.config)
    return client.launch_instance(
        LaunchInstanceDetails(
            display_name=display_name,
            compartment_id=oci_user.compartment_id,
            shape=TARGET_SHAPE,
            shape_config=LaunchInstanceShapeConfigDetails(
                ocpus=target_ocpu,
                memory_in_gbs=target_memory,
            ),
            availability_domain=availability_domain,
            create_vnic_details=CreateVnicDetails(
                subnet_id=subnet_id,
                hostname_label=display_name,
            ),
            source_details=InstanceSourceViaImageDetails(
                image_id=image.id,
                boot_volume_size_in_gbs=boot_volume_size,
            ),
            metadata=dict(
                ssh_authorized_keys=ssh_authorized_keys.read_text(),
            ),
            is_pv_encryption_in_transit_enabled=True,
            # launch_options=LaunchOptions(
            #     boot_volume_type=LaunchOptions.BOOT_VOLUME_TYPE_ISCSI,
            #     network_type=LaunchOptions.NETWORK_TYPE_VFIO,
            # ),
        )
    ).data


def list_available_subnet(oci_user: OCIUser) -> Iterable[Subnet]:
    client = VirtualNetworkClient(oci_user.config)
    subnet: Subnet
    for subnet in client.list_subnets(oci_user.compartment_id).data:
        if subnet.lifecycle_state == Subnet.LIFECYCLE_STATE_AVAILABLE:
            yield subnet
