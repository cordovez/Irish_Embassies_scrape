import scrapy
from urllib.parse import urlencode
import os
from dotenv import load_dotenv
import logging


load_dotenv()
API_KEY = os.getenv("API_KEY")


def get_proxy_url(url):
    payload = {"api_key": API_KEY, "url": url}
    return f"https://proxy.scrapeops.io/v1/?{urlencode(payload)}"


class MySpiderSpider(scrapy.Spider):
    name = "my_spider"
    allowed_domains = ["ireland.ie"]
    start_urls = [
        get_proxy_url("https://www.ireland.ie/en/"),
        get_proxy_url("https://www.ireland.ie/en/dfa/embassies/"),
    ]
    # custom_settings = {
    #     "OFFSITE_ENABLED": False,
    # }

    def _assign_emb(self, item) -> bool:
        return not item.css('div.rich-text p:contains("We do not have an Embassy")')

    def _get_website(self, item) -> str:
        if child:=item.css('b:contains("Embassy Website")'):
            # print( f"https://www.ireland.ie{child.xpath("./parent::a/@href").get()}")
            return f"https://www.ireland.ie{child.xpath("./parent::a/@href").get()}"

    def _get_tel_list(self, item) -> list:
        raw_tels = item.css('a[aria-label="Telephone"]::text').getall()
        return [tel.replace("Tel: ", "") for tel in raw_tels]

    def _get_addresses_list(self, item) -> list:
        address_objs = item.css("address")
        addresses = []
        for obj in address_objs:
            raw_list = obj.css("::text").getall()
            cleaned_list = [text.strip() for text in raw_list if text.strip()]
            addresses.append(", ".join(cleaned_list).replace(",,", ","))
        return addresses

    def parse_embassy(self, response):
        ambassador_name = response.css("div.story__image_margin h3::text").get()
        country = response.meta["country"]
        has_emb = response.meta["has_emb"]
        emb_website = response.meta["emb_website"]
        emb_tels = response.meta["emb_tels"]
        emb_address = response.meta["emb_address"]
        emb_addresses = response.meta["emb_addresses"]

        self.logger.debug(
            f"Parsing embassy details for {country}: Ambassador: {ambassador_name}, Website: {emb_website}"
        )

        yield {
            "country": country,
            "has_emb": has_emb,
            "ambassador": ambassador_name,
            "website": emb_website,
            "tels": emb_tels,
            "emb_address": emb_address,
            "addresses": emb_addresses,
        }

    def parse(self, response):
        self.logger.info("Parsing response")
        # self.logger.debug(response.text)

        accordions = response.css("div.accordion")
        self.logger.info(f"Found {len(accordions)} accordions")

        for accordion in accordions:
            country = accordion.css("div.accordion::attr(id)").get()
            has_emb = self._assign_emb(accordion)
            emb_website = self._get_website(accordion)
            emb_tels = self._get_tel_list(accordion)
            emb_addresses = self._get_addresses_list(accordion)
            emb_address = emb_addresses[0] if emb_addresses else None

            self.logger.debug(
                f"Country: {country}, Has Embassy: {has_emb}, Website: {emb_website}, Tels: {emb_tels}, Addresses: {emb_addresses}"
            )

            if emb_website:
                url = get_proxy_url(emb_website)

                self.logger.debug(f"Making request for {country} to URL: {url}")

                yield response.follow(
                    url,
                    callback=self.parse_embassy,
                    meta={
                        "country": country,
                        "has_emb": has_emb,
                        "emb_website": emb_website,
                        "emb_tels": emb_tels,
                        "emb_address": emb_address,
                        "emb_addresses": emb_addresses,
                    },
                )
            else:
                self.logger.debug(
                    f"Yielding data for {country} without further request"
                )

            yield {
                "country": country,
                "has_emb": has_emb,
                "ambassador": None,
                "website": emb_website,
                "tels": emb_tels,
                "emb_address": emb_address,
                "addresses": emb_addresses,
            }


# import scrapy
# from urllib.parse import urlencode
# import os
# from dotenv import load_dotenv
# import logging


# load_dotenv()
# API_KEY = os.getenv("API_KEY")


