import datetime
from .creation import DatabaseCreation
from ..utils import appid, have_appserver, on_production_server
from djangotoolbox.db.base import NonrelDatabaseFeatures, \
    NonrelDatabaseOperations, NonrelDatabaseWrapper, NonrelDatabaseClient, \
    NonrelDatabaseValidation, NonrelDatabaseIntrospection
import logging, os
from django.db.backends.util import format_number

def auth_func():
    import getpass
    return raw_input('Login via Google Account:'), getpass.getpass('Password:')

def rpc_server_factory(*args, ** kwargs):
    from google.appengine.tools import appengine_rpc
    kwargs['save_cookies'] = True
    return appengine_rpc.HttpRpcServer(*args, ** kwargs)

def get_datastore_paths(options):
    """Returns a tuple with the path to the datastore and history file.

    The datastore is stored in the same location as dev_appserver uses by
    default, but the name is altered to be unique to this project so multiple
    Django projects can be developed on the same machine in parallel.

    Returns:
      (datastore_path, history_path)
    """
    from google.appengine.tools import dev_appserver_main
    datastore_path = options.get('datastore_path',
                                 dev_appserver_main.DEFAULT_ARGS['datastore_path'].replace(
                                 'dev_appserver', 'django_%s' % appid))
    blobstore_path = options.get('blobstore_path',
                                 dev_appserver_main.DEFAULT_ARGS['blobstore_path'].replace(
                                 'dev_appserver', 'django_%s' % appid))
    history_path = options.get('history_path',
                               dev_appserver_main.DEFAULT_ARGS['history_path'].replace(
                               'dev_appserver', 'django_%s' % appid))
    return datastore_path, blobstore_path, history_path

def get_test_datastore_paths(inmemory=True):
    """Returns a tuple with the path to the test datastore and history file.

    If inmemory is true, (None, None) is returned to request an in-memory
    datastore. If inmemory is false the path returned will be similar to the path
    returned by get_datastore_paths but with a different name.

    Returns:
      (datastore_path, history_path)
    """
    if inmemory:
        return None, None, None
    datastore_path, blobstore_path, history_path = get_datastore_paths()
    datastore_path = datastore_path.replace('.datastore', '.testdatastore')
    blobstore_path = blobstore_path.replace('.blobstore', '.testblobstore')
    history_path = history_path.replace('.datastore', '.testdatastore')
    return datastore_path, blobstore_path, history_path

def destroy_datastore(*args):
    """Destroys the appengine datastore at the specified paths."""
    for path in args:
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
    pass

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
        self.use_test_datastore = options.get('use_test_datastore', False)
        self.test_datastore_inmemory = options.get('test_datastore_inmemory', True)
        self.remote = options.get('remote', False)
        if on_production_server:
            self.remote = False
        self.remote_app_id = options.get('remote_id', appid)
        self.remote_host = options.get('remote_host', '%s.appspot.com' % self.remote_app_id)
        self.remote_url = options.get('remote_url', '/remote_api')
        self._setup_stubs()

    def _get_paths(self):
        if self.use_test_datastore:
            return get_test_datastore_paths(self.test_datastore_inmemory)
        else:
            return get_datastore_paths(self.settings_dict)

    def _setup_stubs(self):
        # If this code is being run without an appserver (eg. via a django
        # commandline flag) then setup a default stub environment.
        if not have_appserver:
            from google.appengine.tools import dev_appserver_main
            args = dev_appserver_main.DEFAULT_ARGS.copy()
            args['datastore_path'], args['blobstore_path'], args['history_path'] = self._get_paths()
            from google.appengine.tools import dev_appserver
            dev_appserver.SetupStubs(appid, **args)
        # If we're supposed to set up the remote_api, do that now.
        if self.remote:
            self.setup_remote()

    def setup_remote(self):
        self.remote = True
        logging.info('Setting up remote_api for "%s" at http://%s%s' %
                     (self.remote_app_id, self.remote_host, self.remote_url)
                     )
        from google.appengine.ext.remote_api import remote_api_stub
        from google.appengine.ext import db
        remote_api_stub.ConfigureRemoteDatastore(self.remote_app_id,
            self.remote_url, auth_func, self.remote_host,
            rpc_server_factory=rpc_server_factory)
        logging.info('Now using the remote datastore for "%s" at http://%s%s' %
                     (self.remote_app_id, self.remote_host, self.remote_url))

    def flush(self):
        """Helper function to remove the current datastore and re-open the stubs"""
        if self.remote:
            import random, string
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
                from django.db import models
                from google.appengine.api import datastore as ds
                for model in models.get_models():
                    print 'Deleting %s...' % model._meta.db_table
                    while True:
                        data = ds.Query(model._meta.db_table, keys_only=True).Get(200)
                        if not data:
                            break
                        ds.Delete(data)
                print "Datastore flushed! Please check your dashboard's " \
                      'datastore viewer for any remaining entities and remove ' \
                      'all unneeded indexes with manage.py vacuum_indexes.'
            else:
                print 'Aborting'
                exit()
        else:
            destroy_datastore(*self._get_paths())
        self._setup_stubs()
