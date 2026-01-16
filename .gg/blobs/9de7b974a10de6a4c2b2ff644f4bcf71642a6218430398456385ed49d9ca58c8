class BaseUtil:
    def __init__(self):
        self.lines = None
        self.root_node = None
        self._dirty = False

    def get_bind(self, lines, root_node):
        self.lines = lines
        self.root_node = root_node

    def _rebuild_node(self):
        from nextlib.openfoam.PyFoamCase.header.nodebuilder import NodeBuilder
        from nextlib.openfoam.PyFoamCase.utils.tokenize import TokenizeUtil
        from nextlib.openfoam.PyFoamCase.utils.extract import ExtractUtil

        text = "\n".join(self.lines)
        tokens = TokenizeUtil().tokenize(text)
        data, _ = ExtractUtil().extract(tokens)
        self.root_node = NodeBuilder(text).build(data)

    def begin(self):
        self._dirty = False

    def mark_dirty(self):
        self._dirty = True

    def end(self):
        if self._dirty:
            self._rebuild_node()
            self._dirty = False

    def _find_node(self, node, route: str):
        if not route:
            return node

        cur = node
        for part in route.split("."):
            if "[" in part and part.endswith("]"):
                key, idx = part[:-1].split("[", 1)
                idx = int(idx)

                lst = cur.child_map.get(key)
                if not lst:
                    return None

                if idx < 0:
                    idx = len(lst) + idx

                if idx < 0 or idx >= len(lst):
                    return None
                cur = lst[idx]
            else:
                lst = cur.child_map.get(part)
                if not lst:
                    return None
                cur = lst[0]

        return cur

    def _guess_value_col(self, start, end):
        start_line = self.lines[start]
        start_indent = len(start_line) - len(start_line.lstrip())

        indent_cols = {}

        for i in range(start + 1, end):
            line = self.lines[i]
            s = line.lstrip()

            if not s or s.startswith("//") or s.startswith("/*"):
                continue
            if ";" not in s or "{" in s or "}" in s:
                continue

            indent = len(line) - len(s)

            key = s.split()[0]
            j = indent + len(key)
            while j < len(line) and line[j] in " \t":
                j += 1

            if indent > start_indent:
                return j

            indent_cols.setdefault(indent, []).append(j)

        if not indent_cols:
            return None

        max_indent = max(indent_cols, key=lambda k: len(indent_cols[k]))
        return indent_cols[max_indent][0]

    def _find_block_end(self, start):
        depth = 0
        opened = False
        for i in range(start, len(self.lines)):
            depth += self.lines[i].count("{")
            if self.lines[i].count("{") > 0:
                opened = True
            depth -= self.lines[i].count("}")
            if opened and depth == 0 and "}" in self.lines[i]:
                return i
        return None

    def _find_child_block_start(self, start, end, key):
        for i in range(start + 1, end):
            stripped = self.lines[i].lstrip()
            if stripped and stripped.startswith(key):
                return i
        return None

    def _cleanup_inner_blank_lines(self, start, end):
        i = start + 1

        while i < end and "{" not in self.lines[i]:
            i += 1
        i += 1

        while i < end and self.lines[i].strip() == "":
            del self.lines[i]
            end -= 1

        return end

    def _ensure_top_blank(self):
        if not self.lines:
            return

        i = len(self.lines) - 1
        while i >= 0 and self.lines[i].strip() == "":
            i -= 1

        if i < len(self.lines) - 1:
            self.lines = self.lines[:i + 2]
        else:
            self.lines.append("")

    def _find_line_start_uncached(self, key):
        for i, line in enumerate(self.lines):
            if line.lstrip().startswith(key):
                return i
        return None

    def _find_line_start(self, key):
        """
        기본 _find_line_start 메서드 (서브클래스에서 오버라이드 가능)
        ChangeDataUtil은 캐싱 버전으로 오버라이드함
        """
        return self._find_line_start_uncached(key)

    def _cleanup_blank_lines(self):
        new_lines = []
        blank_count = 0

        for line in self.lines:
            if line.strip() == "":
                blank_count += 1
                if blank_count <= 1:
                    new_lines.append(line)
            else:
                blank_count = 0
                new_lines.append(line)

        self.lines = new_lines

    def _resolve_insert_at(self, start, end,
            before_key=None, after_key=None, position=None):
        if position == "top":
            return start + 1

        if before_key:
            for i in range(start + 1, end):
                if self.lines[i].lstrip().startswith(before_key):
                    return i

        if after_key:
            for i in range(start + 1, end):
                if self.lines[i].lstrip().startswith(after_key):
                    return self._find_block_end(i) + 1

        return end

    def _build_block_lines(self, indent: str, key: str, payload,
                           is_leaf=False, parent_start=None, parent_end=None):
        KEY_COL = 16

        def pad_for(k):
            col = None
            if parent_start is not None and parent_end is not None:
                col = self._guess_value_col(parent_start, parent_end)
            if col is None:
                col = KEY_COL
            return " " * max(1, col - len(indent) - len(k))

        if is_leaf and not isinstance(payload, dict):
            pad = pad_for(key)

            if isinstance(payload, (list, tuple)) and len(payload) == 3:
                vec = "( " + " ".join(str(v) for v in payload) + " )"
                return [f"{indent}{key}{pad}{vec};"]

            return [f"{indent}{key}{pad}{payload};"]

        lines = [f"{indent}{key}", f"{indent}{{"]

        if isinstance(payload, dict):
            for k, v in payload.items():
                if isinstance(v, dict):
                    sub = self._build_block_lines(
                        indent + "    ",
                        k,
                        v,
                        is_leaf=False,
                        parent_start=parent_start,
                        parent_end=parent_end,
                    )
                    lines.extend(sub)
                else:
                    pad = pad_for(k)
                    lines.append(f"{indent}    {k}{pad}{v};")

        lines.append(f"{indent}}}")
        return lines
