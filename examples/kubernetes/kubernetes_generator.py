from generator import Generator


class KubernetesGenerator:
    fixed_class_definitions = {
        'JSONSchemaProps': open('./special/JSONSchemaProps.py').read()
    }

    def main(self):
        generator = Generator(
            parent_class_name='YamlDataClass',
            parent_class_package='generator',
            fixed_class_definitions=self.fixed_class_definitions)

        generator.from_file(open('resources/openapiv2.json', 'r'), open('./kubernetes_models.py', 'w'))

if __name__ == "__main__":
    kubernetes_generator = KubernetesGenerator()
    kubernetes_generator.main()
