#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# CHANGED: show warning if profiler is enabled, so you don't mistakenly upload
# with non-production settings. Also, added --nosyncdb switch.

import sys
import logging

from django.core.management.base import BaseCommand

def run_appcfg(argv):
    # import this so that we run through the checks at the beginning
    # and report the appropriate errors
    import appcfg

    # We don't really want to use that one though, it just executes this one
    from google.appengine.tools import appcfg

    # Reset the logging level to WARN as appcfg will spew tons of logs on INFO
    logging.getLogger().setLevel(logging.WARN)
    
    new_args = argv[:]
    new_args[1] = 'update'
    new_args.append('.')
    syncdb = True
    if '--nosyncdb' in new_args:
        syncdb = False
        new_args.remove('--nosyncdb')
    appcfg.main(new_args)

    if syncdb:
        from django.core.management import call_command
        from django.db import connection
        connection.setup_remote()
        print 'Running syncdb.'
        call_command('syncdb', remote=True, interactive=True)

    from django.conf import settings
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
        run_appcfg(argv)
