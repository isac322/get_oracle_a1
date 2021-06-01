import argparse
import logging
import os
from time import sleep

from oci.config import validate_config
from oci.exceptions import ServiceError

from get_oracle_a1 import commands, config, usecases

logger = logging.getLogger(__name__)
RETRY_SEC = 120
LOG_TERM = 10_000


def main():
    oci_user, cmd = _bootstrap()

    if isinstance(cmd, commands.IncreaseResource):
        increase(cmd, oci_user)
    else:
        # TODO: custom exception
        raise ValueError(f'Unknown command: {cmd}')

    # compute_client = ComputeClient(config=oci_user.config)
    # for shape in compute_client.list_shapes(oci_user.compartment_id).data:
    #     print(shape)
    # instance: Instance
    # for instance in compute_client.list_instances(oci_user.compartment_id).data:
    #     if instance.lifecycle_state in (Instance.LIFECYCLE_STATE_TERMINATED, Instance.LIFECYCLE_STATE_TERMINATING):
    #         continue
    #     print(instance)


def increase(cmd: commands.IncreaseResource, oci_user: config.OCIUser) -> None:
    def get_instance():
        _ins = usecases.find_target_instance(oci_user=oci_user, display_name=cmd.display_name)
        if _ins is None:
            # TODO: custom exception
            raise RuntimeError('Failed to fetch instance')
        return _ins

    instance = get_instance()
    resource_limit = usecases.get_res_limit(oci_user, instance.availability_domain)
    while (
        instance.shape_config.ocpus < resource_limit.ocpu or instance.shape_config.memory_in_gbs < resource_limit.memory
    ):
        instance = get_instance()
        step = usecases.calc_next_increase_step(instance=instance, resource_limit=resource_limit)
        logger.info(f'New Increasing Step: {step}', extra=dict(step=step))

        succeed = False
        try_count = 0
        while not succeed:
            try:
                usecases.increase_resource(oci_user=oci_user, instance=instance, step=step)
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


def _cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub_cmd = parser.add_subparsers(title='Sub Command', dest='cmd', required=True)

    increase_cmd = sub_cmd.add_parser('increase')
    increase_cmd.add_argument(
        '-n',
        '--display-name',
        required=True,
        type=str,
    )
    increase_cmd.add_argument(
        '-c',
        '--ocpu',
        dest='target_ocpu',
        default=None,
        type=int,
    )
    increase_cmd.add_argument(
        '-m',
        '--memory',
        dest='target_memory',
        default=None,
        type=int,
    )

    return parser.parse_args()


def _parse_cmd(oci_user: config.OCIUser, params: argparse.Namespace) -> commands.Command:
    if params.cmd == 'increase':
        instance = usecases.find_target_instance(oci_user=oci_user, display_name=params.display_name)
        if instance is None:
            # TODO: custom exception
            raise RuntimeError(f'Failed to find target instance. display_name: {params.display_name}')

        if params.target_ocpu is None or params.target_memory is None:
            resource_limit = usecases.get_res_limit(oci_user, instance.availability_domain)
            params.target_ocpu = resource_limit.ocpu
            params.target_memory = resource_limit.memory

        return commands.IncreaseResource.from_orm(params)


def _bootstrap() -> tuple[config.OCIUser, commands.Command]:
    if os.getenv('DEBUG', False):
        from dotenv import load_dotenv

        load_dotenv(override=True)
        logger.setLevel(logging.DEBUG)

    oci_user = config.OCIUser()
    validate_config(oci_user.config)

    for h in logger.handlers:
        logger.removeHandler(h)
    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter(fmt='%(asctime)s [%(levelname)-8s] %(message)s', datefmt='%Y-%m-%dT%H:%M:%S%z')
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)

    params = _cli()
    cmd = _parse_cmd(oci_user=oci_user, params=params)

    return oci_user, cmd
