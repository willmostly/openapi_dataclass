# Python OpenApi Client implementations using Dataclasses instead of dictionaries

[Python Dataclasses](https://docs.python.org/3/library/dataclasses.html) integrate well with IDEs and support type checking. The dictionaries
generated in the standard swagger codegen Python clients don't do either. This project demonstrates how to generate a Dataclass based client from an 
OpenAPI spec.

The generator isn't production level code, but the generated clients should be. Note that the security section of the OpenAPI spec is ignored,
you will need to add your own request headers for security.

You may specify a parent class that every generated dataclass will inherit from. By default, they will inherit from [YamlDataClass](./src/generator/YamlDataClass.py),
which provides some serialization/deserialization capabilities. You can also provide explicit class definitions for methods and types the converter 
can't handle. There is some special handling for wierdness in the spec, like class names containing spaces or fields that are Python reserved words.
You are likely to find more edge cases.
