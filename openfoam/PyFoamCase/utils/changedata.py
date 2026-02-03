import re
from nextlib.openfoam.PyFoamCase.utils.baseutil import BaseUtil


class ChangeDataUtil(BaseUtil):
    def __init__(self):
        super().__init__()

        self.KEY_COL = 16
        self._line_cache = {}

    def get_bind(self, lines, root_node):
        self.lines = lines
        self.root_node = root_node
        self._invalidate_cache()

    def _invalidate_cache(self):
        self._line_cache.clear()
        for i, line in enumerate(self.lines):
            key = line.lstrip().split()[0] if line.strip() else None
            if key:
                self._line_cache.setdefault(key, []).append(i)

    def _find_line_start(self, key):
        if key in self._line_cache:
            return self._line_cache[key][0]
        return self._find_line_start_uncached(key)

    def to_text(self):
        return "\n".join(self.lines)

    # Remove
    def remove(self, route: str):
        if self.lines is None or self.root_node is None:
            return False

        if re.match(r"^[^\[\]]+\[\d+\]\.[^\.]+$", route):
            return self._remove_list_dict_field(route)

        if re.match(r"^[^\[\]]+\[\d+\]$", route):
            return self._remove_list_item(route)

        if "[" in route and route.endswith("]"):
            return self._remove_list_item(route)

        node = self._find_node(self.root_node, route)
        if node is None:
            return False

        start = node.line_start

        if node.block_end_line is not None:
            end = node.block_end_line + 1
        else:
            end = start + 1

        del self.lines[start:end]

        parent = node.parent
        if parent:
            parent.children = [c for c in parent.children if c is not node]

        self._normalize_after_remove(start - 1, start + 1)
        self._rebuild_node()
        self._invalidate_cache()
        return True

    def _remove_list_dict_field(self, route: str):
        m = re.match(r"^([^\[\]]+)\[(\d+)\]\.([^\.]+)$", route)
        if not m:
            return False

        list_key, idx, field = m.groups()
        idx = int(idx)

        start = self._find_line_start(list_key)
        if start is None:
            return False

        i = start
        while i < len(self.lines) and "(" not in self.lines[i]:
            i += 1
        if i >= len(self.lines):
            return False

        list_start = i

        items = []
        depth = 0
        cur_start = None

        for j in range(list_start + 1, len(self.lines)):
            line = self.lines[j]

            if "{" in line:
                cur_start = j

            if cur_start is not None:
                depth += line.count("{")
                depth -= line.count("}")

                if depth == 0:
                    items.append((cur_start, j))
                    cur_start = None

            if ")" in line and depth == 0:
                break

        if idx < 0 or idx >= len(items):
            return False

        item_start, item_end = items[idx]

        for k in range(item_start + 1, item_end):
            s = self.lines[k].lstrip()
            if s.startswith(field):
                del self.lines[k]
                self._cleanup_blank_lines()
                self._rebuild_node()
                return True

        return False

    def _remove_list_item(self, route: str):
        key, idx = route[:-1].split("[", 1)
        idx = int(idx)

        start = self._find_line_start(key)
        if start is None:
            return False

        i = start
        while i < len(self.lines) and "(" not in self.lines[i]:
            i += 1
        if i >= len(self.lines):
            return False

        list_start = i

        list_end = None
        depth = 0
        for j in range(list_start, len(self.lines)):
            depth += self.lines[j].count("(")
            depth -= self.lines[j].count(")")
            if depth == 0 and ")" in self.lines[j]:
                list_end = j
                break
        if list_end is None:
            return False

        for k in range(list_start + 1, list_end):
            if "{" in self.lines[k]:
                return self._remove_list_dict_item(list_start, list_end, idx)

        values = []
        for k in range(list_start + 1, list_end):
            line = self.lines[k].strip()
            if not line or line.startswith("//"):
                continue
            values.append(k)

        if idx < 0 or idx >= len(values):
            return False

        del self.lines[values[idx]]
        self._cleanup_blank_lines()
        self._rebuild_node()
        self._invalidate_cache()
        return True

    def _remove_list_dict_item(self, list_start, list_end, idx):
        items = []
        depth = 0
        cur_start = None

        for j in range(list_start + 1, list_end):
            line = self.lines[j]

            if "{" in line:
                cur_start = j

            if cur_start is not None:
                depth += line.count("{")
                depth -= line.count("}")

                if depth == 0:
                    items.append((cur_start, j))
                    cur_start = None

        if idx < 0 or idx >= len(items):
            return False

        s, e = items[idx]

        del self.lines[s:e + 1]
        self._normalize_after_remove(s - 1, s)
        self.mark_dirty()
        return True

    # Rename Keyname
    def rename(self, route: str, new_key: str):
        node = self._find_node(self.root_node, route)
        if node is None:
            return False

        line = node.line_start
        text = self.lines[line]

        ks = node.key_col_start
        ke = node.key_col_end

        vcol = ke
        while vcol < len(text) and text[vcol] in " \t":
            vcol += 1

        new_key_end = ks + len(new_key)

        if new_key_end <= vcol:
            gap = vcol - new_key_end
            new_line = text[:ks] + new_key + (" " * gap) + text[vcol:]
        else:
            new_line = text[:ks] + new_key + " " + text[vcol:]

        self.lines[line] = new_line
        node.key = new_key
        node.key_col_end = ks + len(new_key)
        self.mark_dirty()
        return True

    # Set(Change)
    def _resolve_name_to_index(self, route: str):
        parts = [p for p in route.split(".") if p]
        if len(parts) < 2:
            return route

        top = parts[0]
        if "[" in top and "]" in top:
            return route

        node = self._find_node(self.root_node, top)
        if node is None:
            return route

        if not isinstance(node.value, list):
            return route

        name = parts[1]
        tail = ".".join(parts[2:])

        for i, child in enumerate(getattr(node, "children", []) or []):
            if str(getattr(child, "key", "")) == name:
                return f"{top}[{i}]" + (f".{tail}" if tail else "")

        return route

    def _format_vector(self, value):
        return f"({' '.join(str(v) for v in value)})"

    def _replace_range(self, line: int, col_start: int, col_end: int, new_value: str):
        text = self.lines[line]
        self.lines[line] = text[:col_start] + new_value + text[col_end:]

    def change_value(self, route, new_value, show_type="auto", map_key=None):
        if self.lines is None or self.root_node is None:
            return False

        route = self._resolve_name_to_index(route)

        if route.endswith("inGroups"):
            result = self._set_ingroups_patch(route, new_value)
            if result:
                self._invalidate_cache()
            return result

        if "regions[" in route and map_key is not None:
            result = self._set_regions_patch(route, new_value, map_key)
            if result:
                self._invalidate_cache()
            return result

        if "vertices" in route :
            result = self._set_vertices_block_patch(new_value)
            if result:
                self._invalidate_cache()
            return result

        if "vertices[" in route:
            result = self._set_vertices_patch(route, new_value)
            if result:
                self._invalidate_cache()
            return result

        if "blocks[" in route and map_key is not None:
            result = self._set_blocks_patch(route, new_value, map_key)
            if result:
                self._invalidate_cache()
            return result

        if self._is_simple_list_block(route, new_value):
            result = self._set_simple_list_block_patch(route, new_value, show_type)
            if result:
                self._invalidate_cache()
            return result

        if "[" in route and "]." in route:
            result = self._set_list_dict_line_patch(route, new_value)
            if result:
                self._invalidate_cache()
            return result

        node = self._find_node(self.root_node, route)
        if node is None:
            return False

        if node.value_col_start is None or node.value_col_end is None:
            return False

        if isinstance(new_value, (list, tuple)) and len(new_value) == 3:
            value_str = self._format_vector(new_value)
        else:
            value_str = str(new_value)

        # 주석보존
        line = self.lines[node.line_start]

        comment_pos = line.find("//", node.value_col_end)
        if comment_pos != -1 and comment_pos > node.value_col_start:
            comment = " " + line[comment_pos:].lstrip()
            body = line[:comment_pos].rstrip()
        else:
            comment = ""
            body = line

        new_line = (
                body[:node.value_col_start]
                + value_str
                + body[node.value_col_end:]
                + comment
        )

        self.lines[node.line_start] = new_line
        node.value = new_value
        self.mark_dirty()
        # self._rebuild_node()
        self._invalidate_cache()
        return True

    def _parse_route(self, route: str):
        tokens = []
        for part in route.split("."):
            for k, i in re.findall(r'([^\[\]]+)|\[(\d+)\]', part):
                tokens.append(k if k else int(i))
        return tokens

    def _set_list_dict_line_patch(self, route, new_value):
        tokens = self._parse_route(route)
        if len(tokens) != 3:
            return False

        top_key, idx, field = tokens
        if not isinstance(idx, int):
            return False

        node = self._find_node(self.root_node, top_key)
        if node is None:
            return False

        cur = -1
        i = node.line_start + 1

        while i <= node.block_end_line:
            if self.lines[i].strip() == "{":
                cur += 1
                i += 1

                if cur != idx:
                    depth = 1
                    while i <= node.block_end_line and depth > 0:
                        s = self.lines[i].strip()
                        if s == "{":
                            depth += 1
                        elif s == "}":
                            depth -= 1
                        i += 1
                    continue

                while i <= node.block_end_line:
                    line = self.lines[i]
                    s = line.strip()

                    if s == "}":
                        return False

                    if s.startswith(field):
                        body = line.lstrip()
                        indent_len = len(line) - len(body)

                        key_len = len(field)
                        val_start = indent_len + key_len
                        while val_start < len(line) and line[val_start] in " \t":
                            val_start += 1

                        val_end = val_start
                        while val_end < len(line) and line[val_end] not in ";/":
                            val_end += 1

                        self._replace_range(i, val_start, val_end, str(new_value))
                        return True

                    i += 1
            i += 1

        return False

    def _is_simple_list_block(self, route, value):
        if not isinstance(value, (list, tuple)):
            return False

        node = self._find_node(self.root_node, route)
        if node is None:
            return False

        if node.block_end_line is None:
            return False

        for v in value:
            if isinstance(v, (list, tuple, dict)):
                return False

        return True

    def _set_simple_list_block_patch(self, route, value, show_type):
        node = self._find_node(self.root_node, route)
        if node is None:
            return False

        indent = self.lines[node.line_start][
                 :len(self.lines[node.line_start]) - len(self.lines[node.line_start].lstrip())]

        lines = []

        if show_type == "inline":
            body = " ".join('"' + v + '"' if isinstance(v, str) else str(v) for v in value)
            lines.append(indent + "    " + body)
        else:
            for v in value:
                if isinstance(v, str):
                    lines.append(indent + "    " + '"' + v + '"')
                else:
                    lines.append(indent + "    " + str(v))

        start = node.line_start + 2
        end = node.block_end_line

        self.lines[start:end] = lines
        self._rebuild_node()
        return True

    def _set_ingroups_patch(self, route, value):
        if not isinstance(value, (list, tuple)):
            return False

        parent_route = route.rsplit(".", 1)[0]
        node = self._find_node(self.root_node, parent_route)
        if node is None:
            return False

        items = list(value)
        count = len(items)
        inner = " ".join(str(v) for v in items)

        for i in range(node.line_start + 1, node.block_end_line):
            line = self.lines[i]
            s = line.lstrip()

            if not s.startswith("inGroups"):
                continue

            key_pos = line.find("inGroups")
            after_key = key_pos + len("inGroups")

            count_start = after_key
            while count_start < len(line) and line[count_start] in " \t":
                count_start += 1

            count_end = count_start
            while count_end < len(line) and line[count_end].isdigit():
                count_end += 1

            paren_l = line.find("(", after_key)
            paren_r = line.find(")", paren_l + 1)
            if paren_l == -1 or paren_r == -1:
                return False

            self._replace_range(i, count_start, count_end, str(count))
            self._replace_range(i, paren_l + 1, paren_r, f" {inner} ")
            self.mark_dirty()
            return True
        return False

    def _set_regions_patch(self, route, value, map_key):
        base_route = route.split("[", 1)[0]
        node = self._find_node(self.root_node, base_route)
        if node is None:
            return False

        regions = node.value
        idx = int(route.split("[")[1].split("]")[0])
        if idx < 0 or idx >= len(regions):
            return False

        region = regions[idx]

        if map_key == "type":
            region[0] = value
        elif map_key == "names":
            region[1] = value if isinstance(value, list) else [value]
        else:
            return False

        cur = -1
        for i in range(node.line_start + 1, node.block_end_line):
            line = self.lines[i]
            stripped = line.strip()

            if not stripped or stripped == "(":
                continue
            if stripped.startswith(")"):
                break

            cur += 1
            if cur != idx:
                continue

            paren_l = line.find("(")
            paren_r = line.find(")", paren_l + 1)
            if paren_l == -1 or paren_r == -1:
                return False

            if map_key == "names":
                names = " ".join(region[1])
                self._replace_range(i, paren_l + 1,paren_r,
                    f" {names} ",)
                return True

            type_start = len(line) - len(line.lstrip())

            paren_l = line.find("(")
            if paren_l == -1:
                return False

            type_end = type_start
            while type_end < paren_l and line[type_end] not in " \t":
                type_end += 1

            count_start = type_end
            while count_start < paren_l and not line[count_start].isdigit():
                count_start += 1

            if map_key == "type":
                regions[idx][0] = value
                self.lines[i] = self._format_regions_line(
                    line,
                    value,
                    regions[idx][1],
                )
                return True

            if map_key == "names":
                regions[idx][1] = value if isinstance(value, list) else [value]
                self.lines[i] = self._format_regions_line(
                    line,
                    regions[idx][0],
                    regions[idx][1],
                )
                return True

            new_type = region[0]

            width = count_start - type_start

            if len(new_type) < width:
                repl = new_type + (" " * (width - len(new_type)))
            else:
                repl = new_type + " "

            self._replace_range(i, type_start, count_start, repl)
            self.mark_dirty()
            return True
        return False

    def _format_regions_line(self, line, type_name, names):
        indent = line[:len(line) - len(line.lstrip())]

        type_start = len(indent)
        type_end = type_start
        while type_end < len(line) and not line[type_end].isspace():
            type_end += 1

        paren_l = line.find("(")
        if paren_l == -1:
            return f"{indent}{type_name} ({' '.join(names)})"

        old_pad_len = paren_l - type_end
        old_type_len = type_end - type_start
        new_type_len = len(type_name)

        pad_len = max(1, old_pad_len - (new_type_len - old_type_len))
        pad = " " * pad_len

        return f"{indent}{type_name}{pad}({' '.join(names)})"

    def _set_vertices_block_patch(self, value):
        node = self._find_node(self.root_node, "vertices")
        if node is None:
            return False

        if not isinstance(value, (list, tuple)):
            return False

        lines = []
        for v in value:
            if not isinstance(v, (list, tuple)) or len(v) != 3:
                return False
            lines.append("    ( " + "  ".join(str(x) for x in v) + " )")

        start = node.line_start + 2
        end = node.block_end_line

        self.lines[start:end] = lines
        self.mark_dirty()
        return True

    def _set_blocks_patch(self, route, value, map_key):
        node = self._find_node(self.root_node, "blocks")
        if node is None:
            return False

        idx = int(route.split("[")[1].split("]")[0])

        cur = -1
        for i in range(node.line_start + 1, node.block_end_line):
            line = self.lines[i]
            stripped = line.lstrip()

            if not stripped.startswith("hex"):
                continue

            cur += 1
            if cur != idx:
                continue

            if map_key == "cells":
                first_l = line.find("(")
                first_r = line.find(")", first_l + 1)
                second_l = line.find("(", first_r + 1)
                second_r = line.find(")", second_l + 1)

                if second_l == -1 or second_r == -1:
                    return False

                new_text = " ".join(str(v) for v in value)
                self._replace_range(i, second_l + 1, second_r, new_text)
                return True

            if map_key == "grading":
                key_pos = line.find("simpleGrading")
                if key_pos == -1:
                    return False

                l = line.find("(", key_pos)
                r = line.find(")", l + 1)
                if l == -1 or r == -1:
                    return False

                new_text = " ".join(str(v) for v in value)
                self._replace_range(i, l + 1, r, new_text)
                self.mark_dirty()
                return True
            return False
        return False

    # Clear dictionary or list contents
    def clear(self, route: str):
        """Clear dictionary or list contents while keeping the structure"""
        if self.lines is None or self.root_node is None:
            return False

        node = self._find_node(self.root_node, route)
        if node is None:
            return False

        # Handle dictionary (has block_end_line)
        if node.block_end_line is not None:
            # Delete all lines between the opening and closing braces
            start = node.line_start + 2  # Skip key line and opening brace
            end = node.block_end_line     # Keep closing brace

            if start < end:
                del self.lines[start:end]

            # Clear children nodes
            node.children = []

            self._rebuild_node()
            self._invalidate_cache()
            return True

        # Handle list (value is a list)
        if isinstance(node.value, list):
            # Find the line with opening parenthesis
            start = node.line_start
            i = start
            while i < len(self.lines) and "(" not in self.lines[i]:
                i += 1
            if i >= len(self.lines):
                return False

            list_start = i

            # Find the line with closing parenthesis
            list_end = None
            depth = 0
            for j in range(list_start, len(self.lines)):
                depth += self.lines[j].count("(")
                depth -= self.lines[j].count(")")
                if depth == 0 and ")" in self.lines[j]:
                    list_end = j
                    break

            if list_end is None:
                return False

            # Delete all lines between parentheses
            if list_start + 1 < list_end:
                del self.lines[list_start + 1:list_end]

            # Update node value
            node.value = []
            if hasattr(node, 'children'):
                node.children = []

            self._rebuild_node()
            self._invalidate_cache()
            return True

        return False

    def _normalize_after_remove(self, start=None, end=None):
        if start is not None and end is not None:
            self._cleanup_inner_blank_lines(start, end)
        self._cleanup_blank_lines()

