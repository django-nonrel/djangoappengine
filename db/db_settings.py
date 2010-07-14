from django.conf import settings
from django.utils.importlib import import_module

_MODULE_NAMES = getattr(settings, 'GAE_SETTINGS_MODULES', ())

FIELD_INDEXES = None

# TODO: add support for eventual consistency setting on specific models

def get_indexes():
    global FIELD_INDEXES
    if FIELD_INDEXES is None:
        field_indexes = {}
        for name in _MODULE_NAMES:
            try:
                field_indexes.update(import_module(name).FIELD_INDEXES)
            except (ImportError, AttributeError):
                pass
        FIELD_INDEXES = field_indexes
    return FIELD_INDEXES
