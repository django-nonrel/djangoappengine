from django.conf import settings
from django.utils.importlib import import_module

# TODO: add autodiscover() and make API more like dbindexer's register_index

_MODULE_NAMES = getattr(settings, 'GAE_SETTINGS_MODULES', ())

FIELD_INDEXES = None

# TODO: add support for eventual consistency setting on specific models

def get_model_indexes(model):
    indexes = get_indexes()
    model_index = {'indexed': [], 'unindexed': []}
    for item in reversed(model.mro()):
        config = indexes.get(item, {})
        model_index['indexed'].extend(config.get('indexed', ()))
        model_index['unindexed'].extend(config.get('unindexed', ()))
    return model_index

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
