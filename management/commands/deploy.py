from ...boot import PROJECT_DIR
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
import logging
import sys
import time

PRE_DEPLOY_COMMANDS = ()
if 'mediagenerator' in settings.INSTALLED_APPS:
    PRE_DEPLOY_COMMANDS += ('generatemedia',)
PRE_DEPLOY_COMMANDS = getattr(settings, 'PRE_DEPLOY_COMMANDS',
                              PRE_DEPLOY_COMMANDS)
POST_DEPLOY_COMMANDS = getattr(settings, 'POST_DEPLOY_COMMANDS', ())

def run_appcfg(argv):
    # We don't really want to use that one though, it just executes this one
    from google.appengine.tools import appcfg

    # Reset the logging level to WARN as appcfg will spew tons of logs on INFO
    logging.getLogger().setLevel(logging.WARN)

    new_args = argv[:]
    new_args[1] = 'update'
    new_args.append(PROJECT_DIR)
    syncdb = True
    if '--nosyncdb' in new_args:
        syncdb = False
        new_args.remove('--nosyncdb')
    appcfg.main(new_args)

    if syncdb:
        print 'Running syncdb.'
        # Wait a little bit for deployment to finish
        for countdown in range(9, 0, -1):
            sys.stdout.write('%s\r' % countdown)
            time.sleep(1)
        from django.db import connections
        for connection in connections.all():
            if hasattr(connection, 'setup_remote'):
                connection.setup_remote()
        call_command('syncdb', remote=True, interactive=True)

    if getattr(settings, 'ENABLE_PROFILER', False):
        print '--------------------------\n' \
              'WARNING: PROFILER ENABLED!\n' \
              '--------------------------'

class Command(BaseCommand):
    """Deploys the website to the production server.

    Any additional arguments are passed directly to appcfg.py update
    """
    help = 'Calls appcfg.py update for the current project.'
    args = '[any appcfg.py options]'

    def run_from_argv(self, argv):
        for command in PRE_DEPLOY_COMMANDS:
            call_command(command)
        try:
            run_appcfg(argv)
        finally:
            for command in POST_DEPLOY_COMMANDS:
                call_command(command)
