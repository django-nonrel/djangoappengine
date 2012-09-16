import logging
from optparse import make_option
import sys

from django.db import connections
from django.core.management.base import BaseCommand
from django.core.management.commands.runserver import BaseRunserverCommand
from django.core.exceptions import ImproperlyConfigured

from google.appengine.tools import dev_appserver_main

from ...boot import PROJECT_DIR
from ...db.base import DatabaseWrapper, get_datastore_paths


class Command(BaseRunserverCommand):
    """
    Overrides the default Django runserver command.

    Instead of starting the default Django development server this
    command fires up a copy of the full fledged App Engine
    dev_appserver that emulates the live environment your application
    will be deployed to.
    """

    option_list = BaseCommand.option_list + (
        make_option(
            '--debug', action='store_true', default=False,
            help="Prints verbose debugging messages to the console while " \
                 "running."),
        make_option(
            '--debug_imports', action='store_true', default=False,
            help="Prints debugging messages related to importing modules, " \
                 "including search paths and errors."),
        make_option(
            '-c', '--clear_datastore', action='store_true', default=False,
            help="Clears the datastore data and history files before " \
                 "starting the web server."),
        make_option(
            '--high_replication', action='store_true', default=False,
            help='Use the high replication datastore consistency model.'),
        make_option(
            '--require_indexes', action='store_true', default=False,
            help="Disables automatic generation of entries in the " \
                 "index.yaml file. Instead, when the application makes a " \
                 "query that requires that its index be defined in the file " \
                 "and the index definition is not found, an exception will " \
                 "be raised, similar to what would happen when running on " \
                 "App Engine."),
        make_option(
            '--enable_sendmail', action='store_true', default=False,
            help="Uses the local computer's Sendmail installation for " \
                 "sending email messages."),
        make_option(
            '--datastore_path',
            help="The path to use for the local datastore data file. " \
                 "The server creates this file if it does not exist."),
        make_option(
            '--history_path',
            help="The path to use for the local datastore history file. " \
                 "The server uses the query history file to generate " \
                 "entries for index.yaml."),
        make_option(
            '--login_url',
            help="The relative URL to use for the Users sign-in page. " \
                 "Default is /_ah/login."),
        make_option(
            '--smtp_host',
            help="The hostname of the SMTP server to use for sending email " \
                 "messages."),
        make_option(
            '--smtp_port',
            help="The port number of the SMTP server to use for sending " \
                 "email messages."),
        make_option(
            '--smtp_user',
            help="The username to use with the SMTP server for sending " \
                 "email messages."),
        make_option(
            '--smtp_password',
            help="The password to use with the SMTP server for sending " \
                 "email messages."),
        make_option(
            '--use_sqlite', action='store_true', default=False,
            help="Use the new, SQLite datastore stub."),
        make_option(
            '--allow_skipped_files', action='store_true', default=False,
            help="Allow access to files listed in skip_files."),
        make_option(
            '--disable_task_running', action='store_true', default=False,
            help="When supplied, tasks will not be automatically run after " \
                 "submission and must be run manually in the local admin " \
                 "console."),
    )

    help = "Runs a copy of the App Engine development server."
    args = "[optional port number, or ipaddr:port]"

    def create_parser(self, prog_name, subcommand):
        """
        Creates and returns the ``OptionParser`` which will be used to
        parse the arguments to this command.
        """
        # Hack __main__ so --help in dev_appserver_main works OK.
        sys.modules['__main__'] = dev_appserver_main
        return super(Command, self).create_parser(prog_name, subcommand)

    def run_from_argv(self, argv):
        """
        Captures the program name, usually "manage.py".
        """
        self.progname = argv[0]
        super(Command, self).run_from_argv(argv)

    def run(self, *args, **options):
        """
        Starts the App Engine dev_appserver program for the Django
        project. The appserver is run with default parameters. If you
        need to pass any special parameters to the dev_appserver you
        will have to invoke it manually.

        Unlike the normal devserver, does not use the autoreloader as
        App Engine dev_appserver needs to be run from the main thread
        """

        args = []
        # Set bind ip/port if specified.
        if self.addr:
            args.extend(['--address', self.addr])
        if self.port:
            args.extend(['--port', self.port])

        # If runserver is called using handle(), progname will not be
        # set.
        if not hasattr(self, 'progname'):
            self.progname = 'manage.py'

        # Add email settings.
        from django.conf import settings
        if not options.get('smtp_host', None) and \
           not options.get('enable_sendmail', None):
            args.extend(['--smtp_host', settings.EMAIL_HOST,
                         '--smtp_port', str(settings.EMAIL_PORT),
                         '--smtp_user', settings.EMAIL_HOST_USER,
                         '--smtp_password', settings.EMAIL_HOST_PASSWORD])

        # Pass the application specific datastore location to the
        # server.
        preset_options = {}
        for name in connections:
            connection = connections[name]
            if isinstance(connection, DatabaseWrapper):
                for key, path in get_datastore_paths(
                        connection.settings_dict).items():
                    # XXX/TODO: Remove this when SDK 1.4.3 is released.
                    if key == 'prospective_search_path':
                        continue

                    arg = '--' + key
                    if arg not in args:
                        args.extend([arg, path])
                # Get dev_appserver option presets, to be applied below.
                preset_options = connection.settings_dict.get(
                    'DEV_APPSERVER_OPTIONS', {})
                break

        # Process the rest of the options here.
        bool_options = [
            'debug', 'debug_imports', 'clear_datastore', 'require_indexes',
            'high_replication', 'enable_sendmail', 'use_sqlite',
            'allow_skipped_files', 'disable_task_running', ]
        for opt in bool_options:
            if options[opt] != False:
                args.append('--%s' % opt)

        str_options = [
            'datastore_path', 'history_path', 'login_url', 'smtp_host',
            'smtp_port', 'smtp_user', 'smtp_password', ]
        for opt in str_options:
            if options.get(opt, None) != None:
                args.extend(['--%s' % opt, options[opt]])

        # Fill any non-overridden options with presets from settings.
        for opt, value in preset_options.items():
            arg = '--%s' % opt
            if arg not in args:
                if value and opt in bool_options:
                    args.append(arg)
                elif opt in str_options:
                    args.extend([arg, value])
                # TODO: Issue warning about bogus option key(s)?

        # Reset logging level to INFO as dev_appserver will spew tons
        # of debug logs.
        logging.getLogger().setLevel(logging.INFO)

        # Append the current working directory to the arguments.
        dev_appserver_main.main([self.progname] + args + [PROJECT_DIR])
