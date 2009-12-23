#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Overrides the default Django flush command."""
    help = 'Clears the current datastore and loads the initial fixture data.'

    def run_from_argv(self, argv):
        from django.db import connection
        connection.flush()
        from django.core.management import call_command
        call_command('loaddata', 'initial_data')

    def handle(self, *args, **kwargs):
        self.run_from_argv(None)
