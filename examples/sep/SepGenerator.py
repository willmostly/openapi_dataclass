from generator import Generator


class SepGenerator:
    fixed_class_definitions = {
    }

    def main(self):
        generator = Generator(
            parent_class_name='YamlDataClass',
            parent_class_package='generator',
            fixed_class_definitions=self.fixed_class_definitions)

        generator.from_file(open('resources/sep_swagger.json', 'r'), open('./sep_models.py', 'w'))

if __name__ == "__main__":
    sep_generator = SepGenerator()
    sep_generator.main()
