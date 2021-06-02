import logging
from time import sleep

from oci.exceptions import ServiceError

from get_oracle_a1 import commands, config, helpers

logger = logging.getLogger(__name__)
RETRY_SEC = 120
LOG_TERM = 10_000


def increase(cmd: commands.IncreaseResource, oci_user: config.OCIUser) -> None:
    while True:
        instance = helpers.get_instance(oci_user=oci_user, ocid=cmd.instance_ocid)
        if instance.shape_config.ocpus >= cmd.target_ocpu and instance.shape_config.memory_in_gbs >= cmd.target_memory:
            break

        step = helpers.calc_next_increase_step(
            oci_user=oci_user,
            instance=instance,
            target_ocpu=cmd.target_ocpu,
            target_memory=cmd.target_memory,
        )
        logger.info(f'New Increasing Step: {step}')

        succeed = False
        try_count = 0
        while not succeed:
            try:
                helpers.increase_resource(oci_user=oci_user, instance=instance, step=step)
            except ServiceError as e:
                if e.status != 500 or e.code != 'InternalError' or e.message != 'Out of host capacity.':
                    logger.exception('Unsupported exception happened')
                    break
            else:
                succeed = True
            finally:
                try_count += 1

            if try_count % LOG_TERM == 0:
                logger.info(f'Tried {try_count}. Keep trying...')

        if succeed:
            logger.info(f'Increasing succeed in {try_count} tries.')
        else:
            logger.error(f'Failed to increase after {try_count} tries. Retry after {RETRY_SEC} seconds')
        sleep(RETRY_SEC)


def create(cmd: commands.CreateA1, oci_user: config.OCIUser) -> None:
    if not helpers.check_a1_available(oci_user, cmd.availability_domain):
        raise RuntimeError('Does not support A1.Flex')

    image = helpers.get_image(oci_user=oci_user, os_name=cmd.os_name, os_version=cmd.os_version)
    if image is None:
        raise RuntimeError(f'Failed to find image {cmd.os_name}-{cmd.os_version}')

    logger.info(f'Try to create {cmd}')

    try_count = 0
    while True:
        try:
            instance = helpers.create_a1(
                oci_user=oci_user,
                availability_domain=cmd.availability_domain,
                target_ocpu=cmd.target_ocpu,
                target_memory=cmd.target_memory,
                image=image,
                display_name=cmd.display_name,
                subnet_id=cmd.subnet_id,
            )
        except ServiceError as e:
            if e.status != 500 or e.code != 'InternalError' or e.message != 'Out of host capacity.':
                logger.exception(f'Failed to create instance with unknown reason. ({try_count} times tried)')
                raise e
        else:
            logger.info(f'Succeed to create in {try_count} tries.')
            logger.info(instance)
            break
        finally:
            try_count += 1


def list_availability_domain(_: commands.ListAvailabilityDomain, oci_user: config.OCIUser) -> None:
    for domain in helpers.list_availability_domain(oci_user):
        print(domain.name)


def list_available_subnet(_: commands.ListAvailableSubnet, oci_user: config.OCIUser) -> None:
    for subnet in helpers.list_available_subnet(oci_user):
        print(subnet)
