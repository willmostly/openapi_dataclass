from generator import Generator


class GalaxyGenerator:
    fixed_class_definitions = {
    }

    def main(self):
        generator = Generator(
            parent_class_name='YamlDataClass',
            parent_class_package='generator',
            fixed_class_definitions=self.fixed_class_definitions)

        generator.from_file(open('resources/galaxy-openapiv3.json', 'r'), open('./galaxy_models.py', 'w'))

if __name__ == "__main__":
    galaxy_generator = GalaxyGenerator()
    galaxy_generator.main()
