import os
import importlib
import inspect

# Explicitly import base classes to avoid circular imports
from .base import BaseScraper
from .scrapy import ScrapyBasedScraper, BaseSpider

# Get the directory of the current file
current_dir = os.path.dirname(os.path.abspath(__file__))

# Initialize a dictionary to store all exported items
all_exports = {
    "BaseScraper": BaseScraper,
    "ScrapyBasedScraper": ScrapyBasedScraper,
    "BaseSpider": BaseSpider,
}

# Iterate through all Python files in the current directory
for filename in os.listdir(current_dir):
    if filename.endswith(".py") and filename not in [
        "__init__.py",
        "base.py",
        "scrapy.py",
    ]:
        module_name = filename[:-3]  # Remove the .py extension
        module = importlib.import_module(f".{module_name}", package=__package__)

        # Find all classes in the module
        for name, obj in module.__dict__.items():
            if inspect.isclass(obj) and obj.__module__ == module.__name__:
                all_exports[name] = obj
                globals()[name] = obj

# Set __all__ to the list of all exported names
__all__ = list(all_exports.keys())

# Make sure BaseScraper and BaseSpider are available at the package level
globals()["BaseScraper"] = BaseScraper
globals()["BaseSpider"] = BaseSpider
