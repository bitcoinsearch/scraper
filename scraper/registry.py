from typing import Dict, Type, TypeVar

T = TypeVar("T")


class Registry:
    def __init__(self):
        self._registry: Dict[str, Type[T]] = {}

    def register(self, *names: str):
        def decorator(cls: Type[T]):
            for name in names:
                self._registry[name.lower()] = cls
            return cls

        return decorator

    def get(self, name: str) -> Type[T]:
        name = name.lower()
        if name.lower() not in self._registry:
            raise ValueError(f"Unknown type: {name}")
        return self._registry[name]

    def get_all(self):
        return list(self._registry.keys())


# Create registries for each component
output_registry = Registry()
scraper_registry = Registry()
