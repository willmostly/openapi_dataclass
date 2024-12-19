from generator import Generator
from types import ModuleType

####################################################################
# This will not compile if wrapped in a function or class due to
# the reference to the generated class. This means pytest cannot be
# used. Run using the test.sh script.
####################################################################

if __name__ == "__main__":
    # from https://swagger.io/docs/specification/v2_0/basic-structure/
    simple_spec = """
    swagger: "2.0"
    info:
      title: Sample API
      description: API description in Markdown.
      version: 1.0.0

    host: api.example.com
    basePath: /v1
    schemes:
      - https

    definitions:
      User:
        properties:
          id:
            type: integer
          name:
            type: string
        # Both properties are required
        required:
          - id
          - name
    """

    generator = Generator()
    generated_class_definitions = generator.from_string(simple_spec)

    compiled = compile(generated_class_definitions, '', 'exec')
    module = ModuleType("testmodule")
    exec(compiled)
    user = User(name='Richard D. James', id=18081971)

    assert user.id == 18081971
    assert user.name == 'Richard D. James'
