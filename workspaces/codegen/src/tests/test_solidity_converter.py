from balpy.codegen.solidity_converter import SolidityConverter


def test_convert_type_basic():
    assert SolidityConverter.convert_type("address") == "str"
    assert SolidityConverter.convert_type("bool") == "bool"
    assert SolidityConverter.convert_type("string") == "str"
    assert SolidityConverter.convert_type("uint") == "int"


def test_convert_type_dynamic():
    assert SolidityConverter.convert_type("uint8") == "int"
    assert SolidityConverter.convert_type("bytes1") == "HexBytes"
    assert SolidityConverter.convert_type("bytes32") == "HexBytes"


def test_convert_type_arrays():
    assert SolidityConverter.convert_type("address[]") == "List[str]"
    assert SolidityConverter.convert_type("uint8[3]") == "List[int]"


def test_convert_type_structs():
    assert (
        SolidityConverter.convert_type("tuple", "SomeModule.SomeStruct") == "SomeStruct"
    )


def test_convert_type_enums():
    assert (
        SolidityConverter.convert_type("enum", "enum SomeModule.SomeEnum") == "SomeEnum"
    )


def test_generate_dataclass():
    components = [
        {"name": "someAddress", "type": "address"},
        {"name": "value", "type": "uint8"},
        {"name": "isTrue", "type": "bool"},
    ]
    result = SolidityConverter.generate_dataclass(components, "SomeModule.SomeStruct")
    expected_result = """@dataclass
class SomeStruct:
    someAddress: str
    value: int
    isTrue: bool"""
    assert result == expected_result


def test_generate_enum_with_values():
    enum_values = ["VALUE_A", "VALUE_B"]
    result = SolidityConverter.generate_enum("SomeModule.SomeEnum", enum_values)
    expected_result = """class SomeEnum(Enum):
    VALUE_A = 1
    VALUE_B = 2"""
    assert result == expected_result


def test_generate_enum_without_values():
    result = SolidityConverter.generate_enum("SomeModule.SomeEnum")
    expected_result = """class SomeEnum(Enum):
    # Enum values are placeholders as they're not provided in the ABI
    VALUE_1 = 1
    VALUE_2 = 2"""
    assert result == expected_result
