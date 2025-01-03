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

    def __str__(self):
        class_string = f"class {self.name}"
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
    args: List[PythonProgramMethodArg]
    return_type: Optional[str]
    body: list[PythonProgramElement]
    method_type: MethodType = MethodType.INSTANCE

    def __method_type_to_arg__(self) -> List[str]:
        if self.method_type == MethodType.INSTANCE:
            return ['self']
        elif self.method_type == MethodType.CLASS:
            return ['cls']
        else:
            return []
    def __str__(self):
        definition = f"def {self.name}({','.join(self.__method_type_to_arg__() + [arg.__str__() for arg in self.args])})"
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
class PythonProgramMethodArg:
    name: str
    type_string: str

    def __str__(self):
        return f"{self.name}: {self.type_string}"

    def indented_str(self, indent_level: int):
        return f"{indent_level*indent}{self.name}: {self.type_string}"

@dataclass
class ItemType:
    data_type: DataType
    type_string: str = None


@dataclass
class Parameter:
    name: str
    type: str
    required: bool


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

            descriptions = []
            if schema.get("description"):
                descriptions.append(f"{self.indent}{schema.get('description')}")
            descriptions.append(f"{self.indent}Fields:")

            for field_name, field_props in properties.items():
                open_api_type = self.get_openapi_type(field_props)
                array_type = None
                if open_api_type.data_type == DataType.BASIC and open_api_type.type_string == 'array':
                    array_type = self.get_openapi_type(field_props["items"])

                field_type = map_openapi_type(open_api_type, array_type)
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

    def convert_paths_to_methods(self, paths: Dict[str, Dict], response_content_type: str = 'application/json') -> (str, PythonProgramClass):

        result = []
        api = PythonProgramClass(
            name="Api",
            fields=[
                PythonProgramClassField(name="host", type_string="str"),
                PythonProgramClassField(name="request_headers", type_string="dict")],
            methods=[])

        for path, methods in paths.items():
            for method, methoddef in methods.items():
                method_args = []
                path_parameters = []
                query_parameters = []
                for parameter in methoddef.get('parameters', []):
                    if parameter['in'] == 'path':
                        path_parameters.append(Parameter(
                            name=parameter['name'],
                            type=map_openapi_type(self.get_openapi_type(parameter['schema'])),
                            required=parameter['required']
                        ))
                    elif parameter['in'] == 'query':
                        query_parameters.append(Parameter(
                            name=parameter['name'],
                            type=map_openapi_type(self.get_openapi_type(parameter['schema'])),
                            required=parameter['required']
                        ))
                function_name = self.__construct_name__(path=path, methoddef=methoddef, method=method)
                #TODO - add method descriptions
                args = []
                for parameter in path_parameters + query_parameters:
                    if parameter.required:
                        args.insert(0, f"{parameter.name}:{parameter.type}")
                        method_args.insert(0, PythonProgramMethodArg(name=parameter.name, type_string=parameter.type))
                    else:
                        args.append(f"{parameter.name}:{parameter.type} = None")
                        method_args.append(PythonProgramMethodArg(name=parameter.name, type_string=parameter.type))
                data_arg = None
                if method == "post" or method == "patch" or method == "put":
                    request_body_content = methoddef.get("requestBody", {}).get("content", {})
                    if response_content_type not in request_body_content:
                        contains_valid_response_type = False
                        for key in request_body_content:
                            if key.startswith(response_content_type):
                                response_content_type = key
                                contains_valid_response_type = True
                        if not contains_valid_response_type:
                            print(f"Warning: Generation only supports posts/patches with {response_content_type} content. Skipping: {method.upper()} {path}")
                            continue
                    request_body_type = map_openapi_type(self.get_openapi_type(request_body_content[response_content_type]["schema"]))
                    data_arg = f'data: {request_body_type}, '
                    method_args.insert(0, PythonProgramMethodArg(name='data', type_string=request_body_type))

                return_statement = "pass"
                response_type = "Any"
                if method.lower() == 'delete' or method.lower() == 'put' or '204' in methoddef['responses']:
                    response_type = 'None'
                elif '200' in methoddef['responses']:
                    if 'content' in methoddef['responses']['200']:
                        if response_content_type not in methoddef['responses']['200'].get('content'):
                            contains_valid_response_type = False
                            for key in methoddef['responses']['200']['content']:
                                if key.startswith(response_content_type):
                                    response_content_type = key
                                    contains_valid_response_type = True
                            if not contains_valid_response_type:
                                print(f"WARNING: NO VALID RESPONSE TYPE FOR {function_name} IN {methoddef['responses']['200']['content']}!!!. SKIPPING!!!")
                                continue
                        #  todo - refactor the type handling to avoid multiple calls and branches
                        openapi_type = self.get_openapi_type(methoddef['responses']['200']['content'][response_content_type]['schema'])
                        item_type = None
                        if openapi_type.type_string == 'array':
                            item_type = self.get_openapi_type(methoddef['responses']['200']['content'][response_content_type]['schema']["items"])
                        response_type = map_openapi_type(openapi_type, item_type)
                        if response_type == 'str':
                            return_statement = "return response.string()"
                        elif openapi_type.type_string == 'array':
                            return_statement = f"return [{map_openapi_type(item_type)}.load(item) for item in response.json()]"
                        else:
                            return_statement = f"return {response_type}.load(response.json())"
                else:
                    print(f"Warning: no supported success response type for {method.upper()} {path}. Skipping")
                    print(f"responses:\n{methoddef['responses']}")
                    continue

                result.append(f"""{self.indent}def {function_name}(self, {data_arg or ''}{', '.join(args)}) -> {response_type}:
{self.indent*2}response = requests.{method}(f'{{self.host}}{path}',
{self.indent*8}headers=self.request_headers,
{self.indent*8}params={{{','.join(['"'+parameter.name+'": '+parameter.name for parameter in query_parameters])}}}{',' if data_arg else ''}
{self.indent*8}{'data=data.asdict()' if data_arg else ''})
{self.indent*2}try:
{self.indent*3}{return_statement}
{self.indent*2}except Exception as e:
{self.indent*3}print(f'Bad response:{{response.json()}}')
{self.indent*3}raise e""")

                request_call = f"response = requests.{method}(f'{{self.host}}{path}', headers=self.request_headers,"
                request_call += "params={" + ','.join(['"'+parameter.name+'": '+parameter.name for parameter in query_parameters]) + "}"
                if data_arg:
                    request_call += ", data=data.asdict()"
                request_call += ")"
                method_body = [
                    PythonProgramElement(lines=[request_call], indent_level=2),
                    PythonProgramElement(lines=["try:"], indent_level=2, children=[
                        PythonProgramElement(lines=[return_statement], indent_level=3)]),
                    PythonProgramElement(lines=["except Exception as e::"], indent_level=2, children=[
                        PythonProgramElement(lines=["print(f'Bad response:{{response.json()}}')", "raise e"], indent_level=3)]),
                ]
                api.methods.append(PythonProgramMethod(
                    name=function_name,
                    return_type=response_type,
                    args=method_args,
                    body=method_body)
                )
        return "\n".join(result), api

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

        methods, methods_class = self.convert_paths_to_methods(openapi_spec.get("paths"), response_content_type=self.response_content_type)
        output_file.write("from __future__ import annotations\n")
        output_file.write("from typing import List, Dict, Any\nfrom dataclasses import dataclass, field\n")
        if self.parent_class_name:
            if self.parent_class_package:
                output_file.write(f"from {self.parent_class_package} import {self.parent_class_name}\n")
            else:
                output_file.write(f"import {self.parent_class_name}")

        output_file.write("\n")
        output_file.write(dataclasses_code)
        output_file.write("\n")
        output_file.write("""

######################################
# API from paths
######################################
import requests


class API:

    def __init__(self, host: str, request_headers: dict):
        self.host = host
        self.request_headers = request_headers

""")
        output_file.write(methods)
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
