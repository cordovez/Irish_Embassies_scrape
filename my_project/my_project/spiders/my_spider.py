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
        get_proxy_url("https://www.ireland.ie/en/dfa/embassies/"),
    ]
    custom_settings = {
        "OFFSITE_ENABLED": False,
    }

    def _get_countries(self, divs):
        countries = []
        for div in divs:
            id_attr = div.css("::attr(id)").get()
            if not any(
                keyword in id_attr
                for keyword in ["Representation", "Mission", "Partnership"]
            ):
                countries.append(div)

        return countries

    def _populate_country(self, item) -> dict[str:str]:
        def _assign_emb(item) -> bool:
            return not item.css('div.rich-text p:contains("We do not have an Embassy")')

        def _get_website(item) -> str:
            child = item.css('b:contains("Embassy Website")')
            if child:
                return f"https://www.ireland.ie{child.xpath('./parent::a/@href').get()}"
            return ""

        def _get_tel(item) -> str:
            if item.css('a[aria-label="Telephone"]::text').get():
                raw_tel = item.css('a[aria-label="Telephone"]::text').get()
                return raw_tel.replace("Tel: ", "")
            else:
                return ""

        def _get_embassy_address(item) -> str:
            addresses = item.css("address")
            if addresses:
                first_address = addresses[0]
                raw_address = first_address.css("address::text").getall()
                return ", ".join(
                    [
                        line.strip().replace(",, ", ",")
                        for line in raw_address
                        if line.strip().replace(",, ", ",")
                    ]
                )
            return ""

        return {
            "country": item.css("::attr(id)").get(),
            "has_emb": _assign_emb(item),
            "ambassador": "",
            "emb_website": _get_website(item),
            "emb_tel": _get_tel(item),
            "emb_address": _get_embassy_address(item),
            "consulates": [],
        }

    def _get_missions(self, divs):
        return [
            mission
            for mission in divs
            if "Permanent Mission" in mission.css("::attr(id)").get()
        ]

    def _get_perm_reps(self, divs):
        return [
            perm_rep
            for perm_rep in divs
            if "Permanent Representation" in perm_rep.css("::attr(id)").get()
        ]

    def _get_partnerships(self, divs):
        return [
            partner
            for partner in divs
            if "Partnership" in partner.css("::attr(id)").get()
        ]

    def _get_consulates(self, item) -> list:
        pass

    def parse(self, response):

        accordions = response.css("div.accordion")
        countries = self._get_countries(accordions)
        # perm_reps = self._get_perm_reps(accordions)
        # missions = self._get_missions(accordions)
        # partners = self._get_partnerships(accordions)

        for country in countries:
            country_data = self._populate_country(country)

            yield country_data


# def parse_embassy(self, response):
#     ambassador_name = response.css("div.story__image_margin h3::text").get()


#     self.logger.debug(
#         f"Parsing embassy details for {response.meta["country"]}: Ambassador: {ambassador_name}, Website: {response.meta["emb_website"]}"
#     )

#     yield {
#         "country": response.meta["country"],
#         "has_emb": response.meta["has_emb"],
#         "emb_website": response.meta["emb_website"],
#         "tels": response.meta["emb_tels"],
#         "emb_address": response.meta["emb_address"],
#         "emb_addresses": response.meta["emb_addresses"],
#         "ambassador": ambassador_name,
#     }
# yield scrapy.Request(
#     url,
#     callback=self.parse_embassy,
#     meta={
#         "country": country,
#         "has_emb": has_emb,
#         "emb_website": emb_website,
#         "emb_tels": emb_tels,
#         "emb_address": emb_address,
#         "emb_addresses": emb_addresses,
#     },
# )
# else:
#     self.logger.debug(
#         f"Yielding data for {country} without further request"
#     )
