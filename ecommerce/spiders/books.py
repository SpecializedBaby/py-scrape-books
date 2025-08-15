import re

import scrapy
from scrapy.http import Response
from selenium import webdriver
from selenium.webdriver.common.by import By
from twisted.internet.defer import Deferred


class BooksSpider(scrapy.Spider):
    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/"]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.driver = webdriver.Chrome()

    def close(self, reason: str) -> Deferred[None] | None:
        self.driver.quit()
        return super().close(reason)

    def parse(self, response: Response, *args, **kwargs) -> dict:
        for book in response.css(".product_pod"):
            url_book = response.urljoin(url=book.css("a::attr(href)").get())
            title = book.css("a::attr(title)").get()
            price_class = book.css(".price_color::text").get()
            price = float(price_class.replace("£", ""))
            rating_class = book.css(".star-rating::attr(class)").get("")
            rating = rating_class.split()[-1] if rating_class else None

            self.driver.get(url_book)
            yield {
                "title": title,
                "price": price,
                "amount_in_stock": self._parse_amount_in_stock(),
                "rating": rating,  # Three
                "category": self._parse_category(),
                "description": self._parse_description(),
                "upc": self._parse_upc()
            }

            next_page = response.css("li.next a::attr(href)").get()
            if next_page is not None:
                next_page = response.urljoin(next_page)
                yield scrapy.Request(next_page, callback=self.parse)

    def _parse_amount_in_stock(self) -> int:
        num_availability = self.driver.find_element(
            By.CSS_SELECTOR,
            "p.availability"
        ).text.strip()
        return int(re.search(r"\d+", num_availability).group())

    def _parse_category(self) -> str:
        ul_element = self.driver.find_element(By.CSS_SELECTOR, "ul.breadcrumb")
        li_elements = ul_element.find_elements(By.TAG_NAME, "li")
        category = li_elements[2].find_element(By.TAG_NAME, "a").text
        return str(category)

    def _parse_description(self) -> str:
        description_element = self.driver.find_element(
            By.XPATH,
            "//div[@id='product_description']/following-sibling::p"
        )
        return str(description_element.text)

    def _parse_upc(self) -> str:
        table = self.driver.find_element(By.CSS_SELECTOR, "table.table")
        tbody = table.find_element(By.TAG_NAME, "tbody")
        tr_elements = tbody.find_elements(By.TAG_NAME, "tr")
        upc = tr_elements[0].find_element(By.TAG_NAME, "td").text
        return str(upc)
