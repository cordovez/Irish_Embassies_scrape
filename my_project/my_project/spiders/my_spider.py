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
        "FEED_EXPORT_INDENT": 4,
    }

    def _get_name(self, item):
        return item.css("::attr(id)").get()

    def _get_address(self, item) -> str:
        if addresses := item.css("address"):
            first_address = addresses[0]
            raw_address = first_address.css("address::text").getall()
            return ", ".join([line.strip() for line in raw_address if line.strip()])
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

    def _get_others(self, divs):
        others = []
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
                others.append(div)

        return others

    def _get_embassies(self, divs):
        embassies = []
        sub_str = "We do not have an Embassy in this country"
        for div in divs:
            text_blocks = div.css("div.accordion ::text").getall()
            full_text = " ".join(text_blocks)
            if sub_str not in full_text:
                embassies.append(div)
        return embassies

    def _get_consulates(self, embassies):
        consulates_divs = []
        city = ""

        def get_city_ids(consulates: list) -> list:
            ids = []
            for consulate in consulates:
                phrase = consulate.css(
                    'h3:contains("Consulate General of Ireland, ")::text'
                ).get()

                city_id = (
                    phrase.replace("Consulate General of Ireland, ", "")
                    .lower()
                    .replace(" ", "")
                )
                ids.append(city_id)
            return ids

        for embassy in embassies:
            consulate_markers = embassy.css(
                'h3:contains("Consulate General of Ireland, ")'
            )

            city_ids = get_city_ids(consulate_markers)

            for city in city_ids:
                consulates_divs.append(embassy.css(f"div[id = {city}]"))

        return consulates_divs

    def _assign_emb(self, div):
        return not div.css('div.rich-text p:contains("We do not have an Embassy")')

    def _covering_mission(self, div):
        if (
            div.css('div.rich-text b:contains("Passport Office in Dublin")::text').get()
            == "Passport Office in Dublin"
        ):
            mission = "Passport Office in Dublin"
        elif div.css("div.rich-text h2"):
            mission = div.css("div.rich-text h2::text").get()
        else:
            mission = div.css("div h3::text").get()

        mission = mission.lower()

        phrases = [
            "diplomatic and consular information for ",
            "embassy of ireland, ",
        ]

        for phrase in phrases:
            if phrase in mission:
                mission = mission.replace(phrase, "")

        return mission.title()

    def _get_kw_values_for(self, category_type: str, div):
        category = MissionInfos()
        category["type_of"] = category_type
        category["name"] = self._get_name(div)
        category["head_of_mission"] = ""
        category["address"] = self._get_address(div).replace(",,", ",")
        category["tel"] = self._get_tel(div)
        category["website"] = self._get_website(div)

        return category

    def _populate_country(self, div):
        country = Country()
        country["type_of"] = "country"
        country["name"] = div.css("::attr(id)").get()
        country["is_represented"] = self._assign_emb(div)
        country["covered_by"] = self._covering_mission(div)

        yield country

    def _populate_other(self, div):
        other = self._get_kw_values_for("other", div)

        # some websites may not be hosted by ireland.ie
        if "https://www.ireland.ie/" in other["website"]:
            yield scrapy.Request(
                other["website"],
                callback=self.parse_mission_website,
                cb_kwargs={"mission_item": other},
            )

        else:
            yield other

    def _populate_embassy(self, div):
        embassy = self._get_kw_values_for("embassy", div)

        if "https://www.ireland.ie/" in embassy["website"]:
            yield scrapy.Request(
                embassy["website"],
                callback=self.parse_mission_website,
                cb_kwargs={"mission_item": embassy},
            )

        else:
            yield embassy

    def _populate_consulate(self, div):
        consulate = self._get_kw_values_for("consulate", div)

        if "https://www.ireland.ie/" in consulate["website"]:
            yield scrapy.Request(
                consulate["website"],
                callback=self.parse_mission_website,
                cb_kwargs={"mission_item": consulate},
            )

        else:
            yield consulate

    def parse(self, response):
        # sourcery skip: inline-immediately-yielded-variable
        accordions = response.css("div.accordion")
        countries = self._get_countries(accordions)
        others = self._get_others(accordions)
        embassies = self._get_embassies(countries)
        consulates = self._get_consulates(embassies)

        for country in countries:
            yield from self._populate_country(country)

        for other in others:
            yield from self._populate_other(other)

        for embassy in embassies:
            yield from self._populate_embassy(embassy)

        for consulate in consulates:
            yield from self._populate_consulate(consulate)

    def parse_mission_website(self, response, mission_item):
        try:
            person = response.css("div.story__image_margin h3::text").get()
            mission_item["head_of_mission"] = person
        except Exception as e:
            self.logger.error(
                f"Failed to parse website for {mission_item['name']}: {e}"
            )
        finally:
            yield mission_item
