class TokenizeUtil:
    def __init__(self):
        ...

    def tokenize(self, text):
        tokens = []
        i = 0
        n = len(text)

        symbols = {'{', '}', '(', ')', ';'}

        while i < n:
            c = text[i]

            if c == '/' and i + 1 < n:
                if text[i + 1] == '/':
                    token, i = self._read_line_comment(text, i)
                    tokens.append(token)
                    continue
                if text[i + 1] == '*':
                    token, i = self._read_block_comment(text, i)
                    tokens.append(token)
                    continue

            if c == '\n':
                tokens.append('\n')
                i += 1
                continue

            if c.isspace():
                token, i = self._read_space(text, i)
                tokens.append(token)
                continue

            if c in symbols:
                tokens.append(c)
                i += 1
                continue

            if c.isalnum() or c in ['"', '#', '$']:
                token, i = self._read_word(text, i)
                tokens.append(token)
                continue

            i += 1

        return tokens

    def _read_line_comment(self, text, start):
        i = start
        n = len(text)

        i += 2
        while i < n:
            if text[i] == '\n':
                break
            i += 1

        return text[start:i], i

    def _read_block_comment(self, text, start):
        i = start
        n = len(text)

        i += 2
        while i < n - 1:
            if text[i] == '*' and text[i + 1] == '/':
                i += 2
                break
            i += 1

        return text[start:i], i

    def _read_space(self, text, start):
        i = start
        n = len(text)

        while i < n and text[i].isspace() and text[i] != '\n':
            i += 1

        return text[start:i], i

    def _read_word(self, text, start):
        n = len(text)
        i = start

        if text[i] == '"':
            i += 1
            while i < n:
                if text[i] == '"':
                    i += 1
                    break
                i += 1
            return text[start:i], i

        while i < n:
            if text[i].isspace():
                break
            if text[i] in ['{', '}', '(', ')', ';']:
                break
            i += 1

        return text[start:i], i


