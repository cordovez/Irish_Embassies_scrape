import scrapy
from urllib.parse import urlencode
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")


def get_proxy_url(url):
    payload = {"api_key": API_KEY, "url": url}
    proxy_url = "https://proxy.scrapeops.io/v1/?" + urlencode(payload)
    return proxy_url


class MySpiderSpider(scrapy.Spider):
    name = "my_spider"
    allowed_domains = ["www.your-url-with-403-response.com"]
    # start_urls = ["https://www.your-url-with-403-response.com"]

    def start_requests(self):
        start_url = "https://www.your-url-with-403-response.com/page/items"
        yield scrapy.Request(url=get_proxy_url(start_url), callback=self.parse)

    def parse(self, response):
        pass
