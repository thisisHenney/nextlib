from nextlib.openfoam.PyFoamCase.header.index import (
    BLOCKS_INDEX_MAP, REGIONS_INDEX_MAP
)

class GetDataUtil:
    def __init__(self):
        pass

    def get_bind(self, lines, root_node):
        self.lines = lines
        self.root_node = root_node

    def _find_node(self, node, route: str):
        if not route:
            return node

        cur = node
        for part in route.split("."):
            if "[" in part and part.endswith("]"):
                key, idx = part[:-1].split("[", 1)
                idx = int(idx)

                lst = cur.child_map.get(key)
                if not lst or idx < 0 or idx >= len(lst):
                    return None
                cur = lst[idx]
            else:
                lst = cur.child_map.get(part)
                if not lst:
                    return None
                cur = lst[0]

        return cur

    def _resolve(self, data, route: str):
        if not route:
            return data

        cur = data
        for part in route.split("."):
            if "[" in part and part.endswith("]"):
                key, idx = part[:-1].split("[", 1)
                cur = cur.get(key) if isinstance(cur, dict) else None
                if not isinstance(cur, list):
                    return None
                i = int(idx)
                if i < 0 or i >= len(cur):
                    return None
                cur = cur[i]
            else:
                if isinstance(cur, list):
                    found = None
                    for item in cur:
                        if isinstance(item, dict) and part in item:
                            found = item[part]
                            break
                    cur = found
                elif isinstance(cur, dict):
                    if part in cur:
                        cur = cur.get(part)
                    else:
                        if len(cur) == 1:
                            only_val = next(iter(cur.values()))
                            if isinstance(only_val, dict) and part in only_val:
                                cur = only_val.get(part)
                            else:
                                return None
                        else:
                            return None
                else:
                    return None

            if cur is None:
                return None

        return cur

    # Get
    def has_key(self, data: dict, route: str) -> bool:
        return self._resolve(data, route) is not None

    def get_value(self, data: dict, route: str,
                  show_type: str = "auto",
                  map_key=None,
                  proxy: bool = False):

        node = None
        if hasattr(self, "root_node") and self.root_node is not None:
            node = self._find_node(self.root_node, route)

        if node is not None:
            value = node.value
        else:
            value = self._resolve(data, route)
            if value is None:
                return None

        key = self._extract_key(route)

        if key == "blocks":
            value = self._get_blocks_value(value, map_key, route)
        elif key == "inGroups":
            value = self._get_inGroups_value(value)
        elif key == "regions":
            route_index = self._extract_last_index(route)
            value = self._get_regions_value(value, map_key, route_index)
        elif key == "vertices":
            value = value
        elif show_type == "vector":
            value = self._get_vector_value(value)
        else:
            value = self._get_default_value(value, map_key)
        return value

    def _extract_key(self, route: str | None):
        if not route:
            return None
        key = route.split(".")[-1]
        if "[" in key:
            key = key.split("[")[0]
        return key

    def _strip_inline_comment(self, v):
        if isinstance(v, str):
            if "//" in v:
                return v.split("//", 1)[0].strip()
        return v

    def _get_blocks_value(self, value, map_key, route: str | None = None):
        if route:
            idx_route = self._extract_last_index(route)
            if idx_route is not None and isinstance(value, list) and value and isinstance(value[0], list):
                if idx_route is not None and 0 <= idx_route < len(value):
                    value = value[idx_route]
                else:
                    return None

        if map_key is None:
            return value

        idx = BLOCKS_INDEX_MAP.get(map_key)
        if idx is None:
            return None

        if isinstance(value, list) and value and isinstance(value[0], list):
            out = []
            for b in value:
                if not isinstance(b, list):
                    continue
                if idx >= len(b):
                    continue
                out.append(self._strip_inline_comment(b[idx]))
            return out

        if isinstance(value, list):
            if idx < len(value):
                return self._strip_inline_comment(value[idx])
            return None

        return None

    def _get_inGroups_value(self, value):
        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            if "values" in value and isinstance(value["values"], list):
                return value["values"]

        if isinstance(value, str):
            l = value.find("(")
            r = value.find(")", l + 1)
            if l != -1 and r != -1:
                inner = value[l + 1: r].strip()
                if inner:
                    return inner.split()
                return []

        return None

    def _get_regions_value(self, value, map_key, route_index: int | None):
        if route_index is not None and isinstance(value, list) and value and isinstance(value[0], list):
            if 0 <= route_index < len(value):
                value = value[route_index]
            else:
                return None

        if map_key is None:
            return value

        idx = REGIONS_INDEX_MAP.get(map_key)
        if idx is None:
            return None

        if isinstance(value, list) and value and isinstance(value[0], list):
            return [r[idx] for r in value if isinstance(r, list) and idx < len(r)]

        if isinstance(value, list):
            return value[idx] if idx < len(value) else None

        return None

    def _get_vector_value(self, value):
        if (
                isinstance(value, list)
                and len(value) >= 2
                and all(isinstance(v, (int, float)) for v in value)
        ):
            return value
        return None

    def _get_default_value(self, value, map_key):
        if map_key is None:
            return value

        if isinstance(value, dict):
            return value.get(map_key)

        if isinstance(value, list):
            return [item[map_key] for item in value if isinstance(item, dict) and map_key in item]

        return None

    def get_key_list(self, data: dict, route: str = ''):
        target = self._resolve(data, route)
        if isinstance(target, dict):
            return list(target.keys())
        return []

    def get_key_name_list(self, data: dict, route: str = ''):
        target = self._resolve(data, route)
        if isinstance(target, dict):
            return list(target.keys())
        return []

    def _extract_last_index(self, route: str):
        if not route:
            return None
        last = route.split(".")[-1]
        if "[" in last and last.endswith("]"):
            try:
                return int(last.split("[", 1)[1][:-1])
            except ValueError:
                return None
        return None





