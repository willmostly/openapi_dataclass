import yaml
from typing import Dict, TextIO
from dataclasses import dataclass
from enum import Enum
import keyword


class DataType(Enum):
    BASIC = 1
    REF = 2


@dataclass
class ItemType:
    data_type: DataType
    type_string: str = None


def map_openapi_type(openapi_type: ItemType, array_type: ItemType = None) -> str:
    type_mapping = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "List",
        "object": "Dict",
    }
    if openapi_type.data_type == DataType.REF:
        ref = openapi_type.type_string.split('/')[-1]
        ref = ref.split('.')  # todo: if packages are implemented, use package name here for import
        return ref[-1]
    if openapi_type.type_string == "array":
        if array_type.data_type == DataType.REF:
            array_type_string = array_type.type_string.split('/')[-1]
            array_type_string = array_type_string.split('.')[-1]
            return f"List[{array_type_string}]"
        return f"List[{type_mapping[array_type.type_string]}]"
    return type_mapping[openapi_type.type_string]


class Generator:
    reserved_names = ['field', 'List', 'Dict', 'Any']

    def __init__(self, parent_class_name: str = None, parent_class_package: str = None,
                 fixed_class_definitions: dict = ()):
        self.parent_class_name = parent_class_name
        if parent_class_package is not None and parent_class_name is None:
            raise Exception("parent_class_name must be defined if parent_class_package is used")
        self.parent_class_package = parent_class_package
        self.fixed_class_definitions = fixed_class_definitions

    # Helper function to map OpenAPI types to Python types

    def get_openapi_type(self, properties: dict) -> ItemType:
        if "$ref" in properties:
            return ItemType(data_type=DataType.REF, type_string=properties["$ref"])
        elif "type" in properties:
            return ItemType(data_type=DataType.BASIC, type_string=properties["type"])
        else:
            raise NotImplementedError(f'field properties contains neither a type nor a $ref: {properties}')

    def mangle_python_keyword(self, word: str) -> str:
        if keyword.iskeyword(word) or word in self.reserved_names:
            return word.upper()
        return word

    # Function to convert OpenAPI definitions to dataclasses
    def convert_definitions_to_dataclasses(self, definitions: Dict[str, Dict]) -> str:
        result = []
        for name, schema in definitions.items():
            name = name.split('.')
            class_name = name[-1]
            package_name = name[:-1]  # todo: create python packages
            if class_name in self.fixed_class_definitions:
                result.append(self.fixed_class_definitions[class_name])
                continue

            fields = []
            required_fields = schema.get("required", [])
            properties = schema.get("properties", {})

            for field_name, field_props in properties.items():
                open_api_type = self.get_openapi_type(field_props)
                array_type = None
                if open_api_type.data_type == DataType.BASIC and open_api_type.type_string == 'array':
                    array_type = self.get_openapi_type(field_props["items"])

                field_type = map_openapi_type(open_api_type, array_type)
                default = "= field(default=None)" if field_name not in required_fields else ""
                if field_name in required_fields:
                    fields.insert(0, f"    {self.mangle_python_keyword(field_name)}: {field_type} {default}")
                else:
                    fields.append(f"    {self.mangle_python_keyword(field_name)}: {field_type} {default}")

            dataclass_definition = [
                f"\n@dataclass",
                f"class {class_name}{'(' + self.parent_class_name + ')' if self.parent_class_name is not None else ''}:",
                "\n".join(fields) if fields else "    pass",
            ]
            result.append("\n".join(dataclass_definition))

        return "\n\n".join(result)

    # Main function to parse the OpenAPI spec and generate dataclasses
    def from_file(self, openapi_file: TextIO, output_file: TextIO):
        openapi_spec = yaml.safe_load(openapi_file)

        if openapi_spec.get("swagger") != "2.0":
            print("Only OpenAPI v2 is currently supported")
            exit(1)
        definitions = openapi_spec.get("definitions", {})
        if not definitions:
            print("No definitions section found in the OpenAPI specification.")
            return

        dataclasses_code = self.convert_definitions_to_dataclasses(definitions)

        output_file.write("from __future__ import annotations\n")
        output_file.write("from typing import List, Dict, Any\nfrom dataclasses import dataclass, field\n")
        if self.parent_class_name:
            if self.parent_class_package:
                output_file.write(f"from {self.parent_class_package} import {self.parent_class_name}\n")
            else:
                output_file.write(f"import {self.parent_class_name}")

        output_file.write("\n")
        output_file.write(dataclasses_code)

        print(f"Dataclasses written to {output_file.name}")

    def from_string(self, openapi_spec: str) -> str:

        definitions = yaml.safe_load(openapi_spec).get("definitions", {})
        if not definitions:
            print("No definitions section found in the OpenAPI specification.")
            return

        dataclasses_code = self.convert_definitions_to_dataclasses(definitions)

        imports = f"""
from __future__ import annotations
from typing import List, Dict, Any
from dataclasses import dataclass, field        
        """

        if self.parent_class_package is not None:
            imports += f'from {self.parent_class_package} import {self.parent_class_name}'
        elif self.parent_class_name is not None:
            imports += f'import {self.parent_class_name}'

        return imports + dataclasses_code
