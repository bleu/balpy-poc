import json

from balpy.codegen.abi_handler import ABIHandler


# Generalized to pass in filenames as arguments
def main(abi_file: str, types_file: str, todo_file: str):
    try:
        with open(abi_file, "r") as f:
            abi_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {abi_file} not found.")
        exit(1)
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from {abi_file}.")
        exit(1)

    contract_name = abi_file.split("ABI")[0]
    handler = ABIHandler(abi_data, contract_name)
    content, todo_content = handler.generate()

    with open(types_file, "w") as f:
        f.write(content)

    with open(todo_file, "w") as f:
        f.write(todo_content)


if __name__ == "__main__":
    ABI_FILE = "VaultABI.json"
    TYPES_FILE = "Vault_types.py"
    TODO_FILE = "Vault_TODO.py"

    main(ABI_FILE, TYPES_FILE, TODO_FILE)
