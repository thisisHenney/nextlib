from nextlib.openfoam.PyFoamCase.header.node import Node


class NodeBuilder:
    def __init__(self, raw_text: str):
        self.lines = raw_text.splitlines(keepends=False)

    def build(self, extract_data: dict):
        root = Node(
            key=None,
            value=extract_data,
            line_start=0,
            line_end=max(0, len(self.lines) - 1),
            col_start=0,
            col_end=len(self.lines[-1]) if self.lines else 0,
            block_end_line=len(self.lines),
        )

        self._walk_dict(extract_data, root, 0)
        return root

    def _walk_dict(self, data: dict, parent: Node, start_line: int):
        line = start_line

        for key, value in data.items():
            key_line = self._find_key_line(key, line)
            if key_line is None:
                continue

            key_col_start = self.lines[key_line].find(key)
            key_col_end = key_col_start + len(key)

            node = Node(
                key=key,
                value=value,
                parent=parent,
                line_start=key_line,
                key_col_start=key_col_start,
                key_col_end=key_col_end,
            )

            block_start = self._find_next_non_empty(key_line)

            if isinstance(value, dict):
                block_end = self._find_brace_block_end(block_start)
                node.line_end = block_end
                node.col_end = len(self.lines[block_end])
                node.block_end_line = block_end
                self._walk_dict(value, node, block_start + 1)

            elif isinstance(value, list):
                inline = "(" in self.lines[key_line] and ")" in self.lines[key_line]
                if inline:
                    vs, ve = self._find_value_range(key_line, key_col_end)
                    node.value_col_start = vs
                    node.value_col_end = ve
                    node.line_end = key_line
                    node.col_end = ve
                else:
                    block_end = self._find_paren_block_end(block_start)
                    node.line_end = block_end
                    node.col_end = len(self.lines[block_end])
                    node.block_end_line = block_end
                    self._walk_list(value, node, block_start + 1, block_end - 1)

            else:
                vs, ve = self._find_value_range(key_line, key_col_end)
                node.value_col_start = vs
                node.value_col_end = ve
                node.line_end = key_line
                node.col_end = ve

            parent.add_child(node)
            line = node.line_end + 1

    def _walk_list(self, values: list, parent: Node, start_line: int, end_line: int):
        index = 0
        line = start_line

        while index < len(values) and line <= end_line:
            value = values[index]

            if isinstance(value, dict):
                open_line = self._find_next_char_line("{", line, end_line)
                if open_line is None:
                    # regions 같은 소괄호 기반 문법은 dict라도 { } 블록이 없음
                    item_line = self._find_next_non_empty(line - 1)
                    if item_line is None or item_line > end_line:
                        break

                    item = Node(
                        key=f"[{index}]",
                        value=value,
                        parent=parent,
                        line_start=item_line,
                        line_end=item_line,
                        col_end=len(self.lines[item_line]),
                    )

                    parent.add_child(item)
                    line = item_line + 1
                    index += 1
                    continue

                close_line = self._find_matching_brace_close(open_line, end_line)

                item = Node(
                    key=f"[{index}]",
                    value=value,
                    parent=parent,
                    line_start=open_line,
                    line_end=close_line,
                    col_end=len(self.lines[close_line]),
                    block_end_line=close_line,
                )

                parent.add_child(item)
                self._walk_dict(value, item, open_line + 1)
                line = close_line + 1
                index += 1
                continue

            item_line = self._find_next_non_empty(line - 1)
            if item_line is None or item_line > end_line:
                break

            item = Node(
                key=f"[{index}]",
                value=value,
                parent=parent,
                line_start=item_line,
                line_end=item_line,
                col_end=len(self.lines[item_line]),
            )

            parent.add_child(item)
            line = item_line + 1
            index += 1

    def _find_key_line(self, key: str, start: int):
        search_limit = min(start + 50, len(self.lines))
        for i in range(start, search_limit):
            if self.lines[i].lstrip().startswith(key):
                return i

        for i in range(search_limit, len(self.lines)):
            if self.lines[i].lstrip().startswith(key):
                return i
        return None

    def _find_next_non_empty(self, line: int):
        for i in range(line + 1, len(self.lines)):
            if self.lines[i].strip():
                return i
        return None

    def _find_next_char_line(self, ch: str, start: int, end: int):
        for i in range(start, min(end + 1, len(self.lines))):
            if ch in self.lines[i]:
                return i
        return None

    def _find_matching_brace_close(self, open_line: int, end_line: int):
        depth = 0
        for i in range(open_line, min(end_line + 1, len(self.lines))):
            depth += self.lines[i].count("{")
            depth -= self.lines[i].count("}")
            if depth == 0:
                return i
        return open_line

    def _find_brace_block_end(self, start: int):
        depth = 0
        for i in range(start, len(self.lines)):
            depth += self.lines[i].count("{")
            depth -= self.lines[i].count("}")
            if depth == 0 and "}" in self.lines[i]:
                return i
        return start

    def _find_paren_block_end(self, start: int):
        depth = 0
        for i in range(start, len(self.lines)):
            depth += self.lines[i].count("(")
            depth -= self.lines[i].count(")")
            if depth == 0 and ")" in self.lines[i]:
                return i
        return start

    def _find_value_range(self, line: int, key_col_end: int):
        text = self.lines[line]
        i = key_col_end

        while i < len(text) and text[i] in " \t":
            i += 1

        start = i

        if start < len(text) and text[start] in "({":
            open_ch = text[start]
            close_ch = ")" if open_ch == "(" else "}"
            depth = 0
            j = start

            while j < len(text):
                if text[j] == open_ch:
                    depth += 1
                elif text[j] == close_ch:
                    depth -= 1
                    if depth == 0:
                        return start, j + 1
                j += 1

            return start, j

        j = start
        while j < len(text) and text[j] != ";":
            j += 1

        return start, j


