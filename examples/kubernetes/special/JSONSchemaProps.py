from dataclasses import asdict
from generator import YamlDataClass
import marshmallow_dataclass
from yaml import safe_load
from functools import singledispatchmethod


def __JSONSchemaProps_alias_keywords__(data: dict) -> dict:
    data["ref"] = data["$ref"]
    data["schema"] = data["$schema"]
    data["x_kubernetes_embedded_resource"] = data["x-kubernetes-embedded-resource"]
    data["x_kubernetes_int_or_string"] = data["x-kubernetes-int-or-string"]
    data["x_kubernetes_list_map_keys"] = data["x-kubernetes-list-map-keys"]
    data["x_kubernetes_list_type"] = data["x-kubernetes-list-type"]
    data["x_kubernetes_preserve_unknown_fields"] = data["x-kubernetes-preserve-unknown-fields"]
    data["x_kubernetes_validations"] = data["x-kubernetes-validations"]
    return data


@dataclass
class JSONSchemaProps(YamlDataClass):
    ref: str = field(default=None)
    schema: str = field(default=None)
    additionalItems: JSONSchemaPropsOrBool = field(default=None)
    additionalProperties: JSONSchemaPropsOrBool = field(default=None)
    allOf: List[JSONSchemaProps] = field(default=None)
    anyOf: List[JSONSchemaProps] = field(default=None)
    default: JSON = field(default=None)
    definitions: Dict = field(default=None)
    dependencies: Dict = field(default=None)
    description: str = field(default=None)
    enum: List[JSON] = field(default=None)
    example: JSON = field(default=None)
    exclusiveMaximum: bool = field(default=None)
    exclusiveMinimum: bool = field(default=None)
    externalDocs: ExternalDocumentation = field(default=None)
    format: str = field(default=None)
    id: str = field(default=None)
    items: JSONSchemaPropsOrArray = field(default=None)
    maxItems: int = field(default=None)
    maxLength: int = field(default=None)
    maxProperties: int = field(default=None)
    maximum: float = field(default=None)
    minItems: int = field(default=None)
    minLength: int = field(default=None)
    minProperties: int = field(default=None)
    minimum: float = field(default=None)
    multipleOf: float = field(default=None)
    NOT: JSONSchemaProps = field(default=None)
    nullable: bool = field(default=None)
    oneOf: List[JSONSchemaProps] = field(default=None)
    pattern: str = field(default=None)
    patternProperties: Dict = field(default=None)
    properties: Dict = field(default=None)
    required: List[str] = field(default=None)
    title: str = field(default=None)
    type: str = field(default=None)
    uniqueItems: bool = field(default=None)
    x_kubernetes_embedded_resource: bool = field(default=None)
    x_kubernetes_int_or_string: bool = field(default=None)
    x_kubernetes_list_map_keys: List[str] = field(default=None)
    x_kubernetes_list_type: str = field(default=None)
    x_kubernetes_map_type: str = field(default=None)
    x_kubernetes_preserve_unknown_fields: bool = field(default=None)
    x_kubernetes_validations: List[ValidationRule] = field(default=None)

    def asdict(self) -> dict:
        d = asdict(self)
        d["$ref"] = self.ref
        d["$schema"] = self.schema
        d["x-kubernetes-embedded-resource"] = self.x_kubernetes_embedded_resource
        d["x-kubernetes-int-or-string"] = self.x_kubernetes_int_or_string
        d["x-kubernetes-list-map-keys"] = self.x_kubernetes_list_map_keys
        d["x-kubernetes-list-type"] = self.x_kubernetes_map_type
        d["x-kubernetes-preserve-unknown-fields"] = self.x_kubernetes_preserve_unknown_fields
        d["x-kubernetes-validations"] = self.x_kubernetes_validations
        return d

    @singledispatchmethod
    @classmethod
    def load(cls, arg) -> YamlDataClass:
        raise NotImplemented('YamlDataClass.load() only accepts dicts and json strings')

    @load.register
    @classmethod
    def _(cls, data: str) -> YamlDataClass:
        schema = marshmallow_dataclass.class_schema(cls)()
        return schema.load(__JSONSchemaProps_alias_keywords__(safe_load(data)))

    @load.register
    @classmethod
    def _(cls, data: dict) -> YamlDataClass:
        schema = marshmallow_dataclass.class_schema(cls)()
        return schema.load(__JSONSchemaProps_alias_keywords__(data))
