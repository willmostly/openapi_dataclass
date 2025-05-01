from booker import *
from random import randint

class TestBookingApi:

    def __init__(self):
        self.booker = Api(host="http://fakerestapi.azurewebsites.net", request_headers={})

    def main(self):
        print("Testing booking API")
        books = self.booker.listBooks()
        print (f"Found {len(books)} books")

        random_index = randint(0, len(books) - 1)
        book = self.booker.getBooks(books[random_index].id)
        # assert book.asdict() == books[random_index].asdict()  # cannot use this - apparently publish date is not
        # constant. Looks like it is something like now() - offset
        assert book.excerpt == books[random_index].excerpt
        assert book.id == books[random_index].id
        assert book.pageCount == books[random_index].pageCount
        assert book.title == books[random_index].title
        assert book.description == books[random_index].description

        new_book = Book(id=99990, title="mother night", description="Action packed, fun for all", pageCount=222,
                        excerpt="Be careful who you pretend to be, because you are who you pretend to be",
                        publishDate='1961-01-01')
        self.booker.postBooks(data=new_book)

        authors = self.booker.listAuthors()
        random_index = randint(0, len(authors) - 1)
        author = self.booker.getAuthors(authors[random_index].id)

        assert author.id == authors[random_index].id
        assert author.firstName == authors[random_index].firstName
        assert author.lastName == authors[random_index].lastName

        self.booker.deleteAuthors(author.id)
        self.booker.putAuthors(author, author.id)
        author.firstName = "Beowulf"

if __name__ == "__main__":
    tester = TestBookingApi()
    tester.main()
