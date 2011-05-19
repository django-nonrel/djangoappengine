from ..utils import appid, have_appserver, on_production_server
from ..boot import DATA_ROOT
from .creation import DatabaseCreation
from django.db.backends.util import format_number
from djangotoolbox.db.base import NonrelDatabaseFeatures, \
    NonrelDatabaseOperations, NonrelDatabaseWrapper, NonrelDatabaseClient, \
    NonrelDatabaseValidation, NonrelDatabaseIntrospection
from google.appengine.ext.db.metadata import get_kinds, get_namespaces
from google.appengine.api.datastore import Query, Delete
from google.appengine.api.namespace_manager import set_namespace
from urllib2 import HTTPError, URLError
import logging
import os
import time

REMOTE_API_SCRIPT = '$PYTHON_LIB/google/appengine/ext/remote_api/handler.py'
DATASTORE_PATHS = {
    'datastore_path': os.path.join(DATA_ROOT, 'datastore'),
    'blobstore_path': os.path.join(DATA_ROOT, 'blobstore'),
    'rdbms_sqlite_path': os.path.join(DATA_ROOT, 'rdbms'),
    'prospective_search_path': os.path.join(DATA_ROOT, 'prospective-search'),
}

def auth_func():
    import getpass
    return raw_input('Login via Google Account (see note above if login fails): '), getpass.getpass('Password: ')

def rpc_server_factory(*args, ** kwargs):
    from google.appengine.tools import appengine_rpc
    kwargs['save_cookies'] = True
    return appengine_rpc.HttpRpcServer(*args, ** kwargs)

def get_datastore_paths(options):
    paths = {}
    for key, path in DATASTORE_PATHS.items():
        paths[key] = options.get(key, path)
    return paths

def get_test_datastore_paths(options, inmemory=True):
    paths = get_datastore_paths(options)
    for key in paths:
        paths[key] += '.test'
    if inmemory:
        for key in ('datastore_path', 'blobstore_path'):
            paths[key] = None
    return paths

def destroy_datastore(paths):
    """Destroys the appengine datastore at the specified paths."""
    for path in paths.values():
        if not path:
            continue
        try:
            os.remove(path)
        except OSError, error:
            if error.errno != 2:
                logging.error("Failed to clear datastore: %s" % error)

class DatabaseFeatures(NonrelDatabaseFeatures):
    allows_primary_key_0 = True
    supports_dicts = True

class DatabaseOperations(NonrelDatabaseOperations):
    compiler_module = __name__.rsplit('.', 1)[0] + '.compiler'

    DEFAULT_MAX_DIGITS = 16

    def value_to_db_decimal(self, value, max_digits, decimal_places):
        if value is None:
            return None
        sign = value < 0 and u'-' or u''
        if sign: 
            value = abs(value)
        if max_digits is None: 
            max_digits = self.DEFAULT_MAX_DIGITS

        if decimal_places is None:
            value = unicode(value)
        else:
            value = format_number(value, max_digits, decimal_places)
        decimal_places = decimal_places or 0
        n = value.find('.')

        if n < 0:
            n = len(value)
        if n < max_digits - decimal_places:
            value = u"0" * (max_digits - decimal_places - n) + value
        return sign + value

    def sql_flush(self, style, tables, sequences):
        self.connection.flush()
        return []

class DatabaseClient(NonrelDatabaseClient):
    pass

class DatabaseValidation(NonrelDatabaseValidation):
    pass

class DatabaseIntrospection(NonrelDatabaseIntrospection):
    def table_names(self):
        """Returns a list of names of all tables that exist in the database."""
        return [kind.key().name() for kind in Query(kind='__kind__').Run()]

