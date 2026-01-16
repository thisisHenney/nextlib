import re
from nextlib.openfoam.PyFoamCase.utils.baseutil import BaseUtil

class InsertDataUtil(BaseUtil):
    def __init__(self):
        super().__init__()

        self.KEY_COL = 16

    def insert_value(
            self,
            route: str,
            value,
            show_type: str = "auto",
            before_key: str | None = None,
            after_key: str | None = None,
            position: str | None = None,
    ):
        if self.lines is None:
            return False

        self._strip_trailing_blank_lines()

        m = re.match(r"^([^\[\]]+)\[(\d+)\]\.(.+)$", route)
        if m:
            list_key, idx, rest = m.groups()
            idx = int(idx)
            return self._insert_into_list_dict(list_key, idx, rest, value, show_type)

        parts = [p for p in route.split(".") if p]
        if not parts:
            return False

        if len(parts) == 1 and not isinstance(value, dict):
            key = parts[0]

            if self._find_line_start(key) is not None:
                return True

            if isinstance(value, (list, tuple)) and show_type == "multiline":
                self._ensure_top_blank()
                self.lines.append(key)
                self.lines.append("(")
                for v in value:
                    if isinstance(v, str):
                        self.lines.append(f"    '{v}'")
                    else:
                        self.lines.append(f"    {v}")
                self.lines.append(");")

                self._cleanup_blank_lines()
                self.mark_dirty()
                return True

            value_col = self._find_last_toplevel_value_col()
            if value_col is None:
                value_col = self.KEY_COL

            self._strip_trailing_blank_lines()
            self._ensure_one_blank_before_append()

            pad = " " * max(1, value_col - len(key))
            self.lines.append(f"{key}{pad}{value};")

            self._cleanup_blank_lines()
            self.mark_dirty()
            return True

        if len(parts) == 1 and isinstance(value, dict):
            key = parts[0]

            if self._find_line_start(key) is not None:
                return True

            target_col = self._guess_top_level_child_value_col_visual()

            self._ensure_top_blank()
            self.lines.append(key)
            self.lines.append("{")

            field_indent = "    "
            tabsize = 8

            for k, v in value.items():
                left = (field_indent + k).expandtabs(tabsize)
                pad = " " * max(1, target_col - len(left))
                self.lines.append(f"{field_indent}{k}{pad}{v};")

            self.lines.append("}")
            self._cleanup_blank_lines()
            self.mark_dirty()
            return True

        top = parts[0]
        top_start = self._find_line_start(top)

        if top_start is None:
            self._ensure_top_blank()
            self.lines.append(top)
            self.lines.append("{")
            self.lines.append("}")
            top_start = len(self.lines) - 3

        top_end = self._find_block_end(top_start)
        if top_end is None:
            return False

        cur_start, cur_end = top_start, top_end

        for depth, key in enumerate(parts[1:], start=1):
            child_start = self._find_child_block_start(cur_start, cur_end, key)

            if child_start is None:
                indent = "    " * depth
                payload = value if depth == len(parts) - 1 else {}
                block_lines = self._build_block_lines(
                    indent,
                    key,
                    payload,
                    is_leaf=(depth == len(parts) - 1),
                    parent_start=cur_start,
                    parent_end=cur_end,
                )

                cur_end = self._cleanup_inner_blank_lines(cur_start, cur_end)

                insert_at = self._resolve_insert_at(
                    cur_start,
                    cur_end,
                    before_key if depth == len(parts) - 1 else None,
                    after_key if depth == len(parts) - 1 else None,
                    position if depth == len(parts) - 1 else None,
                )

                self.lines[insert_at:insert_at] = block_lines

                cur_end += len(block_lines)
                child_start = insert_at
                child_end = child_start + len(block_lines) - 1
            else:
                child_end = self._find_block_end(child_start)
                if child_end is None:
                    return False

            cur_start, cur_end = child_start, child_end

        self._cleanup_blank_lines()
        self.mark_dirty()
        return True

    def _insert_into_list_dict(self, list_key, idx, field, value, show_type="auto"):
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
                return True

        indent = self.lines[item_start]
        indent = indent[:len(indent) - len(indent.lstrip())] + "    "

        pad_len = self._extract_key_padding_from_prev_item(item_start, item_end)
        if pad_len is None:
            pad_len = 5

        pad = " " * pad_len
        insert_at = self._remove_blank_between_items(item_end)
        self.lines.insert(insert_at, f"{indent}{field}{pad}{value};")

        self._cleanup_blank_lines()
        self.mark_dirty()
        return True

    def insert_list_item(self, route: str, item: dict):
        if self.lines is None:
            return False

        start = self._find_line_start(route)
        if start is None:
            return False

        i = start
        while i < len(self.lines) and "(" not in self.lines[i]:
            i += 1
        if i >= len(self.lines):
            return False

        list_start = i

        depth = 0
        list_end = None
        for j in range(list_start, len(self.lines)):
            depth += self.lines[j].count("(")
            depth -= self.lines[j].count(")")
            if depth == 0 and ")" in self.lines[j]:
                list_end = j
                break
        if list_end is None:
            return False

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

        if items:
            prev_start, prev_end = items[-1]
            item_indent = self.lines[prev_start]
            item_indent = item_indent[:len(item_indent) - len(item_indent.lstrip())]
            value_col = self._guess_prev_item_value_col(prev_start, prev_end)
            if value_col is None:
                value_col = self.KEY_COL
        else:
            base = self.lines[list_start]
            base_indent = base[:len(base) - len(base.lstrip())]
            item_indent = base_indent + "    "
            value_col = self.KEY_COL

        lines = self._build_list_dict_lines_aligned(item_indent, item, value_col)

        insert_at = self._remove_blank_between_items(list_end)
        self.lines[insert_at:insert_at] = lines

        self._cleanup_blank_lines()
        self.mark_dirty()
        return True

    def _extract_key_padding_from_prev_item(self, item_start, item_end):
        for i in range(item_start + 1, item_end):
            line = self.lines[i]
            s = line.strip()

            if not s or s.startswith("//"):
                continue
            if "{" in s or "}" in s:
                continue
            if ";" not in s:
                continue

            stripped = line.lstrip()
            indent_len = len(line) - len(stripped)

            key = stripped.split()[0]
            key_end = indent_len + len(key)

            j = key_end
            while j < len(line) and line[j] == " ":
                j += 1

            return j - key_end

        return None

    def _guess_prev_item_value_col(self, item_start, item_end):
        for i in range(item_start + 1, item_end):
            line = self.lines[i]
            s = line.strip()
            if not s or s.startswith("//"):
                continue
            if "{" in s or "}" in s:
                continue
            if ";" not in s:
                continue

            m = re.match(r"^(\s*)(\S+)(\s+)", line)
            if not m:
                continue
            return len(m.group(1)) + len(m.group(2)) + len(m.group(3))

        return None

    def _build_list_dict_lines_aligned(self, block_indent, value: dict, value_col):
        lines = [f"{block_indent}{{"]
        field_indent = block_indent + "    "

        for k, v in value.items():
            pad = " " * max(1, value_col - len(field_indent) - len(k))
            lines.append(f"{field_indent}{k}{pad}{v};")

        lines.append(f"{block_indent}}}")
        return lines

    def _remove_blank_between_items(self, insert_at):
        while 0 < insert_at <= len(self.lines):
            if self.lines[insert_at - 1].strip() == "":
                del self.lines[insert_at - 1]
                insert_at -= 1
            else:
                break
        return insert_at

    def _strip_trailing_blank_lines(self):
        while self.lines and self.lines[-1].strip() == "":
            self.lines.pop()

    def _find_last_toplevel_value_col(self):
        last_key_line = None

        for i in range(len(self.lines)):
            s = self.lines[i].lstrip()
            if not s or s.startswith("//"):
                continue
            if "{" in s or "}" in s:
                continue
            if ";" in s:
                last_key_line = i

        if last_key_line is None:
            return None

        return self._guess_value_col(last_key_line - 1, last_key_line + 1)

    def _ensure_one_blank_before_append(self):
        if not self.lines:
            return
        if self.lines[-1].strip() != "":
            self.lines.append("")

    def _guess_top_level_child_value_col_visual(self):
        cols = []
        tabsize = 8

        i = 0
        while i < len(self.lines):
            line = self.lines[i]
            stripped = line.lstrip()

            if not stripped or stripped.startswith("//"):
                i += 1
                continue

            if stripped.endswith("{") and not line.startswith(" "):
                block_start = i
                block_end = self._find_block_end(block_start)
                if block_end is None:
                    i += 1
                    continue

                for j in range(block_start + 1, block_end):
                    l = self.lines[j]
                    if not l.startswith("    "):
                        continue
                    if l.startswith("        "):
                        continue
                    col = self._value_start_col_visual(l)
                    if col is not None:
                        cols.append(col)

                i = block_end + 1
                continue

            i += 1

        return max(cols) if cols else self.KEY_COL

    def _value_start_col_visual(self, line: str):
        s = line.rstrip("\n")
        if ";" not in s:
            return None

        if "//" in s:
            s = s.split("//", 1)[0].rstrip()

        t = s.lstrip()
        if not t or t.startswith("//"):
            return None
        if "{" in t or "}" in t:
            return None

        if not t.endswith(";"):
            return None

        indent = s[:len(s) - len(t)]
        parts = t.split(None, 1)
        if len(parts) < 2:
            return None

        key = parts[0]
        rest = parts[1]
        m = re.match(r"^(\s+)", rest)
        if not m:
            return None

        tabsize = 8
        left = (indent + key + m.group(1)).expandtabs(tabsize)
        return len(left)



