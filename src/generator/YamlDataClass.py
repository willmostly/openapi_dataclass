from typing import cast, Self
import marshmallow_dataclass
from dataclasses import asdict, is_dataclass
from functools import singledispatchmethod
from yaml import safe_load, dump
import keyword
from generator.generator import Generator


def __dealias_keywords__(output_dict: dict):
    for key in output_dict:
        if key.isupper():
            match_found = False
            for kw in list(keyword.kwlist) + Generator.reserved_names:
                if key.casefold() == kw.casefold():
                    match_found = True
                    output_dict[kw] = output_dict[key]
                    del output_dict[key]
            if not match_found:
                raise Exception(f"Unhandled uppercase keyword key: {key.upper()}!")
    return output_dict


def __alias_keywords__(input_dict: dict):
    for key in input_dict:
        if keyword.iskeyword(key) or key in Generator.reserved_names:
            if keyword.iskeyword(key.upper()):
                raise Exception(f"Unhandled uppercase keyword key: {key.upper()}!")
            print(f'delete {key}')
            input_dict[key.upper()] = input_dict[key]
            del input_dict[key]
    return input_dict


class YamlDataClass:

    @singledispatchmethod
    @classmethod
    def load(cls, arg) -> Self:
        raise NotImplemented('YamlDataClass.load() only accepts dicts and json strings')

    @load.register
    @classmethod
    def _(cls, data: str) -> Self:
        if is_dataclass(cls):
            schema = marshmallow_dataclass.class_schema(cls)()
            return cast(cls, schema.load(__alias_keywords__(safe_load(data))))
        else:
            raise NotImplemented('Only dataclasses should inherit from YamlDataClass!')

    @load.register
    @classmethod
    def _(cls, data: dict) -> Self:
        if is_dataclass(cls):
            schema = marshmallow_dataclass.class_schema(cls)()
            return cast(cls, schema.load(__alias_keywords__(data)))
        else:
            raise NotImplemented('Only dataclasses should inherit from YamlDataClass!')

    def asdict(self) -> dict:
        if is_dataclass(self):
            return __dealias_keywords__(asdict(self))
        else:
            raise NotImplemented('Only dataclasses should inherit from JsonDataClass!')

    def to_yaml(self) -> str:
        return dump(self.asdict())
