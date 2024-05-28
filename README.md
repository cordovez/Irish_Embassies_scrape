# Scrapy_ScrapeOps_template
A Scrapy spider project for websites that respond with a 403 HTTP response.

You must sign-up and obtain an API key from [ScrapeOps](https://scrapeops.io/).

This project uses Poetry for dependency management. To create a virtual environment and install dependencies using Poetry, please [refer to this page](https://python-poetry.org/docs/basic-usage/#using-your-virtual-environment).

Once you have set up your virtual environment and installed the dependecies, you can delete 'template_' from `.template_env` and paste your api key in the file.

Finally, replace the fake urls used in 'allowed_domains' and 'start_url' in the `my_spider.py` file.

To bypass a 403 response  [I followed instructions from this video](https://www.youtube.com/watch?v=NiFuoJw0sn8) to create these changes:

## Settings 
### Middlewares:
```
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": 400,
}
```
### Concurrent Requests:
```
CONCURRENT_REQUESTS = 1
```

## Spider
The function get_proxy_url() to use ScrapeOps, and start_requests() to override scrapy's default.
## connect to ScrapeOps
``` py
def get_proxy_url(url):
    payload = {"api_key": API_KEY, "url": url}
    proxy_url = "https://proxy.scrapeops.io/v1/?" + urlencode(payload)
    return proxy_url
```

## Override start_urls
```py
class MySpiderSpider(scrapy.Spider):
    name = "my_spider"
    allowed_domains = ["www.your-url-with-403-response.com"]
    # start_urls = ["https://www.your-url-with-403-response.com"]

    def start_requests(self):
        start_url = "https://www.your-url-with-403-response.com/page/items"
        yield scrapy.Request(url=get_proxy_url(start_url), callback=self.parse)

    def parse(self, response):
        pass

```