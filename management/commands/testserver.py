#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import sys

from .runserver import start_dev_appserver
from django.core.management.base import BaseCommand
from djangoappengine.db.base import destroy_datastore, get_test_datastore_paths


class Command(BaseCommand):
    """Overrides the default Django testserver command.

    Instead of starting the default Django development server this command fires
    up a copy of the full fledged appengine dev_appserver.

    The appserver is always initialised with a blank datastore with the specified
    fixtures loaded into it.
    """
    help = 'Runs the development server with data from the given fixtures.'

    def run_from_argv(self, argv):
        fixtures = []
        for arg in argv[2:]:
            if arg.startswith('-'):
                break
            fixtures.append(arg)
            argv.remove(arg)

        try:
            index = argv.index('--addrport')
            addrport = argv[index + 1]
            del argv[index:index+2]
            argv = argv[:2] + [addrport] + argv[2:index] + argv[index+1:]
        except:
            pass

        # Ensure an on-disk test datastore is used.
        from django.db import connection
        connection.use_test_datastore = True
        connection.test_datastore_inmemory = False

        # Flush any existing test datastore.
        connection.flush()

        # Load the fixtures.
        from django.core.management import call_command
        call_command('loaddata', 'initial_data')
        if fixtures:
            call_command('loaddata', *fixtures)

        # Build new arguments for dev_appserver.
        argv[1] = 'runserver'
        datastore_path, history_path = get_test_datastore_paths(False)
        argv.extend(['--datastore_path', datastore_path])
        argv.extend(['--history_path', history_path])

        start_dev_appserver(argv)
