import click
from click import Context

import kong_admin_client
from kong_admin_client.models.create_service_request import CreateServiceRequest
from kong_admin_client.models.create_route_request import CreateRouteRequest
from kong_admin_client.models.create_consumer_request import CreateConsumerRequest
from kong_admin_client.models.create_plugin_for_consumer_request import (
    CreatePluginForConsumerRequest,
)
from kong_admin_client.models.create_acl_for_consumer_request import (
    CreateAclForConsumerRequest,
)
from kong_admin_client.models.create_key_auth_for_consumer_request import (
    CreateKeyAuthForConsumerRequest,
)
from kong_admin_client.rest import ApiException


@click.group()
@click.option(
    "--kong-admin-url",
    default="http://localhost:8001",
    help="URL to Kong Admin API",
)
@click.pass_context
def cli(ctx: Context, kong_admin_url: str):
    ctx.ensure_object(dict)
    ctx.obj["kong_admin_url"] = kong_admin_url


@cli.command()
@click.pass_context
def list_data_stores(ctx: Context):
    """List all data stores registered with Kong."""
    kong_admin_url = ctx.obj["kong_admin_url"]
    configuration = kong_admin_client.Configuration(host=kong_admin_url)

    try:
        with kong_admin_client.ApiClient(configuration) as api_client:
            api_instance = kong_admin_client.ServicesApi(api_client)
            api_response = api_instance.list_service()
            for service in api_response.data:
                click.echo(
                    f"Data store id: {service.id}, host: {service.host}, port: {service.port}, path: {service.path}"
                )
            if len(api_response.data) == 0:
                click.echo("No data stores registered with Kong.")
    except ApiException as e:
        print(f"Exception when calling ServicesApi->list_services: {e}\n")
    except Exception as e:
        print(f"Exception: {e}\n")


@cli.command()
@click.argument(
    "protocol", metavar="PROTOCOL", type=click.Choice(["http", "https"]), required=True
)
@click.argument("host", metavar="HOST", required=True)
@click.argument("port", metavar="PORT", type=int, required=True)
@click.argument(
    "type", metavar="TYPE", type=click.Choice(["fhir", "s3"]), required=True
)
@click.argument("path", metavar="PATH", required=False)
@click.pass_context
def register_data_store(
    ctx: Context, protocol: str, host: str, port: int, path: str, type: str
):
    """Register a data store with Kong.

    PROTOCOL: The protocol to use for the upstream server. One of http or https.

    HOST: The host of the upstream server.

    PORT: The upstream server port.

    PATH: The path to be used in requests to the upstream server, should start with a leading slash.

    TYPE: The type of the data store. One of fhir or s3.
    """
    kong_admin_url = ctx.obj["kong_admin_url"]
    configuration = kong_admin_client.Configuration(host=kong_admin_url)

    try:
        with kong_admin_client.ApiClient(configuration) as api_client:
            api_instance = kong_admin_client.ServicesApi(api_client)
            create_service_request = CreateServiceRequest(
                host=host,
                path=path,
                port=port,
                protocol=protocol,
                enabled=True,
                tls_verify=None,
                tags=[type],
            )
            api_response = api_instance.create_service(create_service_request)
            click.echo(f"Data store registered with Kong, id: {api_response.id}")
    except ApiException as e:
        print(f"Exception when calling ServicesApi->create_service: {e}\n")
    except Exception as e:
        print(f"Exception: {e}\n")


