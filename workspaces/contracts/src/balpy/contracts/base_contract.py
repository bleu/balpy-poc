import jsondiff as jd
from balpy.chains import Chain
from balpy.contracts.contract_loader import (
    ContractLoader,
    get_name_and_abi_from_etherscan,
    load_abi_from_address,
    load_all_deployments_artifacts,
    load_deployment_addresses,
)
from balpy.core.cache import memory
from jsondiff import diff as jsondiff


def get_contract_address(contract_name, chain: Chain):
    address_book = load_deployment_addresses(chain)

    return next(
        contract["address"]
        for _, v in address_book.items()
        for contract in v.get("contracts", [])
        if contract["name"].casefold() == contract_name.casefold()
    )


class BaseContract:
    """
    A base class for Balancer contracts that implements common functionality.

    This class uses a singleton pattern to ensure that there's only one instance
    of the contract for each contract address and chain combination.

    :ivar _instances: A dictionary to store instances of the BaseContract class.
    """

    ABI_FILE_NAME = None
    ABI = None
    _instances = {}

    # def __new__(cls, contract_address, chain: Chain):
    #     key = (cls, contract_address, chain)
    #     if key not in cls._instances:
    #         cls._instances[key] = super().__new__(cls)
    #     return cls._instances[key]

    def __init__(self, contract_address, chain: Chain, abi_file_name=None, abi=None):
        """
        Initializes the BaseContract with a contract address, chain, and optionally an ABI file name.

        :param contract_address: The address of the contract on the specified chain
        :param chain: The chain the contract is deployed on
        :param abi_file_name: The ABI file name of the contract, optional
        :param abi: The ABI of the contract, optional
        """
        if not "_initialized" in self.__dict__:
            self.contract_loader = ContractLoader(chain)
            self.web3_contract = self.contract_loader.get_web3_contract(
                contract_address, abi_file_name, abi
            )
            self._initialized = True

    @property
    def contract_address(self):
        return self.web3_contract.address

    def _function_exists_in_abi(self, function_name):
        """
        Checks if a function exists in the ABI of the contract.

        :param function_name: The name of the function to check for
        :return: True if the function exists, False otherwise
        """
        for item in self.web3_contract.abi:
            if item.get("type") == "function" and item.get("name") == function_name:
                return True
        return False

    def _event_exists_in_abi(self, event_name):
        """
        Checks if an event exists in the ABI of the contract.

        :param event_name: The name of the event to check for
        :return: True if the event exists, False otherwise
        """
        for item in self.web3_contract.abi:
            if item.get("type") == "event" and item.get("name") == event_name:
                return True
        return False

    def __getattr__(self, name):
        """
        Makes contract functions directly accessible as attributes of the BaseContract.

        :param name: The name of the attribute being accessed
        :return: The wrapped contract function if it exists, raises AttributeError otherwise
        """
        if getattr(self.web3_contract, name, None):
            return getattr(self.web3_contract, name)

        if self._event_exists_in_abi(name):
            # TODO: ability to get event signature hash
            function = getattr(self.web3_contract.events, name)

        if self._function_exists_in_abi(name):
            function = getattr(self.web3_contract.functions, name)

            def wrapped_call(*args, **kwargs):
                return function(*args, **kwargs).call()

            return wrapped_call

        raise AttributeError(f"{self.__class__.__name__} has no attribute {name}")


class BalancerContractFactory:
    _contract_classes = {}

    @classmethod
    def get_contract_class(cls, contract_name, chain: Chain, abi=None):
        """
        Retrieves the contract class for a given contract name and chain, creating it if it doesn't exist.

        :param contract_name: The name of the contract
        :param chain: The chain the contract is deployed on
        :return: The contract class for the given contract name and chain
        """
        key = (contract_name, chain)
        if key not in cls._contract_classes:
            if abi is None:
                contract_address = get_contract_address(contract_name, chain)

                # Load the ABI from the deployment address
                abi = load_abi_from_address(chain, contract_address)

                # Dynamically create the contract class
                contract_class = type(f"{contract_name}", (BaseContract,), {"ABI": abi})
                cls._contract_classes[key] = contract_class
            else:
                contract_class = type(f"{contract_name}", (BaseContract,), {"ABI": abi})
            cls._contract_classes[key] = contract_class

        return cls._contract_classes[key]

    @classmethod
    def create(cls, chain: Chain, contract_identifier=None, address_override=None):
        """
        Creates an instance of the contract class for a given contract identifier (name or address) and chain.

        :param chain: The chain the contract is deployed on
        :param contract_identifier: The name or address of the contract on the specified chain, optional
        :param address_override: address with which to instantiate the contract, optional. We do this because some
                                 pool contracts only have a MockPool contract whose ABI we'd like to use
        :return: An instance of the contract class for the given contract identifier and chain
        """
        address_book = load_deployment_addresses(chain)

        if contract_identifier is None:
            raise ValueError(
                "A contract identifier (name or address) must be provided."
            )

        # Check if the contract_identifier is an address or a name
        is_address = (
            contract_identifier.startswith("0x") and len(contract_identifier) == 42
        )

        if is_address:
            contract_address = contract_identifier
            contract_name = address_book.get(contract_address, {}).get("name")

            if contract_name:
                contract_class = cls.get_contract_class(contract_name, chain)
            else:
                contract_name, etherscan_abi = get_name_and_abi_from_etherscan(
                    contract_address, chain
                )

                # contract_name = _validate_abi(etherscan_abi)

                if not contract_name:
                    raise ValueError(
                        f"Contract address {contract_address} not found in the address book and could not match ABI with local contracts."
                    )

                contract_class = cls.get_contract_class(
                    contract_name, chain, abi=etherscan_abi
                )

        else:
            contract_name = contract_identifier
            contract_address = get_contract_address(contract_name, chain)
            contract_class = cls.get_contract_class(contract_name, chain)

        return contract_class(address_override or contract_address, chain)


@memory.cache
def _validate_abi(abi):
    all_deployments_artifacts = load_all_deployments_artifacts()

    diffs = {}
    for _, artifact_data in all_deployments_artifacts.items():
        local_abi = artifact_data["abi"]
        if len(local_abi) == 0:
            continue
        diff = jsondiff(abi, local_abi)

        diffs[
            (
                diff.get(jd.missing, 0) and len(diff.get(jd.missing, 0)),
                diff.get(jd.identical, 0) and len(diff.get(jd.identical, 0)),
                diff.get(jd.delete, 0) and len(diff.get(jd.delete, 0)),
                diff.get(jd.insert, 0) and len(diff.get(jd.insert, 0)),
                diff.get(jd.update, 0) and len(diff.get(jd.update, 0)),
                diff.get(jd.add, 0) and len(diff.get(jd.add, 0)),
                diff.get(jd.discard, 0) and len(diff.get(jd.discard, 0)),
                diff.get(jd.replace, 0) and len(diff.get(jd.replace, 0)),
                diff.get(jd.left, 0) and len(diff.get(jd.left, 0)),
                diff.get(jd.right, 0) and len(diff.get(jd.right, 0)),
                artifact_data["name"],
            )
        ] = diff

    results = sorted([(x[-1], sum(x[:-1])) for x in diffs.keys()], key=lambda x: x[1])

    if results[0][1] > 0:
        raise ValueError(
            f"Contract ABI does not match any local contract ABIs. Closest match is {results[0][0]} with {results[0][1]} differences."
        )

    return results[0][0]
