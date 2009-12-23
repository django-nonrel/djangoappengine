# -*- coding: utf-8 -*-
import os, sys

# Add parent folder to sys.path, so we can import aecmd.
# App Engine causes main.py to be reloaded if an exception gets raised
# on the first request of a main.py instance, so don't add parent_dir multiple
# times.
parent_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if parent_dir not in sys.path:
    sys.path = [parent_dir] + sys.path

# Remove the standard version of Django
for k in [k for k in sys.modules if k.startswith('django')]:
    del sys.modules[k]

from djangoappengine import aecmd
aecmd.setup_threading()
aecmd.setup_project()
aecmd.setup_logging()

import django.core.handlers.wsgi
from google.appengine.ext.webapp import util
from django.conf import settings

def real_main():
    # Reset path and environment variables
    global path_backup
    try:
        sys.path = path_backup[:]
    except:
        path_backup = sys.path[:]
    os.environ.update(aecmd.env_ext)
    aecmd.setup_logging()

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