@cli.command()
@click.argument("data_store_id", metavar="DATA_STORE_ID", required=True)
@click.argument("project_id", metavar="PROJECT_ID", required=True)
@click.argument(
    "type", metavar="TYPE", type=click.Choice(["fhir", "s3"]), required=True
)
@click.argument("protocols", metavar="PROTOCOL(S)", type=str, required=True)
@click.argument("methods", metavar="METHOD(S)", type=str, required=True)
@click.pass_context
def connect_project_to_datastore(
    ctx: Context,
    data_store_id: str,
    protocols: str,
    methods: str,
    project_id: str,
    type: str,
):
    """Connect a project to a data store.

    DATA_STORE_ID: The id of the data store to connect to.

    PROJECT_ID: The id of the project to connect.

    TYPE: The type of the data store. One of fhir or s3.

    PROTOCOLS: The protocols to use for the route. One of http or https.

    METHODS: The HTTP methods that match this route. For example: GET, POST.
    """
    kong_admin_url = ctx.obj["kong_admin_url"]
    configuration = kong_admin_client.Configuration(host=kong_admin_url)

    # Construct path from project_id and type
    path = "/" + project_id + "/" + type

    # Split protocols and methods into lists
    protocols_list = protocols.split(",")
    methods_list = methods.split(",")

    # Add route
    try:
        with kong_admin_client.ApiClient(configuration) as api_client:
            api_instance = kong_admin_client.RoutesApi(api_client)
            create_route_request = CreateRouteRequest(
                name=project_id,
                protocols=protocols_list,
                methods=methods_list,
                paths=[path],
                https_redirect_status_code=426,
                preserve_host=False,
                request_buffering=True,
                response_buffering=True,
                tags=[project_id, type],
            )
            api_response = api_instance.create_route_for_service(
                data_store_id, create_route_request
            )
            click.echo(f"Project connected to data store, id: {api_response.id}")
            route_id = api_response.id
    except ApiException as e:
        print(f"Exception when calling RoutesApi->create_route_for_service: {e}\n")
    except Exception as e:
        print(f"Exception: {e}\n")

    # Add key-auth plugin
    try:
        with kong_admin_client.ApiClient(configuration) as api_client:
            api_instance = kong_admin_client.PluginsApi(api_client)
            create_route_request = CreatePluginForConsumerRequest(
                name="key-auth",
                instance_name=f"{project_id}-keyauth",
                config={
                    "hide_credentials": True,
                    "key_in_body": False,
                    "key_in_header": True,
                    "key_in_query": False,
                    "key_names": ["apikey"],
                    "run_on_preflight": True,
                },
                enabled=True,
                protocols=protocols_list,
            )
            api_response = api_instance.create_plugin_for_route(
                route_id, create_route_request
            )
            click.echo(f"Key authentication plugin added, id: {api_response.id}")
    except ApiException as e:
        print(f"Exception when calling PluginsApi->create_plugin_for_route: {e}\n")
    except Exception as e:
        print(f"Exception: {e}\n")

    # Add acl plugin
    try:
        with kong_admin_client.ApiClient(configuration) as api_client:
            api_instance = kong_admin_client.PluginsApi(api_client)
            create_route_request = CreatePluginForConsumerRequest(
                name="acl",
                instance_name=f"{project_id}-acl",
                config={"allow": [project_id], "hide_groups_header": True},
                enabled=True,
                protocols=protocols_list,
            )
            api_response = api_instance.create_plugin_for_route(
                route_id, create_route_request
            )
            click.echo(f"ACL plugin added, id: {api_response.id}")
    except ApiException as e:
        print(f"Exception when calling PluginsApi->create_plugin_for_route: {e}\n")
    except Exception as e:
        print(f"Exception: {e}\n")


@cli.command()
@click.argument("project_id", metavar="PROJECT_ID", required=True)
@click.pass_context
def list_project_data_stores(ctx: Context, project_id: str):
    """List all data stores connected to a project.

    PROJECT_ID: The id of the project to list data stores for.
    """
    kong_admin_url = ctx.obj["kong_admin_url"]
    configuration = kong_admin_client.Configuration(host=kong_admin_url)

    try:
        with kong_admin_client.ApiClient(configuration) as api_client:
            api_instance = kong_admin_client.RoutesApi(api_client)
            api_response = api_instance.list_route(tags=project_id)
            for route in api_response.data:
                click.echo(f"project connected to data store id: {route.service.id}")
            if len(api_response.data) == 0:
                click.echo("No data stores connected to project.")
    except ApiException as e:
        print(f"Exception when calling RoutesApi->list_routes_for_service: {e}\n")
    except Exception as e:
        print(f"Exception: {e}\n")


