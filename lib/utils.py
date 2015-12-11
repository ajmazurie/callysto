
import collections

import inflect
import six

_inflect_engine = inflect.engine()

def plural (text, count = None):
    return _inflect_engine.plural(text, count)

def is_string (obj):
    return isinstance(obj, six.string_types)

def is_iterable (obj):
    return (isinstance(obj, collections.Iterable)) and (not is_string(obj))

def is_callable (obj):
    return six.callable(obj)

def flatten_text (text):
    lines = []
    for line in text.splitlines():
        lines.append(line.strip())
    return ' '.join(lines)
