import os
import sys

# Add parent folder to sys.path, so we can import boot.
# App Engine causes main.py to be reloaded if an exception gets raised
# on the first request of a main.py instance, so don't add project_dir multiple
# times.
project_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if project_dir not in sys.path or sys.path.index(project_dir) > 0:
    sys.path.insert(0, project_dir)

# Remove the standard version of Django.
if 'django' in sys.modules and sys.modules['django'].VERSION < (1, 2):
    for k in [k for k in sys.modules
              if k.startswith('django\.') or k == 'django']:
        del sys.modules[k]

from djangoappengine.boot import setup_env, setup_logging, env_ext
setup_env()

import django.core.handlers.wsgi
from google.appengine.ext.webapp import util
from django.conf import settings

def log_traceback(*args, **kwargs):
    import logging
    logging.exception('Exception in request:')

from django.core import signals
signals.got_request_exception.connect(log_traceback)

def real_main():
    # Reset path and environment variables
    global path_backup
    try:
        sys.path = path_backup[:]
    except:
        path_backup = sys.path[:]
    os.environ.update(env_ext)
    setup_logging()

    # Create a Django application for WSGI.
    application = django.core.handlers.wsgi.WSGIHandler()

    # Run the WSGI CGI handler with that application.
    util.run_wsgi_app(application)

def profile_main():
    import logging, cProfile, pstats, random, StringIO
    only_forced_profile = getattr(settings, 'ONLY_FORCED_PROFILE', False)
    profile_percentage = getattr(settings, 'PROFILE_PERCENTAGE', None)
    if (only_forced_profile and
                'profile=forced' not in os.environ.get('QUERY_STRING')) or \
            (not only_forced_profile and profile_percentage and
                float(profile_percentage) / 100.0 <= random.random()):
        return real_main()

    prof = cProfile.Profile()
    prof = prof.runctx('real_main()', globals(), locals())
    stream = StringIO.StringIO()
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

main = getattr(settings, 'ENABLE_PROFILER', False) and profile_main or real_main

if __name__ == '__main__':
    main()
