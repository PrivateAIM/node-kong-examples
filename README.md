# Kong Example

This repository provides a set of examples for using Kong as an API gateway, to make the available data stores (e.g., FHIR, S3) in a DIC available to Flame projects and analyses. It uses [kong-admin-python-client](https://github.com/PrivateAIM/kong-admin-python-client) to interact with Kong's Admin API.

## Prerequisites

[Poetry](https://python-poetry.org/) must be installed and an instance of Kong must be running. A way to start Kong is to use the [Kong Setup](https://github.com/PrivateAIM/node-keycloak-autosetup) repository.


## Installation

Clone this repository.
In a terminal, navigate to the repository's root directory.
Run `poetry install`.


## Usage

Run `poetry shell`.
You can then run `kadmin --help` to view the tool's options.

```bash
$ kadmin --help
Usage: kadmin [OPTIONS] COMMAND [ARGS]...

Options:
  --kong-admin-url TEXT  URL to Kong Admin API
  --help                 Show this message and exit.

Commands:
  connect-project-to-datastore   Connect a project to a data store.
  disconnect-project             Disconnect a project from all connected...
  list-data-stores               List all data stores registered with Kong.
  list-project-data-stores       List all data stores connected to a...
  register-analysis-for-project  Register an analysis for a project and...
  register-data-store            Register a data store with Kong.
```

## Examples

- Register a FHIR data store with Kong

The following command registers a FHIR data store with Kong, using the specified protocol, host, port, path and tag. The command returns the ID of the registered data store. Note that here the tag is used to identify the data store type in the Kong Admin API. Plus, registering a data store with Kong does not make it routable.
```bash
$ kadmin --kong-admin-url http://localhost:8001 register-data-store https server.fire.ly 443 fhir
data_store_id=$(kadmin --kong-admin-url http://localhost:8001 register-data-store https server.fire.ly 443 fhir | grep "Data store registered with Kong, id:" | awk '{print $NF}')
```

- Connect `project1` to the registered data store.

This makes the data store routable under `{KONG_GATEWAY}/project1/fhir` and configures the necessary plugins like ACL and key authentication. This means that only analyses (consumers) registered with `project1` as  group and valid API key can access the data store.
```bash
$ kadmin --kong-admin-url http://localhost:8001 connect-project-to-datastore $data_store_id project1 fhir http GET
Project connected to data store, id: 4884a465-b909-454d-a222-fb6dcf336798
Key authentication plugin added, id: 611873a0-38ff-4732-b0ec-2db3f109bdf1
ACL plugin added, id: 1e1e3b35-e0e8-4ac4-990c-81d7cf7daf78
```

- Register an analysis as a consumer for `project1`.

This provides the analysis with an API key and configures the group with ACL plugin.
```bash
$ kadmin --kong-admin-url http://localhost:8001 register-analysis-for-project project1 analysis1-1
Consumer added, id: e67a6653-f3ff-42ec-ace6-fbd43ab9930d
ACL plugin configured for consumer, group: project1
Key authentication plugin configured for consumer, api_key: ilppDVkDFTOJTcnydLbR3EshNuN6wObL
```
