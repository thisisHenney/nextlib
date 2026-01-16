class Node:
    def __init__(
        self,
        key=None,
        value=None,
        children=None,
        parent=None,
        line_start=0,
        line_end=0,
        col_start=0,
        col_end=0,
        key_col_start=None,
        key_col_end=None,
        value_col_start=None,
        value_col_end=None,
        block_end_line=None,
    ):
        self.key = key
        self.value = value
        self.children = children or []
        self.child_map = {}
        self.parent = parent

        self.line_start = line_start
        self.line_end = line_end
        self.col_start = col_start
        self.col_end = col_end

        self.key_col_start = key_col_start
        self.key_col_end = key_col_end
        self.value_col_start = value_col_start
        self.value_col_end = value_col_end
        self.block_end_line = block_end_line

    def add_child(self, node):
        self.children.append(node)
        self.child_map.setdefault(node.key, []).append(node)
