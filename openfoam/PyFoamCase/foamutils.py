from nextlib.openfoam.PyFoamCase.utils.tokenize import TokenizeUtil
from nextlib.openfoam.PyFoamCase.utils.extract import ExtractUtil
from nextlib.openfoam.PyFoamCase.utils.getdata import GetDataUtil
from nextlib.openfoam.PyFoamCase.utils.changedata import ChangeDataUtil
from nextlib.openfoam.PyFoamCase.utils.insertdata import InsertDataUtil
from nextlib.openfoam.PyFoamCase.header.nodebuilder import NodeBuilder


class FoamUtils:
    def __init__(self):
        self.raw_data = ''
        self.extract_data = {}

        self.tokenizeutil = TokenizeUtil()
        self.extractutil = ExtractUtil()
        self.getdatautil = GetDataUtil()
        self.changedatautil = ChangeDataUtil()
        self.insertdatautil = InsertDataUtil()

    def build(self, raw_data: str):
        self.raw_data = raw_data

        token_data = self.tokenizeutil.tokenize(raw_data)
        self.extract_data, _ = self.extractutil.extract(token_data)

        builder = NodeBuilder(raw_data)
        root_node = builder.build(self.extract_data)

        self.root_node = root_node

        lines = self.bind(self.raw_data)
        self.getdatautil.get_bind(lines, root_node)
        self.changedatautil.get_bind(lines, root_node)
        self.insertdatautil.get_bind(lines, root_node)

    def bind(self, raw_text: str):
        return raw_text.splitlines(keepends=False)

    def rebuild(self, raw_data: str):
        self.build(raw_data)

    def to_text(self):
        if self.changedatautil is None:
            return self.raw_data
        return self.changedatautil.to_text()

    # GetDataUtil
    def has_key(self, route: str):
        return self.getdatautil.has_key(self.extract_data, route)

    def get_value(self, route: str,
                  show_type: str = "auto", map_key: str | None = None
    ):
        return self.getdatautil.get_value(
            self.extract_data, route, show_type=show_type, map_key=map_key)

    def get_key_list(self, route: str = ''):
        return self.getdatautil.get_key_list(self.extract_data, route)

    def get_key_name_list(self, route: str = ''):
        return self.getdatautil.get_key_name_list(self.extract_data, route)

    # ChangeDataUtil
    def rename(self, route: str, new_name: str):
        if self.changedatautil is None:
            return False
        return self.changedatautil.rename(route, new_name)

    def set_value(self, route: str, new_value,
                  show_type="auto", map_key: str | None = None,
                  before_key: str | None = None,
                  after_key: str | None = None,
                  position: str | None = None):
        if self.has_key(route):
            result = self.changedatautil.change_value(
                route,
                new_value,
                show_type,
                map_key,
            )
        else:
            result = self.insertdatautil.insert_value(
                route,
                new_value,
                show_type,
                before_key=before_key,
                after_key=after_key,
                position=position,
            )
        return result

    # Remove
    def remove(self, route):
        return self.changedatautil.remove(route)

    # Clear dictionary contents
    def clear(self, route):
        """Clear dictionary contents while keeping the dictionary structure"""
        return self.changedatautil.clear(route)

    # Insert
    def insert_value(self, route: str, value,
                     show_type="auto",
                     before_key=None,
                     after_key=None,
                     position=None):
        if (
                "[" not in route
                and isinstance(value, dict)
                and self.has_key(route)
                and isinstance(self.get_value(route), list)
        ):
            return self.insertdatautil.insert_list_item(route, value)

        return self.insertdatautil.insert_value(
            route,
            value,
            show_type=show_type,
            before_key=before_key,
            after_key=after_key,
            position=position,
        )

    def insert_list_item(self, route: str, item: dict):
        return self.insertdatautil.insert_list_item(route, item)
