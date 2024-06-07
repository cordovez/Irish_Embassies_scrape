# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class MissionInfos(scrapy.Item):
    type_of = scrapy.Field()
    name = scrapy.Field()
    head_of_mission = scrapy.Field()
    address = scrapy.Field()
    tel = scrapy.Field()
    website = scrapy.Field()
    consulates = scrapy.Field()


class Country(scrapy.Item):
    type_of = scrapy.Field()
    name = scrapy.Field()
    is_represented = scrapy.Field()
    covered_by = scrapy.Field()


class Accordion(scrapy.Item):
    type_of = scrapy.Field()
    name = scrapy.Field()
    is_represented = scrapy.Field()
    covered_by = scrapy.Field()
    mission = scrapy.Field()
    head_of_mission = scrapy.Field()
    address = scrapy.Field()
    tel = scrapy.Field()
    website = scrapy.Field()
    consulates = scrapy.Field()
