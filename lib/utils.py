
import collections

import inflect
import six

_inflect_engine = inflect.engine()

def plural (text, count = None):
    return _inflect_engine.plural(text, count)

def is_string (data):
    return isinstance(data, six.string_types)

def is_iterable (data):
    return (isinstance(data, collections.Iterable)) and (not is_string(data))
