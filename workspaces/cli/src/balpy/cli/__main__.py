import logging

import asyncclick as click
from balpy.chains import Chain
from balpy.cli.helpers import (
    contract_function_autocompletion,
    create_contract_from_context,
    display_contract_info,
    network_autocompletion,
    vault_function_autocompletion,
)
from balpy.contracts import BalancerContractFactory


# Main group
@click.group()
@click.option(
    "--network",
    type=click.Choice([x.name for x in Chain], case_sensitive=False),
    help="Specify the network for the contract.",
    shell_complete=network_autocompletion,
)
@click.option(
    "-v", "--verbose", count=True, help="Increase verbosity (e.g., -v or -vv)."
)
@click.pass_context
def balpy(ctx, network, verbose):
    """Main entry point for the balpy command line tool."""
    log_level = max(logging.WARNING - 10 * verbose, logging.DEBUG)
    logging.basicConfig(level=log_level)
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["network"] = Chain[network] if network else Chain.mainnet


@balpy.group("vault")
@click.pass_context
def vault(ctx):
    """Commands related to the Vault."""
    ctx.obj["contract_identifier"] = "Vault"


@balpy.group("contract")
@click.argument("identifier")
@click.pass_context
def contract(ctx, identifier):
    """Commands related to a specific contract."""
    ctx.obj["contract_identifier"] = identifier


@vault.command(name="info")
@click.pass_context
def vault_info(ctx):
    """Display details of the Vault."""
    display_contract_info(ctx)


@contract.command(name="info")
@click.pass_context
def contract_info(ctx):
    """Display details of the contract."""
    display_contract_info(ctx)


@vault.command("fn")
@click.argument(
    "function_name", required=False, shell_complete=vault_function_autocompletion
)
@click.argument("args", nargs=-1)
@click.pass_context
async def vault_fn(ctx, function_name, args):
    """Execute a function on the Vault contract."""
    network = ctx.obj["network"]
    chain = Chain.mainnet if network == "mainnet" else Chain.polygon
    vault = BalancerContractFactory.create(chain, "Vault")

    if hasattr(vault, function_name) and callable(
        func := getattr(vault, function_name)
    ):
        result = await func(*args)

        click.echo(click.style(f"Result of {function_name}:", fg="cyan"))
        click.echo(click.style(f"  {result}", fg="white"))
    else:
        click.echo(click.style("No valid function name provided.", fg="red"))


@contract.command("fn")
@click.argument("function_name", shell_complete=contract_function_autocompletion)
@click.argument("args", nargs=-1)
@click.pass_context
async def contract_fn(ctx, function_name, args):
    logging.debug("Entering fn command")

    contract = create_contract_from_context(ctx)

    try:
        function = getattr(contract, function_name)
        result = await function(*args)
        click.echo(click.style(f"Result: {result}", fg="green"))
    except AttributeError:
        click.echo(click.style(f"Function '{function_name}' not found.", fg="red"))
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))


def main():
    balpy(_anyio_backend="asyncio")


if __name__ == "__main__":
    main()
