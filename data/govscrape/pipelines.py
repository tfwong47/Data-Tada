# govscrape/govscrape/pipelines.py
from scrapy.exceptions import DropItem

class DropEmptyDataTypesPipeline:
    def process_item(self, item, spider):
        s = (item.get("data_types") or "").strip()
        if not s:
            raise DropItem("Dropped: empty data_types")
        return item
