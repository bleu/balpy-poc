import re
from typing import Any, Dict, List, Tuple

from balpy.codegen.solidity_converter import SolidityConverter

CAMEL_TO_SNAKE_REGEX = re.compile(r"(?<!^)(?=[A-Z])")


class ABIHandler:
    """Handles ABI for Ethereum contracts."""

    def __init__(self, abi: List[Dict[str, Any]], contract_name: str):
        self.abi = abi
        self.contract_name = contract_name
        self.imports_for_types = [
            "from typing import List, Tuple, Any",
            "from web3.types import TxParams, BlockIdentifier, Wei",
            "from hexbytes import HexBytes",
            "from balpy.contracts.base_contract import BaseContract, BalancerContractFactory",
            "from balpy.chains import Chain",
            "from dataclasses import dataclass",
            "from abc import ABC, abstractmethod",
            f"from .{contract_name}_TODO import *",
        ]
        self.imports_for_todo = ["from enum import Enum"]

    def generate(self) -> Tuple[str, str]:
        """Generates the ABI handler for types and TODO content."""
        content, todo_content = self._generate_base_content()
        return "\n".join(self.imports_for_types + content), "\n".join(
            self.imports_for_todo + todo_content
        )

    def _generate_base_content(self) -> Tuple[List[str], List[str]]:
        generated_types = set()
        generated_structs = set()
        content = []
        todo_content = []

        for item in self.abi:
            if item["type"] == "function":
                for input_item in item["inputs"]:
                    if input_item["type"] == "tuple":
                        struct_name = SolidityConverter._get_struct_name(
                            input_item["internalType"]
                        )
                        if struct_name not in generated_structs:
                            dataclass_str = SolidityConverter.generate_dataclass(
                                input_item["components"], input_item["internalType"]
                            )
                            content.append(dataclass_str)
                            generated_structs.add(struct_name)
                    elif (
                        "enum " in input_item["internalType"]
                        and input_item["internalType"] not in generated_types
                    ):
                        enum_str = SolidityConverter.generate_enum(
                            input_item["internalType"]
                        )
                        todo_content.append(enum_str)
                        generated_types.add(input_item["internalType"])

        content.append(self._generate_class_definition())
        return content, todo_content

    @staticmethod
    def _generate_function_input_args(item: Dict[str, Any]) -> List[str]:
        input_args = []
        for i in item.get("inputs", []):
            input_name = CAMEL_TO_SNAKE_REGEX.sub("_", i["name"]).lower()
            if i["type"] == "tuple":
                component_names = [component["name"] for component in i["components"]]
                tuple_representation = ", ".join(
                    [f"{input_name}.{component}" for component in component_names]
                )
                input_args.append(f"({tuple_representation})")
            elif "enum " in i["internalType"]:
                input_args.append(f"{input_name}.value")
            else:
                input_args.append(input_name)

        return input_args

    def _generate_class_definition(self) -> str:
        lines = [
            "class BaseMixin(ABC):",
            "    @abstractmethod",
            "    def _method_from_base(self, method_name, *args, **kwargs):",
            "        raise NotImplementedError",
            f"class {self.contract_name}Mixin(BaseMixin):",
            "\n",
        ]

        for item in self.abi:
            if item["type"] == "function":
                fn_name = item["name"]
                input_types = self._generate_function_input_types(item)
                input_args = self._generate_function_input_args(item)
                output_types = [
                    SolidityConverter.convert_type(o["type"], o.get("internalType"))
                    for o in item.get("outputs", [])
                ]
                output_str = (
                    "None"
                    if not output_types
                    else output_types[0]
                    if len(output_types) == 1
                    else f'Tuple[{", ".join(output_types)}]'
                )
                fn_type_hint = f'    def {fn_name}(self, {", ".join(input_types)}) -> {output_str}:'
                lines.append(fn_type_hint)
                fn_implementation = f"        return self._method_from_base('{fn_name}', {', '.join(input_args)})"
                lines.append(fn_implementation)
                lines.append("")

        lines.extend(
            [
                "",
                f"class {self.contract_name}(BaseContract, {self.contract_name}Mixin):",
                self._generate_constructor(self.contract_name),
                "",
                "    def _method_from_base(self, method_name, *args, **kwargs):",
                f"        return BaseContract.__getattr__(self, method_name)(*args, **kwargs)",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def _generate_constructor(contract_name) -> str:
        return f"""
def __init__(self, chain: Chain):
    contract_instance = BalancerContractFactory.create(chain, "{contract_name}")
    super().__init__(contract_instance.contract_address, chain)"""

    @staticmethod
    def _generate_function_input_types(item: Dict[str, Any]) -> List[str]:
        input_types = []
        for i in item.get("inputs", []):
            python_type = SolidityConverter.convert_type(
                i["type"], i.get("internalType")
            )
            input_name = CAMEL_TO_SNAKE_REGEX.sub("_", i["name"]).lower()

            input_types.append(f"{input_name}: {python_type}")

        return input_types
