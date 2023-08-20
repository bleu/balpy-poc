import pytest
from balpy.codegen.abi_handler import ABIHandler


def test_abi_handler_basic_initialization():
    abi = [{"type": "function", "name": "testFunction", "inputs": [], "outputs": []}]
    handler = ABIHandler(abi, "TestContract")

    assert handler.abi == abi
    assert handler.contract_name == "TestContract"


def test_generate_base_content():
    abi = [
        {
            "type": "function",
            "name": "someFunction",
            "inputs": [
                {
                    "type": "tuple",
                    "internalType": "struct SomeModule.SomeStruct",
                    "name": "structInput",
                    "components": [{"name": "someAddress", "type": "address"}],
                }
            ],
            "outputs": [],
        }
    ]
    handler = ABIHandler(abi, "TestContract")
    content, todo_content = handler._generate_base_content()

    assert all(
        x in content[0] for x in ["@dataclass", "class SomeStruct:", "someAddress: str"]
    )


def test_generate_function_input_args():
    abi_item = {
        "type": "function",
        "name": "testFunction",
        "inputs": [
            {
                "name": "simpleInput",
                "type": "address",
                "internalType": "contract IContract",
            },
            {
                "name": "structInput",
                "type": "tuple",
                "internalType": "struct SomeModule.SomeStruct",
                "components": [{"name": "someAddress", "type": "address"}],
            },
            {"name": "enumInput", "type": "uint8", "internalType": "enum SomeEnum"},
        ],
        "outputs": [],
    }

    input_args = ABIHandler._generate_function_input_args(abi_item)

    assert input_args == [
        "simple_input",
        "(struct_input.someAddress)",
        "enum_input.value",
    ]


def test_generate_function_input_types():
    abi_item = {
        "type": "function",
        "name": "testFunction",
        "inputs": [
            {
                "name": "simpleInput",
                "type": "address",
                "internalType": "contract IContract",
            },
            {
                "name": "structInput",
                "type": "tuple",
                "internalType": "struct SomeModule.SomeStruct",
                "components": [{"name": "someAddress", "type": "address"}],
            },
            {"name": "enumInput", "type": "uint8", "internalType": "enum SomeEnum"},
        ],
        "outputs": [],
    }

    input_types = ABIHandler._generate_function_input_types(abi_item)

    assert input_types == [
        "simple_input: str",
        "struct_input: SomeStruct",
        "enum_input: SomeEnum",
    ]


def test_generate_class_definition():
    abi = [
        {
            "type": "function",
            "name": "testFunction",
            "inputs": [
                {
                    "name": "simpleInput",
                    "type": "address",
                    "internalType": "contract IContract",
                }
            ],
            "outputs": [{"name": "outputValue", "type": "uint256"}],
        }
    ]
    handler = ABIHandler(abi, "TestContract")
    class_definition = handler._generate_class_definition()

    assert "class TestContractMixin(BaseMixin):" in class_definition
    assert "def testFunction(self, simple_input: str) -> int:" in class_definition


@pytest.mark.parametrize(
    "contract_name, expected_constructor",
    [
        (
            "TestContract",
            'def __init__(self, chain: Chain):\n        contract_instance = BalancerContractFactory.create(chain, "TestContract")\n        super().__init__(contract_instance.contract_address, chain)',
        )
    ],
)
def test_generate_constructor(contract_name, expected_constructor):
    assert all(
        x in expected_constructor
        for x in ABIHandler._generate_constructor(contract_name)
    )
