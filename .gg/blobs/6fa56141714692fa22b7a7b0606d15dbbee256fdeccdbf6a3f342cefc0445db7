from functools import partial

def create_func_args(func, *args):
    return partial(func, *args)

def create_func_widget_args(widget, func, *args):
    return partial(func, widget, *args)


# 아래는 이전 함수(위에는 수정한 함수)
# def create_func_args(func=None, *args):
#     # 기존 함수에 매개변수가 있다면 args 뒤에 저장됨
#     new_func = func
#
#     if len(args) > 0:
#         new_func = partial(func, *args)
#         # prev: new_func = lambda: func(*args)
#     return new_func
#
#
# def create_func_widget_args(widget, func, *args):
#     # 기존 함수에 매개변수가 있다면 args 뒤에 저장됨
#     new_func = func
#     if len(args) > 0:
#         new_func = partial(func, widget, *args)
#         # prev: new_func = lambda: func(widget, *args)
#     return new_func