# def get_proxy_url(url):
#     payload = {"api_key": API_KEY, "url": url}
#     return f"https://proxy.scrapeops.io/v1/?{urlencode(payload)}"


# class MySpiderSpider(scrapy.Spider):
#     name = "my_spider"
#     allowed_domains = ["ireland.ie"]
#     start_urls = [get_proxy_url("https://www.ireland.ie/en/dfa/embassies/")]
#     custom_settings = {
#         "OFFSITE_ENABLED": False,
#     }

#     def _assign_emb(self, item) -> bool:
#         return not item.css('div.rich-text p:contains("We do not have an Embassy")')

#     def _get_website(self, item) -> str:
#         child = item.css('b:contains("Embassy Website")')
#         return child.xpath("./parent::a/@href").get()

#     def _get_tel_list(self, item) -> list:
#         raw_tels = item.css('a[aria-label="Telephone"]::text').getall()
#         return [tel.replace("Tel: ", "") for tel in raw_tels]

#     def _get_addresses_list(self, item) -> list:
#         address_objs = item.css("address")
#         addresses = []
#         for obj in address_objs:
#             raw_list = obj.css("::text").getall()
#             cleaned_list = [text.strip() for text in raw_list if text.strip()]
#             addresses.append(", ".join(cleaned_list).replace(",,", ","))
#         return addresses

#     def parse_embassy(self, response):
#         ambassador_name = response.css("div.story__image_margin h3::text").get()
#         # Retrieve the meta information passed from the previous request
#         country = response.meta["country"]
#         has_emb = response.meta["has_emb"]
#         emb_website = response.meta["emb_website"]
#         emb_tels = response.meta["emb_tels"]
#         emb_address = response.meta["emb_address"]
#         emb_addresses = response.meta["emb_addresses"]
#         # Yield the final item
#         yield {
#             "country": country,
#             "has_emb": has_emb,
#             "ambassador": ambassador_name,
#             "website": emb_website,
#             "tels": emb_tels,
#             "emb_address": emb_address,
#             "addresses": emb_addresses,
#         }

#     def parse(self, response):
#         self.logger.info("Parsing response")
#         self.logger.debug(response.text)

#         accordions = response.css("div.accordion")
#         self.logger.info(f"Found {len(accordions)} accordions")

#         for accordion in accordions:
#             country = accordion.css("div.accordion::attr(id)").get()
#             has_emb = self._assign_emb(accordion)
#             emb_website = self._get_website(accordion)
#             emb_tels = self._get_tel_list(accordion)
#             emb_addresses = self._get_addresses_list(accordion)
#             emb_address = emb_addresses[0] if emb_addresses else None

#             self.logger.debug(
#                 f"Country: {country}, Has Embassy: {has_emb}, Website: {emb_website}, Tels: {emb_tels}, Addresses: {emb_addresses}"
#             )

#             if emb_website:
#                 url = get_proxy_url(f"https://www.ireland.ie/en/dfa/{emb_website}")

#                 yield scrapy.Request(
#                     url,
#                     callback=self.parse_embassy,
#                     meta={
#                         "country": country,
#                         "has_emb": has_emb,
#                         "emb_website": emb_website,
#                         "emb_tels": emb_tels,
#                         "emb_address": emb_address,
#                         "emb_addresses": emb_addresses,
#                     },
#                 )
#             else:
#                 yield {
#                     "country": country,
#                     "has_emb": has_emb,
#                     "ambassador": None,
#                     "website": emb_website,
#                     "tels": emb_tels,
#                     "emb_address": emb_address,
#                     "addresses": emb_addresses,
#                 }

#     def errback(self, failure):
#         self.logger.error(repr(failure))

#         # In case the error happens when following a request to an embassy page, we retrieve the meta information
#         request = failure.request
#         if request.meta:
#             yield {
#                 "country": request.meta.get("country"),
#                 "has_emb": request.meta.get("has_emb"),
#                 "ambassador": None,
#                 "website": request.meta.get("emb_website"),
#                 "tels": request.meta.get("emb_tels"),
#                 "emb_address": request.meta.get("emb_address"),
#                 "addresses": request.meta.get("emb_addresses"),
#             }
# import scrapy
# from urllib.parse import urlencode
# import os
# from dotenv import load_dotenv
# import logging