@cli.command()
@click.argument("project_id", metavar="PROJECT_ID", required=True)
@click.pass_context
def disconnect_project(ctx: Context, project_id: str):
    """Disconnect a project from all connected data stores.

    PROJECT_ID: The id of the project to disconnect.
    """
    kong_admin_url = ctx.obj["kong_admin_url"]
    configuration = kong_admin_client.Configuration(host=kong_admin_url)

    try:
        with kong_admin_client.ApiClient(configuration) as api_client:
            api_instance = kong_admin_client.RoutesApi(api_client)
            api_response = api_instance.list_route(tags=project_id)
            for route in api_response.data:
                # Delete route
                try:
                    api_instance = kong_admin_client.RoutesApi(api_client)
                    api_instance.delete_route(route.id)
                    click.echo(
                        f"Project disconnected from data store, id: {route.service.id}"
                    )
                except ApiException as e:
                    print(f"Exception when calling RoutesApi->delete_route: {e}\n")
                except Exception as e:
                    print(f"Exception: {e}\n")
    except ApiException as e:
        print(f"Exception when calling RoutesApi->list_routes_for_service: {e}\n")
    except Exception as e:
        print(f"Exception: {e}\n")


@cli.command()
@click.argument("project_id", metavar="PROJECT_ID", required=True)
@click.argument("analysis_id", metavar="ANALYSIS_ID", required=True)
@click.pass_context
def register_analysis_for_project(ctx: Context, project_id: str, analysis_id: str):
    """Register an analysis for a project and configure key-auth and acl plugins. It returns api_key for the analysis.

    PROJECT_ID: The id of the project to register the analysis for.

    ANALYSIS_ID: The id of the analysis to register.
    """
    kong_admin_url = ctx.obj["kong_admin_url"]
    configuration = kong_admin_client.Configuration(host=kong_admin_url)

    # Add consumer
    try:
        with kong_admin_client.ApiClient(configuration) as api_client:
            api_instance = kong_admin_client.ConsumersApi(api_client)
            api_response = api_instance.create_consumer(
                CreateConsumerRequest(
                    username=analysis_id,
                    custom_id=analysis_id,
                    tags=[project_id],
                )
            )
            click.echo(f"Consumer added, id: {api_response.id}")
            consumer_id = api_response.id
    except ApiException as e:
        print(f"Exception when calling ConsumersApi->create_consumer: {e}\n")
    except Exception as e:
        print(f"Exception: {e}\n")

    # Configure acl plugin for consumer
    try:
        with kong_admin_client.ApiClient(configuration) as api_client:
            api_instance = kong_admin_client.ACLsApi(api_client)
            api_response = api_instance.create_acl_for_consumer(
                consumer_id,
                CreateAclForConsumerRequest(
                    group=project_id,
                    tags=[project_id],
                ),
            )
            click.echo(
                f"ACL plugin configured for consumer, group: {api_response.group}"
            )
    except ApiException as e:
        print(f"Exception when calling ACLsApi->create_acl_for_consumer: {e}\n")
    except Exception as e:
        print(f"Exception: {e}\n")

    # Configure key-auth plugin for consumer
    try:
        with kong_admin_client.ApiClient(configuration) as api_client:
            api_instance = kong_admin_client.KeyAuthsApi(api_client)
            api_response = api_instance.create_key_auth_for_consumer(
                consumer_id,
                CreateKeyAuthForConsumerRequest(
                    tags=[project_id],
                ),
            )
            click.echo(
                f"Key authentication plugin configured for consumer, api_key: {api_response.key}"
            )
    except ApiException as e:
        print(
            f"Exception when calling KeyAuthsApi->create_key_auth_for_consumer: {e}\n"
        )
    except Exception as e:
        print(f"Exception: {e}\n")


if __name__ == "__main__":
    cli(obj={})
