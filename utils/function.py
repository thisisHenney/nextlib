from functools import partial

def create_func_args(func, *args):
    return partial(func, *args)

def create_func_widget_args(widget, func, *args):
    return partial(func, widget, *args)


