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

from djangoappengine.boot import setup_env, setup_logging, env_ext
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

def real_main():
    # Reset path and environment variables
    global path_backup
    try:
        sys.path = path_backup[:]
    except:
        path_backup = sys.path[:]
    os.environ.update(env_ext)
    setup_logging()

    # Run the WSGI CGI handler with that application.
    run_wsgi_app(application)

def profile_main(func):
    from cStringIO import StringIO
    import cProfile
    import logging
    import pstats
    import random
    only_forced_profile = getattr(settings, 'ONLY_FORCED_PROFILE', False)
    profile_percentage = getattr(settings, 'PROFILE_PERCENTAGE', None)
    if (only_forced_profile and
                'profile=forced' not in os.environ.get('QUERY_STRING')) or \
            (not only_forced_profile and profile_percentage and
                float(profile_percentage) / 100.0 <= random.random()):
        return func()

    prof = cProfile.Profile()
    prof = prof.runctx('func()', globals(), locals())
    stream = StringIO()
    stats = pstats.Stats(prof, stream=stream)
    sort_by = getattr(settings, 'SORT_PROFILE_RESULTS_BY', 'time')
    if not isinstance(sort_by, (list, tuple)):
        sort_by = (sort_by,)
    stats.sort_stats(*sort_by)

    restrictions = []
    profile_pattern = getattr(settings, 'PROFILE_PATTERN', None)
    if profile_pattern:
        restrictions.append(profile_pattern)
    max_results = getattr(settings, 'MAX_PROFILE_RESULTS', 80)
    if max_results and max_results != 'all':
        restrictions.append(max_results)
    stats.print_stats(*restrictions)
    extra_output = getattr(settings, 'EXTRA_PROFILE_OUTPUT', None) or ()
    if not isinstance(sort_by, (list, tuple)):
        extra_output = (extra_output,)
    if 'callees' in extra_output:
        stats.print_callees()
    if 'callers' in extra_output:
        stats.print_callers()
    logging.info('Profile data:\n%s', stream.getvalue())

def make_profileable(func):
    if getattr(settings, 'ENABLE_PROFILER', False):
        return lambda: profile_main(func)
    return func

main = make_profileable(real_main)

if __name__ == '__main__':
    main()
