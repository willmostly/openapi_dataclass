from generator import Generator

if __name__ == "__main__":

    spec = 'https://fakerestapi.azurewebsites.net/swagger/v1/swagger.json'
    generator = Generator(response_content_type='text/json')
    f = open('booker.py', 'w')
    generator.from_http(spec, f)
    f.close()
