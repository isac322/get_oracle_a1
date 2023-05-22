# Macro to get Oracle Cloud A1.Flex instance

![Docker Pulls](https://img.shields.io/docker/pulls/isac322/get_oracle_a1?logo=docker&style=flat-square)
![Docker Image Size (tag)](https://img.shields.io/docker/image-size/isac322/get_oracle_a1/latest?logo=docker&style=flat-square)
![PyPI](https://img.shields.io/pypi/v/oci?label=oci&logo=python&style=flat-square)
![GitHub last commit (branch)](https://img.shields.io/github/last-commit/isac322/get_oracle_a1/master?logo=github&style=flat-square)
![GitHub Workflow Status (branch)](https://img.shields.io/github/actions/workflow/status/isac322/get_oracle_a1/ci.yaml?branch=master&logo=github&style=flat-square)
![Dependabpt Status](https://flat.badgen.net/github/dependabot/isac322/get_oracle_a1?icon=github)

Supported platform: `linux/amd64`, `linux/arm64/v8`, `linux/arm/v7`

## Overview

It will get or upgrade A1.Flex instance automatically.

You have to add Oracle API Key. please follow [Official Instruction](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm#Required_Keys_and_OCIDs)


## Tag format

`isac322/get_oracle_a1:<app_version>`

## Command

### `get_oracle_a1 --help`

```
usage: get_oracle_a1 [-h] {list_availability_domain,list_available_subnet,increase,create} ...

optional arguments:
  -h, --help            show this help message and exit

Sub Command:
  {list_availability_domain,list_available_subnet,increase,create}
```

### ` get_oracle_a1 create --help`

```
usage: get_oracle_a1 create [-h] [-p PROFILE] [-g API_CONFIG_FILE] [--verbose] [-a AVAILABILITY_DOMAIN] -n DISPLAY_NAME [-c TARGET_OCPU] [-m TARGET_MEMORY] [-s SUBNET_ID] [-o OS_NAME] [-v OS_VERSION] [-b BOOT_VOLUME_SIZE] [--ssh-authorized-keys SSH_AUTHORIZED_KEYS]

optional arguments:
  -h, --help            show this help message and exit
  -p PROFILE, --profile PROFILE
                        OCI API profile. (Default: DEFAULT)
  -g API_CONFIG_FILE, --api-config-file API_CONFIG_FILE
                        OCI API config path. (Default: ~/.oci/config)
  --verbose             increase output verbosity
  -a AVAILABILITY_DOMAIN, --availability-domain AVAILABILITY_DOMAIN
                        Availability Domain name. Run sub command `list_availability_domain` to get list
  -n DISPLAY_NAME, --display-name DISPLAY_NAME
  -c TARGET_OCPU, --ocpu TARGET_OCPU
  -m TARGET_MEMORY, --memory TARGET_MEMORY
  -s SUBNET_ID, --subnet-id SUBNET_ID
                        Subnet OCID. Run sub command `list_available_subnet` to get list
  -o OS_NAME, --os-name OS_NAME
  -v OS_VERSION, --os-version OS_VERSION
  -b BOOT_VOLUME_SIZE, --boot-volume-size BOOT_VOLUME_SIZE
                        Gigabyte
  --ssh-authorized-keys SSH_AUTHORIZED_KEYS

```

### `get_oracle_a1 increase --help`

```
usage: get_oracle_a1 increase [-h] [-p PROFILE] [-g API_CONFIG_FILE] [--verbose] -n DISPLAY_NAME [-c TARGET_OCPU] [-m TARGET_MEMORY] [-i]

optional arguments:
  -h, --help            show this help message and exit
  -p PROFILE, --profile PROFILE
                        OCI API profile. (Default: DEFAULT)
  -g API_CONFIG_FILE, --api-config-file API_CONFIG_FILE
                        OCI API config path. (Default: ~/.oci/config)
  --verbose             increase output verbosity
  -n DISPLAY_NAME, --display-name DISPLAY_NAME
  -c TARGET_OCPU, --ocpu TARGET_OCPU
  -m TARGET_MEMORY, --memory TARGET_MEMORY
  -i, --incremental     Acquire resources incrementally
```

## How to run

`docker run -v <your_oci_key_path>:/root/.oci:ro -ti isac322/get_oracle_a1 create --ocpu 4 --memory 24 -n instance1 --os-name "Canonical Ubuntu" --boot-volume-size 200`

It will keep retry to create A1.Flex with 4 OCPU, 24G Memory, 200GB boot volume with Ubuntu 20.04 using your API profile.

You can also upgrade spec existing instance with `increase` sub-command. Please reference `docker-compose.yml`
