# govscrape/govscrape/items.py
import scrapy

class PageItem(scrapy.Item):
    url = scrapy.Field()
    status = scrapy.Field()
    title = scrapy.Field()
    description = scrapy.Field()
    body_html = scrapy.Field()        # extracted main-body HTML (string)
    file_links = scrapy.Field()       # list of absolute URLs found in body
    file_types = scrapy.Field()       # unique set/list of extensions (e.g., ['.csv', '.pdf'])
