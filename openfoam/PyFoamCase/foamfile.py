from pathlib import Path
from nextlib.openfoam.PyFoamCase.foamutils import FoamUtils


class FoamFile:
    def __init__(self, path: str | None = None):
        self.path: Path | None = Path(path) if path else None
        self.utils = FoamUtils()
        self._loaded = False

    def is_loaded(self):
        return self._loaded

    def load(self, path: str | None = None):
        if path:
            self.path = Path(path)

        if self.path is None or not self.path.is_file():
            return False

        raw_text = self.path.read_text(encoding="utf-8")
        self.utils.build(raw_text)
        self._loaded = True
        return True

    def save(self):
        if not self._loaded or self.path is None:
            return False

        text = self.utils.to_text()
        self.path.write_text(text, encoding="utf-8")
        return True

    def reload(self):
        if not self._loaded:
            return False

        text = self.utils.to_text()
        self.utils.rebuild(text)
        return True

    # Get
    def has_key(self, route: str):
        return self.utils.has_key(route)

    def get_value(
        self,
        route: str,
        show_type: str = "auto",
        map_key: str | None = None,
    ):
        return self.utils.get_value(
            route,
            show_type=show_type,
            map_key=map_key,
        )

    def get_key_list(self, route: str = ''):
        return self.utils.get_key_list(route)

    def get_key_name_list(self, route: str = ''):
        return self.utils.get_key_name_list(route)

    # Set
    def rename(self, route: str, new_name: str):
        self.utils.changedatautil.begin()
        result = self.utils.rename(route, new_name)
        self.utils.changedatautil.end()
        if result:
            self.reload()
        return result

    def set_value(self, route, new_value, show_type="auto", map_key=None):
        self.utils.changedatautil.begin()
        result = self.utils.set_value(route, new_value, show_type, map_key)
        self.utils.changedatautil.end()
        if result:
            self.reload()
        return result

    # Remove
    def remove(self, route):
        self.utils.changedatautil.begin()
        result = self.utils.remove(route)
        self.utils.changedatautil.end()
        if result:
            self.reload()
        return result

    # Insert
    def insert_value(self, route: str, value, show_type="auto"):
        self.utils.changedatautil.begin()
        result = self.utils.insert_value(route, value, show_type)
        self.utils.changedatautil.end()
        if result:
            self.reload()
        return result

    def insert_list_item(self, route: str, item: dict):
        self.utils.changedatautil.begin()
        result = self.utils.insert_list_item(route, item)
        self.utils.changedatautil.end()
        if result:
            self.reload()
        return result
