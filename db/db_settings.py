from django.conf import settings
from django.utils.importlib import import_module

FIELD_INDEXES = {}

# TODO: add support for eventual consistency setting on specific models

def load_indexes():
    index_modules = [app + '.db_settings_gae'
                     for app in settings.INSTALLED_APPS]
    index_modules.append('db_settings_gae')

    for name in index_modules:
        try:
            FIELD_INDEXES.update(import_module(name).FIELD_INDEXES)
        except (ImportError, AttributeError):
            pass

load_indexes()
