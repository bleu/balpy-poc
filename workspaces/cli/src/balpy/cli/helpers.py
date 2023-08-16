import logging

import asyncclick as click
from balpy.chains import Chain
from balpy.contracts.base_contract import BalancerContractFactory

# ----------------------- Autocompletion Functions -----------------------


def network_autocompletion(ctx, args, incomplete):
    """Provide autocompletion for network names."""
    networks = ["mainnet", "polygon"]
    return [n for n in networks if n.startswith(incomplete)]


def _fetch_contract_functions(chain, contract_id):
    """Fetch the list of function names for a given contract."""
    contract = BalancerContractFactory.create(chain, contract_id)
    functions = [
        f["name"] for f in contract.web3_contract.abi if f["type"] == "function"
    ]
    return functions


def vault_function_autocompletion(ctx, args, incomplete):
    """Provide autocompletion for vault functions."""
    chain = resolve_chain_from_args(args)
    functions = _fetch_contract_functions(chain, "Vault")
    return [fn for fn in functions if fn.startswith(incomplete)]


def contract_function_autocompletion(ctx, args, incomplete):
    """Provide autocompletion for contract functions based on the contract address."""
    chain = resolve_chain_from_args(args)

    contract_address_key = "contract"
    contract_address_index = (
        args.index(contract_address_key) + 1 if contract_address_key in args else None
    )
    contract_address = args[contract_address_index] if contract_address_index else None

    if not contract_address:
        return []

    functions = _fetch_contract_functions(chain, contract_address)
    return [fn for fn in functions if fn.startswith(incomplete)]


# ----------------------- Contract Details Printing Functions -----------------------


def echo_argument(argument):
    """Print the argument details."""
    template = (
        "      - Type: {type}"
        if not argument.get("name")
        else "      - Name: {name}, Type: {type}"
    )
    click.echo(click.style(template.format(**argument), fg="white"))


def print_function_info(function):
    """Print the details of a contract function."""
    click.echo(click.style("  - Function name:", fg="cyan") + f" {function['name']}")

    # Input arguments
    if function.get("inputs"):
        click.echo(click.style("    - Input arguments:", fg="magenta"))
        for input_arg in function["inputs"]:
            echo_argument(input_arg)

    # Output arguments
    if function.get("outputs"):
        click.echo(click.style("    - Output arguments:", fg="magenta"))
        for output_arg in function["outputs"]:
            echo_argument(output_arg)

    click.echo()


def get_read_and_write_functions(contract):
    """Separate contract functions into read and write based on their state mutability."""
    read_functions = [
        f
        for f in contract.web3_contract.abi
        if f["type"] == "function" and f.get("stateMutability") == "view"
    ]
    write_functions = [
        f
        for f in contract.web3_contract.abi
        if f["type"] == "function" and f.get("stateMutability") != "view"
    ]
    return read_functions, write_functions


def print_contract_details(contract):
    """Print the detailed structure and functions of a contract."""
    title = contract.__class__.__name__
    click.echo(click.style(f"{title}:", fg="green"))

    read_functions, write_functions = get_read_and_write_functions(contract)

    click.echo(click.style("Read functions:", fg="cyan"))
    for function in read_functions:
        print_function_info(function)

    click.echo(click.style("Write functions:", fg="cyan"))
    for function in write_functions:
        print_function_info(function)


# ----------------------- Chain Resolution and Contract Creation Functions -----------------------


def resolve_chain_from_network(network):
    """Get the chain type based on the network name."""
    return Chain.polygon if network == "polygon" else Chain.mainnet


def resolve_chain_from_args(args):
    """Resolve the chain from command arguments."""
    return Chain.polygon if "polygon" in args else Chain.mainnet


def get_chain_from_context(ctx):
    """Get the chain type from the current context."""
    network = ctx.obj["network"]
    return resolve_chain_from_network(network)


def create_contract_from_context(ctx):
    """Create a contract instance from the current context."""
    chain = get_chain_from_context(ctx)
    return BalancerContractFactory.create(chain, ctx.obj["contract_identifier"])


def display_contract_info(ctx):
    """Display the contract details based on the current context."""
    if ctx.obj["verbose"] > 0:
        logging.info("Entering info command")
    contract = create_contract_from_context(ctx)
    print_contract_details(contract)
