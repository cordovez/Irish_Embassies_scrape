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
        'FEED_FORMAT': 'json',
        'FEED_URI': 'embassies.json',
        'FEED_EXPORT_INDENT': 4,
    }

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

    def _get_website(self, item, phrase: str) -> str:
        if item.css('a:attr(href):contains("https://www.ireland.ie/en/")'):
            return item.css('a:attr(href)').get()
        elif child := item.css(f'b:contains("{phrase}")'):
            return f"https://www.ireland.ie{child.xpath("./parent::a/@href").get()}"
        elif child := item.css('a:contains("Representation website")'):
            return f"https://www.ireland.ie{child.xpath("./@href").get()}"

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
                for keyword in ["Representation", "Mission", "Partnership"]
            ):
                countries.append(div)

        return countries

    def _populate_country(self, item) -> dict:
        def _assign_emb(item) -> bool:
            return not item.css('div.rich-text p:contains("We do not have an Embassy")')

        return {
            "type": "country",
            "country_name": item.css("::attr(id)").get(),
            "has_emb": _assign_emb(item),
            "head_of_mission": "",
            "emb_address": self._get_address(item),
            "emb_tel": self._get_tel(item),
            "emb_website": self._get_website(item, "Embassy Website"),
            "consulates": self._get_consulates(item),
        }

    def _get_missions(self, divs):
        return [
            mission
            for mission in divs
            if "Permanent Mission" in mission.css("::attr(id)").get()
        ]

    def _populate_mission(self, item) -> dict[str:str]:
        return {
            "type": "mission",
            "mission_name": item.css("h3::text").get(),
            "head_of_mission": "",
            "emb_address": self._get_address(item),
            "emb_tel": self._get_tel(item),
            "emb_website": self._get_website(item, "Mission Website"),
        }

    def _get_perm_reps(self, divs):
        return [
            perm_rep
            for perm_rep in divs
            if "Permanent Representation" in perm_rep.css("::attr(id)").get()
        ]

    def _populate_perm_reps(self, item):
        return {
            "type": "permanent representation",
            "perm_rep_name": item.css("h3::text").get(),
            "head_of_mission": "",
            "perm_rep_address": self._get_address(item),
            "perm_rep_tel": self._get_tel(item),
            "perm_rep_website": self._get_website(item, "Representation Website"),
        }

    def _get_partnerships(self, divs):
        return [
            partner
            for partner in divs
            if "Partnership" in partner.css("::attr(id)").get()
        ]

    def _populate_partnerships(self, item):
        return {
            "type": "partnership",
            "partnership_name": item.css("span.embassy_accordion__title::text")
            .get()
            .strip(),
            "partnership_address": self._get_address(item),
            "partnership_tel": self._get_tel(item),
            "partnership_website": item.css("div.rich-text a::attr(href)").get(),
        }

    def _get_consulates(self, country) -> list:
        consulates = []
        child_divs = country.css('h3:contains("Consulate General of Ireland,")')
        for parent in child_divs:
            consulate = parent.xpath('./ancestor::div[1]')
            consulates.append({
                "consulate_name": consulate.css('h3::text').get(),
                "head_of_mission": ""
                "consulate_address": self._get_address(consulate),
                "consulate_tel": self._get_tel(consulate),
                "consulate_website": self._get_website(consulate, "Consulate Website"),
            })
        return consulates
        

    def parse(self, response):
        # sourcery skip: inline-immediately-yielded-variable

        accordions = response.css("div.accordion")
        countries = self._get_countries(accordions)
        missions = self._get_missions(accordions)
        perm_reps = self._get_perm_reps(accordions)
        partners = self._get_partnerships(accordions)

        for country in countries:
            country_data = self._populate_country(country)
            if country_data['emb_website']:
                request = scrapy.Request(
                    country_data['emb_website'],
                    callback=self.parse_mission_website,
                    cb_kwargs={'country_data': country_data}
                )
                yield request
            else:
                yield country_data
        
        # for country in countries:
        #     yield self._populate_country(country)

        for mission in missions:
            yield self._populate_mission(mission)

        for rep in perm_reps:
            rep_data = self._populate_perm_reps(rep)
            if rep_data["perm_rep_website"]:
                request = scrapy.Request(
                    rep_data["perm_rep_website"],
                    callback=self.parse_embassy_website,
                    cb_kwargs={'country_data': rep_data}
                )
                yield request
            else:
                yield rep_data
                
        # for rep in perm_reps:
        #     yield self._populate_perm_reps(rep)

        for partner in partners:
            yield self._populate_partnerships(partner)

    # def parse_embassy_website(self, response, country_data):
    #     ambassador_name = response.css('div.story__image_margin h3::text').get()
    #     country_data['ambassador'] = ambassador_name
    #     yield country_data
    def parse_mission_website(self, response, mission_data):
        person = response.css('div.story__image_margin h3::text').get()
        mission_data['head_of_mission'] = person
        yield mission_data
