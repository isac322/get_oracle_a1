import logging
from time import sleep

from oci.exceptions import ServiceError

from get_oracle_a1 import commands, config, helpers

logger = logging.getLogger(__name__)
RETRY_SEC = 120
LOG_TERM = 10_000


def increase(cmd: commands.IncreaseResource, oci_user: config.OCIUser) -> None:
    def get_instance():
        _ins = helpers.find_target_instance(oci_user=oci_user, display_name=cmd.display_name)
        if _ins is None:
            # TODO: custom exception
            raise RuntimeError('Failed to fetch instance')
        return _ins

    instance = get_instance()
    resource_limit = helpers.get_res_limit(oci_user, instance.availability_domain)
    while (
        instance.shape_config.ocpus < resource_limit.ocpu or instance.shape_config.memory_in_gbs < resource_limit.memory
    ):
        instance = get_instance()
        step = helpers.calc_next_increase_step(instance=instance, resource_limit=resource_limit)
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
