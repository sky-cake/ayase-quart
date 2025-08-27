from typing import Any, Callable


def fuvii(d: dict[str, Any], key: str, default_val_fn: Callable[[Any], Any]|Any=None):
    '''
    Function Update, or Value Insert or Ignore

    `default_val_fn` is either:

        1. a callable taking in 1 value and returning 1 value.
            - expects a value
        2. a value
            - will not change what the key points to

    examples:
        fuvii(conf_d, 'key1', 'A default value')
        fuvii(conf_d, 'key2', some_function)
        fuvii(conf_d, 'key3', lambda x: f"/{x.strip('/')}")
    '''
    if callable(default_val_fn):
        d[key] = default_val_fn(d.get(key))
    else:
        # does not update a key's value if the key exists already
        d.setdefault(key, default_val_fn)