# load_dotenv()
# API_KEY = os.getenv("API_KEY")


# def get_proxy_url(url):
#     payload = {"api_key": API_KEY, "url": url}
#     return f"https://proxy.scrapeops.io/v1/?{urlencode(payload)}"


# class MySpiderSpider(scrapy.Spider):
#     name = "my_spider"
#     allowed_domains = ["ireland.ie"]
#     start_urls = [
#         get_proxy_url("https://www.ireland.ie/en/dfa/embassies/"),
#         get_proxy_url("https://www.ireland.ie/en/"),
#     ]
#     custom_settings = {
#         "OFFSITE_ENABLED": False,
#     }

#     def _assign_emb(self, item) -> bool:
#         return not item.css('div.rich-text p:contains("We do not have an Embassy")')

#     def _get_website(self, item) -> str:
#         child = item.css('b:contains("Embassy Website")')
#         return child.xpath("./parent::a/@href").get()

#     def _get_tel_list(self, item) -> list:
#         raw_tels = item.css('a[aria-label="Telephone"]::text').getall()
#         return [tel.replace("Tel: ", "") for tel in raw_tels]

#     def _get_addresses_list(self, item) -> list:
#         address_objs = item.css("address")
#         addresses = []
#         for obj in address_objs:
#             raw_list = obj.css("::text").getall()
#             cleaned_list = [text.strip() for text in raw_list if text.strip()]
#             addresses.append(", ".join(cleaned_list).replace(",,", ","))
#         return addresses

#     def parse_embassy(self, response):
#         ambassador_name = response.css("div.story__image_margin h3::text").get()
#         country = response.meta["country"]
#         has_emb = response.meta["has_emb"]
#         emb_website = response.meta["emb_website"]
#         emb_tels = response.meta["emb_tels"]
#         emb_address = response.meta["emb_address"]
#         emb_addresses = response.meta["emb_addresses"]

#         self.logger.debug(
#             f"Scraped Embassy: {country}, Ambassador: {ambassador_name}, Website: {emb_website}, Tels: {emb_tels}, Addresses: {emb_addresses}"
#         )

#         yield {
#             "country": country,
#             "has_emb": has_emb,
#             "ambassador": ambassador_name,
#             "website": emb_website,
#             "tels": emb_tels,
#             "emb_address": emb_address,
#             "addresses": emb_addresses,
#         }

#     def parse(self, response):
#         self.logger.info("Parsing response")
#         accordions = response.css("div.accordion")
#         self.logger.info(f"Found {len(accordions)} accordions")

#         for accordion in accordions:
#             country = accordion.css("div.accordion::attr(id)").get()
#             has_emb = self._assign_emb(accordion)
#             emb_website = self._get_website(accordion)
#             emb_tels = self._get_tel_list(accordion)
#             emb_addresses = self._get_addresses_list(accordion)
#             emb_address = emb_addresses[0] if emb_addresses else None

#             self.logger.debug(
#                 f"Country: {country}, Has Embassy: {has_emb}, Website: {emb_website}, Tels: {emb_tels}, Addresses: {emb_addresses}"
#             )

#             if emb_website:
#                 url = get_proxy_url(f"https://www.ireland.ie/en/dfa/{emb_website}")

#                 yield scrapy.Request(
#                     url,
#                     callback=self.parse_embassy,
#                     meta={
#                         "country": country,
#                         "has_emb": has_emb,
#                         "emb_website": emb_website,
#                         "emb_tels": emb_tels,
#                         "emb_address": emb_address,
#                         "emb_addresses": emb_addresses,
#                     },
#                 )
#             else:
#                 self.logger.debug(f"Yielding non-embassy item for country: {country}")
#                 yield {
#                     "country": country,
#                     "has_emb": has_emb,
#                     "ambassador": None,
#                     "website": emb_website,
#                     "tels": emb_tels,
#                     "emb_address": emb_address,
#                     "addresses": emb_addresses,
#                 }
