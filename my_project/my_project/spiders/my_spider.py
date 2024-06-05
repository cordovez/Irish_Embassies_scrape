import scrapy
from urllib.parse import urlencode
import os
from dotenv import load_dotenv
import logging

from my_project.items import Country, MissionInfos


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
        "FEED_FORMAT": "json",
        "FEED_URI": "embassies.json",
        "FEED_EXPORT_INDENT": 4,
    }

    def _get_name(self, item):
        return item.css("::attr(id)").get()

    def _get_address(self, item) -> str:
        if addresses := item.css("address"):
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

    def _get_website(self, item) -> str:
        def clean_url(href):
            return f"https://www.ireland.ie{href}" if "http" not in href else href

        phrases = [
            "Embassy Website",
            "Representation website",
            "Representation Website",
            "Consulate Website",
            "Partnership Website",
            "Mission Website",
        ]

        for phrase in phrases:
            if child := item.css(f'b:contains("{phrase}")'):
                href = child.xpath("./parent::a/@href").get()
                return clean_url(href)
            if child := item.css(f'a:contains("{phrase}")'):
                href = child.xpath("./@href").get()
                return clean_url(href)

        return ""

    def _get_tel(self, item) -> str:
        if item.css('a[aria-label="Telephone"]::text').get():
            raw_tel = item.css('a[aria-label="Telephone"]::text').get()
            return raw_tel.replace("Tel: ", "")
        else:
            return ""

    def _get_countries(self, divs):
        countries = []
        for div in divs:
            id_attr = div.css("::attr(id)").get()
            if not any(
                keyword in id_attr
                for keyword in [
                    "Representation",
                    "Mission",
                    "Partnership",
                    "Palestinian",
                ]
            ):
                countries.append(div)

        return countries

    def _get_embassies(self, divs):
        embassies = []
        sub_str = "We do not have an Embassy in this country"
        for div in divs:
            text_blocks = div.css("div.accordion ::text").getall()
            full_text = " ".join(text_blocks)
            if sub_str not in full_text:
                embassies.append(div)
        return embassies

    def _get_missions(self, divs):
        missions = []
        for div in divs:
            id_attr = div.css("::attr(id)").get()
            if any(
                keyword in id_attr
                for keyword in [
                    "Representation",
                    "Mission",
                    "Partnership",
                    "Palestinian",
                ]
            ):
                missions.append(div)

        return missions

    def _get_consulates(self, mission):
        consulates = []
        child_divs = self.mission.css('h3:contains("Consulate General of Ireland,")')
        for parent in child_divs:
            consulate = parent.xpath("./ancestor::div[1]")
            consulates.append(
                {
                    "type_of": "consulate",
                    "name": consulate.css("h3::text").get(),
                    "head_of_mission": "",
                    "address": self._get_address(consulate),
                    "tel": self._get_tel(consulate),
                    "website": self._get_website(consulate),
                }
            )
        return consulates

    def _assign_emb(self, item):
        return not item.css('div.rich-text p:contains("We do not have an Embassy")')

    def _populate_mission(self, div):
        mission = MissionInfos()
        mission["type_of"] = ""
        mission["name"] = self._get_name(div)
        mission["head_of_mission"] = ""
        mission["address"] = self._get_address(div)
        mission["tel"] = self._get_tel(div)
        mission["website"] = self._get_website(div)

        if mission["website"]:
            request = scrapy.Request(
                mission["website"],
                callback=self.parse_mission_website,
                cb_kwargs={"mission_item": mission},
            )
            yield request
        else:
            yield mission

        # if mission["is_represented"]:
        #     mission["consulates"] = self._get_consulates(div)
        #     for consulate in item["consulates"]:
        #         consulate["head_of_mission"] = item["head_of_mission"]
        #         request = scrapy.Request(
        #             consulate["website"],
        #             callback=self.parse_mission_website,
        #             cb_kwargs={"mission_item": consulate},
        #         )
        #         yield request

    def _populate_country(self, div):
        country = Country()
        country["type_of"] = "country"
        country["name"] = div.css("::attr(id)").get()
        country["is_represented"] = self._assign_emb(div)
        country["covered_by"] = self._get_website(div)

        yield country

    def parse(self, response):
        # sourcery skip: inline-immediately-yielded-variable
        accordions = response.css("div.accordion")
        countries = self._get_countries(accordions)
        others = self._get_missions(accordions)
        embassies = self._get_embassies(countries)

        # for div in embassies:
        #     yield from self._populate_mission(div)
        # for div in countries:
        #     yield from self._populate_country(div)

        # for div in others:
        #     yield from self._populate_mission(div)

        for div in embassies:
            yield from self._populate_mission(div)

    #
    # To do: def _get_mission_type(self, item):
    #
    #

    def parse_mission_website(self, response, mission_item):
        person = response.css("div.story__image_margin h3::text").get()
        mission_item["head_of_mission"] = person
        yield mission_item
