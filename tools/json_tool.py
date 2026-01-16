import json
import os
import copy
from pathlib import Path
from nextlib.utils.file import get_encoding_type

SPLIT_CHAR = '.'


class JsonTool:
    def __init__(self, file='', buffer=None):
        self._file = file
        self._buffer = buffer if buffer is not None else {}
        self._split_char = SPLIT_CHAR

    def create(self, file=''):
        if file:
            self._file = file
        self._buffer = {}
        return self.save()

    def read(self, file=''):
        if file:
            self._file = file

        path = Path(self._file)
        if not path.is_file():
            print(f"[!!] File not found: {self._file}")
            return False

        encoding_type = get_encoding_type(self.path)  # 다시 확인
        text = path.read_text(encoding=encoding_type)

        check = self.check_json_error(text)
        if not check["check"]:
            check["file"] = self._file
            print(check)
            return False

        self._buffer = json.loads(text)
        return True

    def check_json_error(self, text: str):
        try:
            json.loads(text)
            return {"check": True}

        except json.JSONDecodeError as e:
            result = {
                "check": False,
                "message": e.msg,
                "line": e.lineno,
                "column": e.colno,
                "pos": e.pos,
            }

            start = max(e.pos - 30, 0)
            end = min(e.pos + 30, len(text))
            result["near"] = text[start:end]

            import re
            before = text[:e.pos]
            matches = list(re.finditer(r'"([^"]+)"\s*:', before))
            result["key_hint"] = matches[-1].group(1) if matches else None

            return result

    def save(self, file=''):
        if file:
            self._file = file
        if not self._file:
            return False
        with open(self._file, 'w', encoding='utf-8') as f:
            json.dump(self._buffer, f, ensure_ascii=False, indent=4)
        return True

    def _parse_key(self, key):
        parts = []
        for part in key.split(self._split_char):
            while '[' in part and ']' in part:
                idx = part[part.index('[') + 1: part.index(']')]
                name = part[:part.index('[')]
                if name:
                    parts.append(name)
                parts.append(int(idx))
                part = part[part.index(']') + 1:]
            if part:
                parts.append(part)
        return parts

    def _ensure_list_size(self, lst, index):
        while len(lst) <= index:
            lst.append({})
        return lst

    def _navigate(self, keys, create=True):
        buf = self._buffer
        for i, k in enumerate(keys[:-1]):
            next_k = keys[i + 1]

            if isinstance(k, int):
                if not isinstance(buf, list):
                    if not create:
                        return None
                    buf_parent = buf
                    buf_parent[:] = [] if isinstance(buf_parent, list) else []
                    buf = buf_parent

                self._ensure_list_size(buf, k)
                buf = buf[k]
                continue

            if k not in buf:
                if not create:
                    return None

                if isinstance(next_k, int):
                    buf[k] = []
                else:
                    buf[k] = {}

            if isinstance(next_k, int) and not isinstance(buf[k], list):
                buf[k] = []
            elif isinstance(next_k, str) and not isinstance(buf[k], dict):
                buf[k] = {}

            buf = buf[k]

        return buf

    def get(self, keys):
        buf = self._buffer
        for k in self._parse_key(keys):
            if isinstance(k, int):
                if not isinstance(buf, list) or len(buf) <= k:
                    return None
                buf = buf[k]
            else:
                if not isinstance(buf, dict) or k not in buf:
                    return None
                buf = buf[k]
        return buf

    def add(self, keys, value=''):
        keys = self._parse_key(keys)
        buf = self._navigate(keys, create=True)
        last = keys[-1]

        if isinstance(last, int):
            if not isinstance(buf, list):
                buf[last] = []
            self._ensure_list_size(buf, last)
            buf[last] = value
            return True

        if last not in buf:
            buf[last] = value
            return True

        current = buf[last]

        if isinstance(current, dict) and isinstance(value, dict):
            current.update(value)
            return True

        if isinstance(current, list):
            if isinstance(value, list):
                current.extend(value)
            else:
                current.append(value)
            return True

        buf[last] = [current]
        if isinstance(value, list):
            buf[last].extend(value)
        else:
            buf[last].append(value)

        return True

    def set(self, keys, value=''):
        keys = self._parse_key(keys)
        buf = self._navigate(keys, create=True)
        last = keys[-1]

        if isinstance(last, int):
            if not isinstance(buf, list):
                buf.clear()
                buf.extend([])
            self._ensure_list_size(buf, last)
            buf[last] = value
            return True

        buf[last] = value
        return True

    def remove(self, keys, include_key=True):
        keys = self._parse_key(keys)
        buf = self._navigate(keys, create=False)
        if buf is None:
            return False

        last = keys[-1]

        if isinstance(last, int):
            if isinstance(buf, list) and len(buf) > last:
                if include_key:
                    buf.pop(last)
                else:
                    buf[last] = None
            return True

        if last in buf:
            if include_key:
                del buf[last]
            else:
                buf[last] = None
        return True