class DatabaseWrapper(NonrelDatabaseWrapper):
    def __init__(self, *args, **kwds):
        super(DatabaseWrapper, self).__init__(*args, **kwds)
        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.validation = DatabaseValidation(self)
        self.introspection = DatabaseIntrospection(self)
        options = self.settings_dict
        self.use_test_datastore = False
        self.test_datastore_inmemory = True
        self.remote = options.get('REMOTE', False)
        if on_production_server:
            self.remote = False
        self.remote_app_id = options.get('REMOTE_APP_ID', appid)
        self.domain = options.get('DOMAIN', 'appspot.com')
        self.remote_api_path = options.get('REMOTE_API_PATH', None)
        self.secure_remote_api = options.get('SECURE_REMOTE_API', True)
        self._setup_stubs()

    def _get_paths(self):
        if self.use_test_datastore:
            return get_test_datastore_paths(self.settings_dict, self.test_datastore_inmemory)
        else:
            return get_datastore_paths(self.settings_dict)

    def _setup_stubs(self):
        # If this code is being run without an appserver (eg. via a django
        # commandline flag) then setup a default stub environment.
        if not have_appserver:
            from google.appengine.tools import dev_appserver_main
            args = dev_appserver_main.DEFAULT_ARGS.copy()
            args.update(self._get_paths())
            log_level = logging.getLogger().getEffectiveLevel()
            logging.getLogger().setLevel(logging.WARNING)
            from google.appengine.tools import dev_appserver
            dev_appserver.SetupStubs(appid, **args)
            logging.getLogger().setLevel(log_level)
        # If we're supposed to set up the remote_api, do that now.
        if self.remote:
            self.setup_remote()

    def setup_remote(self):
        if not self.remote_api_path:
            from ..utils import appconfig
            for handler in appconfig.handlers:
                if handler.script == REMOTE_API_SCRIPT:
                    self.remote_api_path = handler.url.split('(', 1)[0]
                    break
        self.remote = True
        server = '%s.%s' % (self.remote_app_id, self.domain)
        remote_url = 'https://%s%s' % (server, self.remote_api_path)
        logging.info('Setting up remote_api for "%s" at %s' %
                     (self.remote_app_id, remote_url))
        if not have_appserver:
            print('Connecting to remote_api handler.\n\n'
                  'IMPORTANT: Check your login method settings in the '
                  'App Engine Dashboard if you have problems logging in. '
                  'Login is only supported for Google Accounts.\n')
        from google.appengine.ext.remote_api import remote_api_stub
        remote_api_stub.ConfigureRemoteApi(None,
            self.remote_api_path, auth_func, servername=server,
            secure=self.secure_remote_api,
            rpc_server_factory=rpc_server_factory)
        retry_delay = 1
        while retry_delay <= 16:
            try:
                remote_api_stub.MaybeInvokeAuthentication()
            except HTTPError, e:
                if not have_appserver:
                    print 'Retrying in %d seconds...' % retry_delay
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                break
        else:
            try:
                remote_api_stub.MaybeInvokeAuthentication()
            except HTTPError, e:
                raise URLError("%s\n"
                               "Couldn't reach remote_api handler at %s.\n"
                               "Make sure you've deployed your project and "
                               "installed a remote_api handler in app.yaml. "
                               "Note that login is only supported for "
                               "Google Accounts. Make sure you've configured "
                               "the correct authentication method in the "
                               "App Engine Dashboard."
                               % (e, remote_url))
        logging.info('Now using the remote datastore for "%s" at %s' %
                     (self.remote_app_id, remote_url))

    def flush(self):
        """Helper function to remove the current datastore and re-open the stubs"""
        if self.remote:
            import random
            import string
            code = ''.join([random.choice(string.ascii_letters) for x in range(4)])
            print '\n\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
            print '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
            print "Warning! You're about to delete the *production* datastore!"
            print 'Only models defined in your INSTALLED_APPS can be removed!'
            print 'If you want to clear the whole datastore you have to use the ' \
                  'datastore viewer in the dashboard. Also, in order to delete all '\
                  'unneeded indexes you have to run appcfg.py vacuum_indexes.'
            print 'In order to proceed you have to enter the following code:'
            print code
            response = raw_input('Repeat: ')
            if code == response:
                print 'Deleting...'
                delete_all_entities()
                print "Datastore flushed! Please check your dashboard's " \
                      'datastore viewer for any remaining entities and remove ' \
                      'all unneeded indexes with manage.py vacuum_indexes.'
            else:
                print 'Aborting'
                exit()
        else:
            destroy_datastore(self._get_paths())
        self._setup_stubs()

def delete_all_entities():
    for namespace in get_namespaces():
        set_namespace(namespace)
        for kind in get_kinds():
            if kind.startswith('__'):
                continue
            while True:
                data = Query(kind=kind, keys_only=True).Get(200)
                if not data:
                    break
                Delete(data)