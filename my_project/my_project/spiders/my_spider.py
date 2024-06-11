""" 
This spider scrapes a page that does not necessarily have good class names. It is possible that it is evolving, so all the logic for finding and cleaning the text is exposed in the private class methods I created in the spider
"""

import scrapy
from urllib.parse import urlencode
import os
from dotenv import load_dotenv
from scrapy.selector import Selector, SelectorList

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

    # def _get_name(self, div):
    #     return div.css("::attr(id)").get()

    def _get_text_for(self, div: Selector, css_selector: str):
        """Returns the text content of the specified selector within the provided div element."""
        return div.css(f"{css_selector}").get()

    def _get_address(self, div: Selector) -> str:
        """Returns the cleaned address extracted from the provided div element."""
        if addresses := div.css("address"):
            first_address = addresses[0]
            raw_address = first_address.css("address::text").getall()
            return ", ".join([line.strip() for line in raw_address if line.strip()])
        return ""

    def _get_website(self, div: Selector) -> str:
        """Returns the website URL extracted from the provided div element based on predefined phrases."""

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
            if child := div.css(f'b:contains("{phrase}")'):
                href = child.xpath("./parent::a/@href").get()
                return clean_url(href)
            if child := div.css(f'a:contains("{phrase}")'):
                href = child.xpath("./@href").get()
                return clean_url(href)

        return ""

    def _get_tel(self, div: Selector) -> str:
        """Returns the telephone number extracted from the provided div element."""
        if div.css('a[aria-label="Telephone"]::text').get():
            raw_tel = div.css('a[aria-label="Telephone"]::text').get()
            return raw_tel.replace("Tel: ", "")
        else:
            return ""

    def _get_countries(self, divs: SelectorList) -> list:
        """Returns a list of Scrapy Selector elements representing countries based on specified keywords in their ID attributes."""
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

    def _get_others(self, divs: SelectorList) -> list[Selector]:
        """Returns a list of Scrapy Selector elements representing items other than countries or embassies, based on specified keywords in their ID attributes."""

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

    def _get_embassies(self, divs: SelectorList) -> list[Selector]:
        """Returns a list of Scrapy Selector elements representing embassies based on the absence of a specific substring in their text content."""

        embassies = []
        sub_str = "We do not have an Embassy in this country"
        for div in divs:
            text_blocks = div.css("div.accordion ::text").getall()
            full_text = " ".join(text_blocks)
            if sub_str not in full_text:
                embassies.append(div)
        return embassies

    def _get_consulates(self, embassy_div: Selector) -> list[Selector]:
        """Returns a list of Scrapy Selector elements representing consulates associated with the provided embassy div."""

        consulates_divs = []
        city = ""

        def get_city_ids(consulates: list[Selector]) -> list[Selector]:
            """Extracts and returns a list of city IDs from the provided list of consulate Selector elements."""
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

        consulate_markers = embassy_div.css(
            'h3:contains("Consulate General of Ireland, ")'
        )

        city_ids = get_city_ids(consulate_markers)

        for city in city_ids:
            consulates_divs.extend(embassy_div.css(f"div[id={city}]"))

        return consulates_divs

    def _assign_emb(self, div: Selector) -> bool:
        """Checks if the provided div element contains the text "We do not have an Embassy".

        Returns:
            bool: True if the text is not found, False otherwise.
        """

        return not div.css('div.rich-text p:contains("We do not have an Embassy")')

    def _covering_mission(self, div: Selector) -> str:
        """Determines and returns the mission information extracted from the provided div element."""
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

    def _get_kw_values_for(self, category_type: str, div: Selector) -> MissionInfos:
        """Returns a category object with specific key-value pairs extracted from the provided div element."""
        category = MissionInfos()
        category["type_of"] = category_type
        category["name"] = self._get_text_for(div, "::attr(id)")
        category["head_of_mission"] = ""
        category["address"] = self._get_address(div).replace(",,", ",")
        category["tel"] = self._get_tel(div)
        category["website"] = self._get_website(div)

        return category

    def _populate_country(self, div: Selector) -> Country:
        """Populates and yields a Country object with information extracted from the provided div element."""
        country = Country()
        country["type_of"] = "country"
        country["name"] = self._get_text_for(div, "::attr(id)")
        country["is_represented"] = self._assign_emb(div)
        country["covered_by"] = self._covering_mission(div)

        yield country

    def _populate_other(self, div: Selector) -> MissionInfos:
        """Populates and yields an "other" category object with information extracted from the provided div element."""

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

    def _populate_embassy(self, div: Selector) -> MissionInfos:
        """Populates and yields embassy and consulate objects extracted from the provided div element."""
        embassy = self._get_kw_values_for("embassy", div)
        consulates_divs = self._get_consulates(div)
        consulate_items = []

        for consulate_div in consulates_divs:
            consulate_item = self._get_kw_values_for("consulate", consulate_div)
            consulate_items.append(consulate_item)

        embassy["consulates"] = consulate_items

        if "https://www.ireland.ie/" in embassy["website"]:
            yield scrapy.Request(
                embassy["website"],
                callback=self.parse_mission_website,
                cb_kwargs={"mission_item": embassy},
            )

        if embassy["consulates"]:
            for consulate in embassy["consulates"]:
                if "https://www.ireland.ie/" in consulate["website"]:
                    yield scrapy.Request(
                        consulate["website"],
                        callback=self.parse_mission_website,
                        cb_kwargs={
                            "mission_item": consulate,
                        },
                    )
                else:
                    yield consulate_item
        else:
            yield embassy

    def parse(self, response):
        accordions = response.css(
            "div.accordion"
        )  # countries are grouped in dropdown menus with class = accordion
        countries = self._get_countries(accordions)
        others = self._get_others(accordions)
        embassies = self._get_embassies(countries)

        for country in countries:
            yield from self._populate_country(country)

        for other in others:
            yield from self._populate_other(other)

        for embassy in embassies:
            yield from self._populate_embassy(embassy)

    def parse_mission_website(self, response, mission_item):
        """Parses the mission website response to extract the head of mission information and update the mission item."""
        try:
            person = response.css("div.story__image_margin h3::text").get()
            mission_item["head_of_mission"] = person
        except Exception as e:
            self.logger.error(
                f"Failed to parse website for {mission_item['name']}: {e}"
            )
        finally:
            yield mission_item
