from typing import Any, Dict, List

# Constants
SOLIDITY_TO_PYTHON_TYPES = {
    "address": "str",
    "bool": "bool",
    "string": "str",
    "bytes": "HexBytes",
    "uint": "int",
    "int": "int",
}
DYNAMIC_SOLIDITY_TYPES = {
    f"{prefix}{i*8 if prefix != 'bytes' else i}": "int"
    if prefix != "bytes"
    else "HexBytes"
    for prefix in ["uint", "int", "bytes"]
    for i in range(1, 33)
}
SOLIDITY_TO_PYTHON_TYPES.update(DYNAMIC_SOLIDITY_TYPES)


class SolidityConverter:
    """Handles conversion of Solidity types to Python types."""

    @staticmethod
    def _get_struct_name(internal_type: str) -> str:
        """Returns the struct name for a given internal type."""
        return internal_type.split(".")[-1].replace("[]", "")

    @classmethod
    def convert_type(cls, solidity_type: str, internal_type: str = None) -> str:
        """Converts Solidity types to Python types."""
        if internal_type and "enum" in internal_type:
            return internal_type.split("enum")[-1].split(".")[-1].strip()
        if "[]" in solidity_type:
            base_type = solidity_type.replace("[]", "")
            return f'List[{SOLIDITY_TO_PYTHON_TYPES.get(base_type, "Any")}]'
        elif "[" in solidity_type and "]" in solidity_type:
            base_type = solidity_type.split("[")[0]
            return f'List[{SOLIDITY_TO_PYTHON_TYPES.get(base_type, "Any")}]'
        elif solidity_type == "tuple":
            return cls._get_struct_name(internal_type)
        return SOLIDITY_TO_PYTHON_TYPES.get(solidity_type, "Any")

    @classmethod
    def generate_dataclass(
        cls, components: List[Dict[str, Any]], internal_type: str
    ) -> str:
        """Generates a Python dataclass from Solidity components."""
        struct_name = cls._get_struct_name(internal_type)
        lines = ["@dataclass", f"class {struct_name}:"]
        for component in components:
            component_type = cls.convert_type(
                component["type"], component.get("internalType")
            )
            lines.append(f"    {component['name']}: {component_type}")
        return "\n".join(lines)

    @staticmethod
    def generate_enum(enum_type: str, enum_values: List[str] = None) -> str:
        """Generates a Python enum from a Solidity enum type."""
        enum_name = enum_type.split(".")[-1]
        lines = [f"class {enum_name}(Enum):"]
        if not enum_values:
            lines.extend(
                [
                    "    # Enum values are placeholders as they're not provided in the ABI",
                    "    VALUE_1 = 1",
                    "    VALUE_2 = 2",
                ]
            )
        else:
            for idx, value in enumerate(enum_values):
                lines.append(f"    {value} = {idx + 1}")
        return "\n".join(lines)
