def is_number(value):
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def is_integer(value):
    try:
        float_val = float(value)
        return float_val.is_integer()
    except (ValueError, TypeError):
        return False


def is_float(value):
    try:
        float_val = float(value)
        return not float_val.is_integer()
    except (ValueError, TypeError):
        return False


def is_alphabet(value):
    return isinstance(value, str) and value.isalpha()

def is_string(value):
    return isinstance(value, (str, bytes))
