import argparse
import logging
from pathlib import Path

import oci
from oci.config import validate_config

from get_oracle_a1 import commands, config, helpers, usecases


def main():
    oci_user, cmd = _bootstrap()

    if isinstance(cmd, commands.IncreaseResource):
        usecases.increase(cmd, oci_user)
    elif isinstance(cmd, commands.CreateA1):
        usecases.create(cmd, oci_user)
    elif isinstance(cmd, commands.ListAvailabilityDomain):
        usecases.list_availability_domain(cmd, oci_user)
    elif isinstance(cmd, commands.ListAvailableSubnet):
        usecases.list_available_subnet(cmd, oci_user)
    else:
        # TODO: custom exception
        raise ValueError(f'Unknown command: {cmd}')


def _cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub_cmd = parser.add_subparsers(title='Sub Command', dest='cmd', required=True)

    list_ad = sub_cmd.add_parser('list_availability_domain')
    _add_common_args(list_ad)
    list_as = sub_cmd.add_parser('list_available_subnet')
    _add_common_args(list_as)

    increase_cmd = sub_cmd.add_parser('increase')
    _add_common_args(increase_cmd)
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
    increase_cmd.add_argument(
        '-i',
        '--incremental',
        default=False,
        action='store_true',
        help='Acquire resources incrementally',
    )

    create_cmd = sub_cmd.add_parser('create')
    _add_common_args(create_cmd)
    create_cmd.add_argument(
        '-a',
        '--availability-domain',
        default=None,
        type=str,
        help='Availability Domain name. Run sub command `list_availability_domain` to get list',
    )
    create_cmd.add_argument(
        '-n',
        '--display-name',
        required=True,
        type=str,
    )
    create_cmd.add_argument(
        '-c',
        '--ocpu',
        dest='target_ocpu',
        default=None,
        type=int,
    )
    create_cmd.add_argument(
        '-m',
        '--memory',
        dest='target_memory',
        default=None,
        type=int,
    )
    create_cmd.add_argument(
        '-s',
        '--subnet-id',
        default=None,
        type=str,
        help='Subnet OCID. Run sub command `list_available_subnet` to get list',
    )
    create_cmd.add_argument(
        '-o',
        '--os-name',
        default='Oracle Linux',
        type=str,
    )
    create_cmd.add_argument(
        '-v',
        '--os-version',
        default=None,
        type=str,
    )
    create_cmd.add_argument(
        '-b',
        '--boot-volume-size',
        default=None,
        type=float,
        help='Gigabyte',
    )
    create_cmd.add_argument(
        '--ssh-authorized-keys',
        default=Path.home().joinpath('.ssh/authorized_keys'),
        type=str,
    )

    return parser.parse_args()


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '-p',
        '--profile',
        default=oci.config.DEFAULT_PROFILE,
        type=str,
        help=f'OCI API profile. (Default: {oci.config.DEFAULT_PROFILE})',
    )
    parser.add_argument(
        '-g',
        '--api-config-file',
        default=oci.config.DEFAULT_LOCATION,
        type=Path,
        help=f'OCI API config path. (Default: {oci.config.DEFAULT_LOCATION})',
    )
    parser.add_argument(
        '--verbose',
        help='increase output verbosity',
        action='store_true',
        default=False,
    )


def _parse_cmd(oci_user: config.OCIUser, params: argparse.Namespace) -> commands.Command:
    if params.cmd == 'increase':
        instance = helpers.find_target_instance(oci_user=oci_user, display_name=params.display_name)
        if instance is None:
            # TODO: custom exception
            raise RuntimeError(f'Failed to find target instance. display_name: {params.display_name}')

        params.instance_ocid = instance.id

        if params.target_ocpu is None or params.target_memory is None:
            resource_limit = helpers.get_a1_res_limit(oci_user, instance.availability_domain)
            if params.target_ocpu is None:
                params.target_ocpu = resource_limit.ocpu
            if params.target_memory is None:
                params.target_memory = resource_limit.memory

        return commands.IncreaseResource.from_orm(params)

    elif params.cmd == 'create':
        if params.availability_domain is None:
            availability_domains = helpers.list_availability_domain(oci_user)
            if len(availability_domains) == 0:
                # TODO: custom exception
                raise RuntimeError('Failed to find availability domain')
            params.availability_domain = availability_domains[0].name

        if params.subnet_id is None:
            subnets = tuple(helpers.list_available_subnet(oci_user))
            if len(subnets) == 0:
                # TODO: custom exception
                raise RuntimeError('Failed to find Subnet')
            params.subnet_id = subnets[0].id

        if params.target_ocpu is None or params.target_memory is None:
            shape = helpers.find_target_shape(
                oci_user=oci_user,
                shape=helpers.TARGET_SHAPE,
                availability_domain=params.availability_domain,
            )
            if shape is None:
                raise ValueError(f'Does not support shape {helpers.TARGET_SHAPE}')
            if params.target_ocpu is None:
                params.target_ocpu = shape.ocpu_options.min
            if params.target_memory is None:
                params.target_memory = shape.memory_options.default_per_ocpu_in_g_bs

        return commands.CreateA1.from_orm(params)

    elif params.cmd == 'list_availability_domain':
        return commands.ListAvailabilityDomain()

    elif params.cmd == 'list_available_subnet':
        return commands.ListAvailableSubnet()

    else:
        raise ValueError(f'Unknown command: {params.cmd}')


def _bootstrap() -> tuple[config.OCIUser, commands.Command]:
    logger = logging.getLogger(__name__)

    for h in logger.handlers:
        logger.removeHandler(h)
    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter(fmt='%(asctime)s [%(levelname)-8s] %(message)s', datefmt='%Y-%m-%dT%H:%M:%S%z')
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)

    params = _cli()

    cfg = oci.config.from_file(
        file_location=params.api_config_file,
        profile_name=params.profile,
    )
    validate_config(cfg)
    oci_user = config.OCIUser.parse_obj(cfg)
    validate_config(oci_user.config)
    cmd = _parse_cmd(oci_user=oci_user, params=params)

    if params.verbose:
        logger.setLevel(logging.INFO)

    return oci_user, cmd
