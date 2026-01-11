from city_scrapers.mixins.colgo_skamania import SkamaniaCountyMixin

_location = {
    "name": "Skamania County Courthouse",
    "address": "240 NW Vancouver Ave., Stevenson, WA 98648",
}

spider_configs = [
    {
        "class_name": "SkamaniaBoccSpider",
        "name": "colgo_ska_bocc",
        "agency": "Board of County Commissioners",
        "agenda_param": "agendas-minutes-meeting-audio/-folder-36#docfold_2924_1241_328_36", # noqa
        "location": _location,
    },
    {
        "class_name": "SkamaniaBohSpider",
        "name": "colgo_ska_boh",
        "agency": "Board of Health",
        "agenda_param": "board-of-health/-folder-162#docfold_2001_2047_350_162",
        "location": _location,
    },
    {
        "class_name": "SkamaniaEmsbSpider",
        "name": "colgo_ska_emsb",
        "agency": "Board of EMS District #1",
        "agenda_param": "board-of-ems-district-1/-folder-619#docfold_2001_3132_1205_619", # noqa
        "location": _location,
    },
]


def create_spiders():
    """
    Dynamically create spider classes using the spider_configs list
    and register them in the global namespace.
    """
    for config in spider_configs:
        class_name = config["class_name"]

        if class_name not in globals():
            # Build attributes dict without class_name to avoid duplication.
            # We make sure that the class_name is not already in the global namespace
            # Because some scrapy CLI commands like `scrapy list` will inadvertently
            # declare the spider class more than once otherwise
            attrs = {k: v for k, v in config.items() if k != "class_name"}

            # Dynamically create the spider class
            spider_class = type(
                class_name,
                (SkamaniaCountyMixin,),
                attrs,
            )

            # Register the class in the global namespace using its class_name
            globals()[class_name] = spider_class


# Create all spider classes at module load
create_spiders()
