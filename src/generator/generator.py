from __future__ import annotations

import yaml
from typing import Dict, TextIO, List, Optional
from dataclasses import dataclass
from enum import Enum
import keyword
from urllib.request import urlopen


class DataType(Enum):
    BASIC = 1
    REF = 2


indent = '    '


class PythonProgramElement:
    def __init__(self, lines: List[str], indent_level: int, children: List[PythonProgramElement] = None):
        self.lines = lines
        self.children = children

    def add_child(self, child: PythonProgramElement ):
        self.children.append(child)

    def __str__(self):
        return '\n'.join([indent + line for line in self.lines]) + ('\n' if self.children is not None else '')\
            + '\n'.join([child.__str__() for child in self.children or []])

    def indented_str(self, indent_level: int):
        return '\n'.join([indent*indent_level + line for line in self.lines]) + ('\n' if self.children is not None else '')\
            + '\n'.join([child.indented_str(indent_level=indent_level+1) for child in self.children or []])


@dataclass
class PythonProgramClass:
    name: str
    fields: List[PythonProgramClassField]
    methods: List[PythonProgramMethod]
    parent: Optional[str] = None
    imports: List[str] = ()

    def __str__(self):
        class_string = "\n".join(self.imports) + "\n" + f"class {self.name}"
        if self.parent:
            class_string += f"({self.parent})"
        class_string += ":\n\n"
        class_string += "\n".join([field.indented_str(1) for field in self.fields])
        class_string += "\n\n"
        class_string += "\n\n".join([method.indented_str(1) for method in self.methods])
        return class_string


@dataclass
class PythonProgramClassField:
    name: str
    type_string: str

    def __str__(self):
        return f"{self.name}: {self.type_string}"

    def indented_str(self, indent_level: int):
        return f"{indent*indent_level}{self.name}: {self.type_string}"


class MethodType(Enum):
    INSTANCE = 1
    CLASS = 2
    STATIC = 3


@dataclass
class PythonProgramMethod:
    name: str
    args: List[PythonProgramClassField]
    body: list[PythonProgramElement]
    method_type: MethodType = MethodType.INSTANCE
    return_type: Optional[str] = None

    def __method_type_to_arg__(self) -> List[str]:
        if self.method_type == MethodType.INSTANCE:
            return ['self']
        elif self.method_type == MethodType.CLASS:
            return ['cls']
        else:
            return []
    def __str__(self):
        definition = f"def {self.name}({', '.join(self.__method_type_to_arg__() + [arg.__str__() for arg in self.args])})"
        if self.return_type is not None:
            definition += f" -> {self.return_type}"
        definition += ":\n"
        return definition + "\n".join([element.__str__() for element in self.body])

    def indented_str(self, indent_level: int):
        definition = f"{indent_level*indent}def {self.name}({','.join(self.__method_type_to_arg__() + [arg.__str__() for arg in self.args])})"
        if self.return_type is not None:
            definition += f" -> {self.return_type}"
        definition += ":\n"
        return definition + "\n".join([element.indented_str(indent_level=indent_level+1) for element in self.body])


@dataclass
class ItemType:
    data_type: DataType
    type_string: str = None


@dataclass
class Parameter:
    name: str
    type: str
    required: bool


def map_item_type(field_type: ItemType, array_type: ItemType = None) -> str:
    if field_type is None:
        return 'Any'
    type_mapping = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "List",
        "object": "Dict",
    }
    if field_type.data_type == DataType.REF:
        ref = field_type.type_string.split('/')[-1]
        ref = ref.split('.')  # todo: if packages are implemented, use package name here for import
        return ref[-1]
    if field_type.type_string == "array":
        if array_type.data_type == DataType.REF:
            array_type_string = array_type.type_string.split('/')[-1]
            array_type_string = array_type_string.split('.')[-1]
            return f"List[{array_type_string}]"
        return f"List[{type_mapping[array_type.type_string]}]"
    return type_mapping[field_type.type_string]


