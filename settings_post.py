# -*- coding: utf-8 -*-
from settings import *
import sys

if '%d' in MEDIA_URL:
    MEDIA_URL = MEDIA_URL % MEDIA_VERSION
if '%s' in ADMIN_MEDIA_PREFIX:
    ADMIN_MEDIA_PREFIX = ADMIN_MEDIA_PREFIX % MEDIA_URL

TEMPLATE_DEBUG = DEBUG
MANAGERS = ADMINS

# You can override Django's or some apps' locales with these folders:
if os.path.exists(os.path.join(COMMON_DIR, 'locale_overrides_common')):
    INSTALLED_APPS += ('locale_overrides_common',)
if os.path.exists(os.path.join(PROJECT_DIR, 'locale_overrides')):
    INSTALLED_APPS += ('locale_overrides',)

## Add admin interface media files if necessary
#if 'django.contrib.admin' in INSTALLED_APPS:
#    INSTALLED_APPS += ('django_export.admin_media',)
#
## Always add Django templates (exported from zip)
#INSTALLED_APPS += (
#    'django_export.django_templates',
#)

if have_appserver or on_production_server:
    check_app_imports = None
else:
    def check_app_imports(app):
        before = sys.modules.keys()
        __import__(app, {}, {}, [''])
        after = sys.modules.keys()
        added = [key[len(app)+1:] for key in after if key not in before and
                 key.startswith(app + '.') and key[len(app)+1:]]
        if added:
            import logging
            logging.warn('The app "%(app)s" contains imports in '
                         'its __init__.py (at least %(added)s). This can cause '
                         'strange bugs due to recursive imports! You should '
                         'either do the import lazily (within functions) or '
                         'ignore the app settings/urlsauto with '
                         'IGNORE_APP_SETTINGS and IGNORE_APP_URLSAUTO in '
                         'your settings.py.'
                         % {'app': app, 'added': ', '.join(added)})

# Import app-specific settings
_globals = globals()
class _Module(object):
    def __setattr__(self, key, value):
        _globals[key] = value
    def __getattribute__(self, key):
        return _globals[key]
    def __hasattr__(self, key):
        return key in _globals
settings = _Module()

for app in INSTALLED_APPS:
    # This is an optimization. Django's apps don't have special settings.
    # Also, allow for ignoring some apps' settings.
    if app.startswith('django.') or app.endswith('.*') or \
            app == 'djangoappengine' or app in IGNORE_APP_SETTINGS:
        continue
    try:
        # First we check if __init__.py doesn't import anything
        if check_app_imports:
            check_app_imports(app)
        __import__(app + '.settings', {}, {}, [''])
    except ImportError:
        pass

try:
    from settings_overrides import *
except ImportError:
    pass
