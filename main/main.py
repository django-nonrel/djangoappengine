# Python 2.5 CGI handler.
import os
import sys

from djangoappengine.main import application
from google.appengine.ext.webapp.util import run_wsgi_app

from djangoappengine.boot import setup_logging, env_ext
from django.conf import settings


path_backup = None

def real_main():
    # Reset path and environment variables.
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
    logging.info("Profile data:\n%s.", stream.getvalue())


def make_profileable(func):
    if getattr(settings, 'ENABLE_PROFILER', False):
        return lambda: profile_main(func)
    return func

main = make_profileable(real_main)

if __name__ == '__main__':
    main()