class Generator:
    reserved_names = ['field', 'List', 'Dict', 'Any']
    indent = "    "

    def __init__(self, parent_class_name: str = 'YamlDataClass', parent_class_package: str = 'generator',
                 fixed_class_definitions: dict = (), response_content_type: str = 'application/json'):
        self.parent_class_name = parent_class_name
        if parent_class_package is not None and parent_class_name is None:
            raise Exception("parent_class_name must be defined if parent_class_package is used")
        self.parent_class_package = parent_class_package
        self.fixed_class_definitions = fixed_class_definitions
        self.response_content_type = response_content_type

    # Helper function to map OpenAPI types to Python types

    def openapi_type_to_item_type(self, properties: dict) -> ItemType:
        if "$ref" in properties:
            return ItemType(data_type=DataType.REF, type_string=properties["$ref"])
        elif "type" in properties:
            return ItemType(data_type=DataType.BASIC, type_string=properties["type"])
        else:
            print(properties)
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
            if class_name in self.fixed_class_definitions:
                result.append(self.fixed_class_definitions[class_name])
                continue

            fields = []
            required_fields = schema.get("required", [])
            properties = schema.get("properties", {})

            descriptions = []
            if schema.get("description"):
                descriptions.append(f"{self.indent}{schema.get('description')}")
            descriptions.append(f"{self.indent}Fields:")

            for field_name, field_props in properties.items():
                open_api_type = self.openapi_type_to_item_type(field_props)
                array_type = None
                if open_api_type.data_type == DataType.BASIC and open_api_type.type_string == 'array':
                    array_type = self.openapi_type_to_item_type(field_props["items"])

                field_type = map_item_type(open_api_type, array_type)
                default = "= field(default=None)" if field_name not in required_fields else ""
                descriptions.append(f"{self.indent}{field_name}: {field_type} | {field_props.get('description') or ''}")
                if field_name in required_fields:
                    fields.insert(0, f'{self.indent}{self.mangle_python_keyword(field_name)}: {field_type} {default}')
                else:
                    fields.append(f"{self.indent}{self.mangle_python_keyword(field_name)}: {field_type} {default}")

            docstring = "\n".join(descriptions)
            dataclass_definition = [
                f"\n@dataclass",
                f"class {class_name}{'(' + self.parent_class_name + ')' if self.parent_class_name is not None else ''}:",
                f'{self.indent}"""\n{docstring}\n{self.indent}"""\n',
                "\n".join(fields) if fields else "    pass",
            ]
            result.append("\n".join(dataclass_definition))

        return "\n\n".join(result)

    def __construct_name__(self, path: str, methoddef: dict, method: str):
        last_non_param_path_item = ''
        for item in path.split('/'):
            if item.startswith('{'):
                break
            last_non_param_path_item = item
        if len(methoddef.get('parameters', [])) == 0 and method == 'get':
            method = 'list'
        return methoddef.get("operationId", f"{method}{last_non_param_path_item}")

    def __process_parameters__(self, parameters: list) -> (List[Parameter], List[Parameter]):
        path_parameters = []
        query_parameters = []
        for parameter in parameters:
            if parameter['in'] == 'path':
                path_parameters.append(Parameter(
                    name=parameter['name'],
                    type=map_item_type(self.openapi_type_to_item_type(parameter['schema'])),
                    required=parameter['required']
                ))
            elif parameter['in'] == 'query':
                query_parameters.append(Parameter(
                    name=parameter['name'],
                    type=map_item_type(self.openapi_type_to_item_type(parameter['schema'])),
                    required=parameter['required']
                ))
        return path_parameters, query_parameters

    def __get_type_schema_from_content__(self, content: dict) -> dict | None:
        if self.response_content_type in content:
            return content[self.response_content_type]
        for key in content:
            if key.startswith(self.response_content_type):
                return content[key].get("schema")
        return None

    def __get_data_arg__(self, method: str, methoddef: dict) -> PythonProgramClassField | None:
        if method == "post" or method == "patch" or method == "put":
            openapi_type_properties = self.__get_type_schema_from_content__(
                methoddef.get("requestBody", {}).get("content", {}))
            if openapi_type_properties is None:
                print(
                    f"Warning: Generation only supports posts/patches with {self.response_content_type} content. "
                    f"Skipping: {method.upper()} {methoddef}")
                return None

            return PythonProgramClassField(
                name="data",
                type_string=map_item_type(
                    self.openapi_type_to_item_type(openapi_type_properties)))
        return None

    def __get_return_type__(self, method: str, methoddef: dict) -> (ItemType | None, ItemType | None):
        if method.lower() == 'delete' or method.lower() == 'put' or '204' in methoddef['responses']:
            return None, None
        elif '200' in methoddef['responses']:
            type_schema = self.__get_type_schema_from_content__(
                methoddef['responses']['200'].get("content", {}))
            if type_schema is None:
                print(
                    f"WARNING: NO VALID RESPONSE TYPE IN {methoddef['responses']['200']}!!!")
                return None, None
            openapi_type = self.openapi_type_to_item_type(type_schema)
            item_type = None
            if openapi_type.type_string == 'array':
                item_type = self.openapi_type_to_item_type(type_schema.get("items"))
            return openapi_type, item_type
        print(f"Warning: no supported success response type for {method.upper()} {methoddef}. Skipping")
        return None, None

    def convert_paths_to_methods(self, paths: Dict[str, Dict], response_content_type: str = 'application/json') -> PythonProgramClass:

        api_fields = [
                PythonProgramClassField(name="host", type_string="str"),
                PythonProgramClassField(name="request_headers", type_string="dict")]

        init_method = PythonProgramMethod(
            name="__init__",
            args=api_fields,
            body=[
                PythonProgramElement(lines=[f"self.{field.name} = {field.name}" for field in api_fields], indent_level=1)
            ]
        )
        api = PythonProgramClass(
            name="Api",
            fields=api_fields,
            methods=[init_method],
            imports=["import requests"])

        for path, methods in paths.items():
            for method, methoddef in methods.items():
                query_parameters, path_parameters = self.__process_parameters__(methoddef.get('parameters', []))
                function_name = self.__construct_name__(path=path, methoddef=methoddef, method=method)
                # TODO - add method descriptions
                # TODO - handle argument ordering in method class
                method_args = []
                for parameter in path_parameters + query_parameters:
                    if parameter.required:
                        method_args.insert(0, PythonProgramClassField(name=parameter.name, type_string=parameter.type))
                    else:
                        method_args.append(PythonProgramClassField(name=parameter.name, type_string=parameter.type))
                data_arg = self.__get_data_arg__(method, methoddef)
                if data_arg is not None:
                    method_args.insert(0, data_arg)

                return_statement = "pass"
                field_type, item_type = self.__get_return_type__(method, methoddef)
                response_type = map_item_type(field_type, item_type)
                if field_type is None:
                    pass
                elif response_type == 'str':
                    return_statement = "return response.string()"
                elif field_type.type_string == 'array':
                    return_statement = f"return [{map_item_type(item_type)}.load(item) for item in response.json()]"
                elif response_type is not None:
                    return_statement = f"return {response_type}.load(response.json())"

                request_call = f"response = requests.{method}(f'{{self.host}}{path}', headers=self.request_headers,"
                request_call += "params={" + ','.join(['"'+parameter.name+'": '+parameter.name for parameter in query_parameters]) + "}"
                if data_arg is not None:
                    request_call += ", data=data.asdict()"
                request_call += ")"
                method_body = [
                    PythonProgramElement(lines=[request_call], indent_level=2),
                    PythonProgramElement(lines=["try:"], indent_level=2, children=[
                        PythonProgramElement(lines=[return_statement], indent_level=3)]),
                    PythonProgramElement(lines=["except Exception as e:"], indent_level=2, children=[
                        PythonProgramElement(lines=["print(f'Bad response:{{response.json()}}')", "raise e"], indent_level=3)]),
                ]
                api.methods.append(PythonProgramMethod(
                    name=function_name,
                    return_type=response_type,
                    args=method_args,
                    body=method_body)
                )
        return api

    def from_http(self, spec_url: str, output_file: TextIO):
        return self.from_file(urlopen(spec_url), output_file)

    # Main function to parse the OpenAPI spec and generate dataclasses
    def from_file(self, openapi_file: TextIO, output_file: TextIO):
        openapi_spec = yaml.safe_load(openapi_file)

        definitions = {}
        spec_version = openapi_spec.get("swagger", openapi_spec.get('openapi'))
        if spec_version is None:
            print('Invalid openapi spec: no version information')
            exit(1)
        if spec_version == "2.0":
            definitions = openapi_spec.get("definitions")
        elif spec_version.startswith("3"):
            definitions = openapi_spec.get("components", {}).get('schemas')
        if not definitions:
            print("No definitions section found in the OpenAPI specification.")
            return

        dataclasses_code = self.convert_definitions_to_dataclasses(definitions)

        methods_class = self.convert_paths_to_methods(
            openapi_spec.get("paths"),
            response_content_type=self.response_content_type
        )
        output_file.write("from __future__ import annotations\n")
        output_file.write("from typing import List, Dict, Any\nfrom dataclasses import dataclass, field\n")
        if self.parent_class_name:
            if self.parent_class_package:
                output_file.write(f"from {self.parent_class_package} import {self.parent_class_name}\n")
            else:
                output_file.write(f"import {self.parent_class_name}")

        output_file.write("\n")
        output_file.write(dataclasses_code)
        output_file.write("\n\n")
        output_file.write(methods_class.__str__())
        output_file.write("\n")

        print(f"Dataclasses written to {output_file.name}")
        return methods_class

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
