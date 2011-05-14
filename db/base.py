from ..boot import DATA_ROOT
from ..utils import appid, on_production_server
from .creation import DatabaseCreation
from .stubs import stub_manager
from django.db.backends.util import format_number
from djangotoolbox.db.base import NonrelDatabaseFeatures, \
    NonrelDatabaseOperations, NonrelDatabaseWrapper, NonrelDatabaseClient, \
    NonrelDatabaseValidation, NonrelDatabaseIntrospection
from google.appengine.ext.db.metadata import get_kinds, get_namespaces
from google.appengine.api.datastore import Query, Delete
from google.appengine.api.namespace_manager import set_namespace
import logging
import os

DATASTORE_PATHS = {
    'datastore_path': os.path.join(DATA_ROOT, 'datastore'),
    'blobstore_path': os.path.join(DATA_ROOT, 'blobstore'),
    'rdbms_sqlite_path': os.path.join(DATA_ROOT, 'rdbms'),
    'prospective_search_path': os.path.join(DATA_ROOT, 'prospective-search'),
}

def get_datastore_paths(options):
    paths = {}
    for key, path in DATASTORE_PATHS.items():
        paths[key] = options.get(key, path)
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
        self.remote_app_id = options.get('REMOTE_APP_ID', appid)
        self.domain = options.get('DOMAIN', 'appspot.com')
        self.remote_api_path = options.get('REMOTE_API_PATH', None)
        self.secure_remote_api = options.get('SECURE_REMOTE_API', True)

        remote = options.get('REMOTE', False)
        if on_production_server:
            remote = False
        if remote:
            stub_manager.setup_remote_stubs(self)
        else:
            stub_manager.setup_stubs(self)

    def flush(self):
        """Helper function to remove the current datastore and re-open the stubs"""
        if stub_manager.active_stubs == 'remote':
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
        elif stub_manager.active_stubs == 'test':
            stub_manager.deactivate_test_stubs()
            stub_manager.activate_test_stubs()
#        elif on_production_server or have_appserver:
#            delete_all_entities()
        else:
            destroy_datastore(get_datastore_paths(self.settings_dict))
            stub_manager.setup_local_stubs(self)

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