from django.core.management.base import BaseCommand

from google.appengine.api import apiproxy_stub_map
from google.appengine.datastore import datastore_stub_util

from optparse import make_option

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--addrport', action='store', dest='addrport',
            type='string', default='',
            help='port number or ipaddr:port to run the server on'),
        make_option('--ipv6', '-6', action='store_true', dest='use_ipv6', default=False,
            help='Tells Django to use a IPv6 address.'),
    )
    help = 'Runs a development server with data from the given fixture(s).'
    args = '[fixture ...]'

    requires_model_validation = False

    def handle(self, *fixture_labels, **options):
        from django.core.management import call_command
        from django import db
        from ...db.base import get_datastore_paths, DatabaseWrapper
        from ...db.stubs import stub_manager

        verbosity = int(options.get('verbosity'))
        interactive = options.get('interactive')
        addrport = options.get('addrport')

        db_name = None

        for name in db.connections:
            conn = db.connections[name]
            if isinstance(conn, DatabaseWrapper):
                settings = conn.settings_dict
                for key, path in get_datastore_paths(settings).items():
                    settings[key] = "%s-testdb" % path
                conn.flush()

                # reset stub manager
                stub_manager.active_stubs = None
                stub_manager.setup_local_stubs(conn)

                db_name = name
                break

        # Temporarily change consistency policy to force apply loaded data
        datastore = apiproxy_stub_map.apiproxy.GetStub('datastore_v3')

        orig_consistency_policy = datastore._consistency_policy
        datastore.SetConsistencyPolicy(datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=1))

        # Import the fixture data into the test database.
        call_command('loaddata', *fixture_labels, **{'verbosity': verbosity})

        # reset original policy
        datastore.SetConsistencyPolicy(orig_consistency_policy)

        # Run the development server. Turn off auto-reloading because it causes
        # a strange error -- it causes this handle() method to be called
        # multiple times.
        shutdown_message = '\nServer stopped.\nNote that the test database, %r, has not been deleted. You can explore it on your own.' % db_name
        call_command('runserver', addrport=addrport, shutdown_message=shutdown_message, use_reloader=False, use_ipv6=options['use_ipv6'])
