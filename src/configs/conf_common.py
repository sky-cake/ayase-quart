from typing import Any, Callable

'''
default_val_fn is either:
    a callable taking in 1 value and returning 1 value or a value
    if it's a callable, expect a value
    if it's a value, it should not clobber what is already inside
examples:
    massage_key(conf_d, 'key1', 'A default value')
    massage_key(conf_d, 'key2', some_function)
    massage_key(conf_d, 'key3', lambda x: f"/{x.strip('/')}")
'''
def massage_key(d: dict[str, Any], key: str, default_val_fn: Callable[[Any], Any]|Any=None):
    if callable(default_val_fn):
        d[key] = default_val_fn(d.get(key))
    else:
        d.setdefault(key, default_val_fn)
