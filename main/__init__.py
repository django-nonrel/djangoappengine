import os
import sys

# Add parent folder to sys.path, so we can import boot.
# App Engine causes main.py to be reloaded if an exception gets raised
# on the first request of a main.py instance, so don't add project_dir multiple
# times.
project_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if project_dir not in sys.path or sys.path.index(project_dir) > 0:
    while project_dir in sys.path:
        sys.path.remove(project_dir)
    sys.path.insert(0, project_dir)

for path in sys.path[:]:
    if path != project_dir and os.path.isdir(os.path.join(path, 'django')):
        sys.path.remove(path)
        break

# Remove the standard version of Django.
if 'django' in sys.modules and sys.modules['django'].VERSION < (1, 2):
    for k in [k for k in sys.modules
              if k.startswith('django.') or k == 'django']:
        del sys.modules[k]

from djangoappengine.boot import setup_env
setup_env()

def validate_models():
    """Since BaseRunserverCommand is only run once, we need to call
    model valdidation here to ensure it is run every time the code
    changes.

    """
    import logging
    from django.core.management.validation import get_validation_errors
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

    logging.info("Validating models...")

    s = StringIO()
    num_errors = get_validation_errors(s, None)

    if num_errors:
        s.seek(0)
        error_text = s.read()
        logging.critical("One or more models did not validate:\n%s" % error_text)
    else:
        logging.info("All models validated.")

from djangoappengine.utils import on_production_server
if not on_production_server:
    validate_models()

from django.core.handlers.wsgi import WSGIHandler
from google.appengine.ext.webapp.util import run_wsgi_app
from django.conf import settings

def log_traceback(*args, **kwargs):
    import logging
    logging.exception('Exception in request:')

from django.core import signals
signals.got_request_exception.connect(log_traceback)

# Create a Django application for WSGI
application = WSGIHandler()

# Add the staticfiles handler if necessary
if settings.DEBUG and 'django.contrib.staticfiles' in settings.INSTALLED_APPS:
    from django.contrib.staticfiles.handlers import StaticFilesHandler
    application = StaticFilesHandler(application)
