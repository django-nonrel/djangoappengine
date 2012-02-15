import datetime
import decimal
import logging
import os
import shutil

from django.db.backends.util import format_number
from django.db.utils import DatabaseError

from google.appengine.api.datastore import Delete, Query
from google.appengine.api.datastore_errors import BadArgumentError, \
    BadValueError
from google.appengine.api.datastore_types import Blob, Key, Text, \
    ValidateInteger
from google.appengine.api.namespace_manager import set_namespace
from google.appengine.ext.db.metadata import get_kinds, get_namespaces

from djangotoolbox.db.base import \
    NonrelDatabaseClient, NonrelDatabaseFeatures, \
    NonrelDatabaseIntrospection, NonrelDatabaseOperations, \
    NonrelDatabaseValidation, NonrelDatabaseWrapper

from ..boot import DATA_ROOT
from ..utils import appid, on_production_server
from .creation import DatabaseCreation
from .stubs import stub_manager


DATASTORE_PATHS = {
    'datastore_path': os.path.join(DATA_ROOT, 'datastore'),
    'blobstore_path': os.path.join(DATA_ROOT, 'blobstore'),
    #'rdbms_sqlite_path': os.path.join(DATA_ROOT, 'rdbms'),
    'prospective_search_path': os.path.join(DATA_ROOT, 'prospective-search'),
}


def key_from_path(db_table, value):
    """
    Workaround for GAE choosing not to validate integer ids when
    creating keys.

    TODO: Should be removed if it gets fixed.
    """
    if isinstance(value, (int, long)):
        ValidateInteger(value, 'id')
    return Key.from_path(db_table, value)


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
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError, error:
            if error.errno != 2:
                logging.error("Failed to clear datastore: %s" % error)


class DatabaseFeatures(NonrelDatabaseFeatures):

    # GAE only allow strictly positive integers (and strings) to be
    # used as key values.
    allows_primary_key_0 = False

    # Anything that results in a something different than a positive
    # integer or a string cannot be directly used as a key on GAE.
    # Note that DecimalField values are encoded as strings, so can be
    # used as keys.
    # With some encoding, we could allow most fields to be used as a
    # primary key, but for now only mark what can and what cannot be
    # safely used.
    supports_primary_key_on = \
        NonrelDatabaseFeatures.supports_primary_key_on - set((
        'FloatField', 'DateField', 'DateTimeField', 'TimeField',
        'BooleanField', 'NullBooleanField', 'TextField', 'XMLField'))


class DatabaseOperations(NonrelDatabaseOperations):
    compiler_module = __name__.rsplit('.', 1)[0] + '.compiler'

    # Used when a DecimalField does not specify max_digits or when
    # encoding a float as a string, fixed to preserve comparisons.
    DEFAULT_MAX_DIGITS = 16

    # Date used to store times as datetimes.
    # TODO: Use just date()?
    DEFAULT_DATE = datetime.date(1970, 1, 1)

    # Time used to store dates as datetimes.
    DEFAULT_TIME = datetime.time()

    def sql_flush(self, style, tables, sequences):
        self.connection.flush()
        return []

    def value_to_db_auto(self, value):
        """
        Converts all AutoField values to integers, just like vanilla
        Django.

        Why can't we allow both strings and ints for keys? Because
        Django cannot differentiate one from the other, for example
        it can create an object with a key equal to int(1) and then ask
        for it using string('1'). This is not a flaw -- ints arrive
        as strings in requests and "untyped" field doesn't have any
        way to distinguish one from the other (unless you'd implement
        a custom AutoField that would use values reinforced with their
        type, but that's rather not worth the hassle).
        """
        if value is None:
            return None
        return int(value)

    def value_to_db_decimal(self, value, max_digits, decimal_places):
        """
        Converts decimal to a unicode string for storage / lookup.

        We need to convert in a way that preserves order -- if one
        decimal is less than another, their string representations
        should compare the same.

        This is more a field conversion than a type conversion because
        it needs a fixed field attributes to function and doesn't work
        for special decimal values like Infinity or NaN.

        TODO: Can't this be done using string.format()?
              Not in Python 2.5, str.format is backported to 2.6 only.
        """
        if value is None:
            return None

        # Handle sign separately.
        if value.is_signed():
            sign = u'-'
            value = abs(value)
        else:
            sign = u''

        # Convert to a string.
        if max_digits is None:
            max_digits = self.DEFAULT_MAX_DIGITS
        if decimal_places is None:
            value = unicode(value)
            decimal_places = 0
        else:
            value = format_number(value, max_digits, decimal_places)

        # Pad with zeroes to a constant width.
        n = value.find('.')
        if n < 0:
            n = len(value)
        if n < max_digits - decimal_places:
            value = u'0' * (max_digits - decimal_places - n) + value
        return sign + value

    def convert_values(self, value, field):
        """
        Decodes decimal encoding done in value_to_db_decimal, also
        casts AutoField values to ints (new entities may get a key
        with a long id from the datastore).
        """
        if value is None:
            return None

        field_kind = field.get_internal_type()

        if field_kind == 'AutoField':
            return int(value)
        elif field_kind == 'DecimalField':
            return decimal.Decimal(value)

        return value

    def value_for_db(self, value, field, field_kind, db_type, lookup):
        """
        GAE database may store a restricted set of Python types, for
        some cases it has its own types like Key, Text or Blob.

        TODO: Consider moving empty list handling here (from insert).
        """

        # Store Nones as Nones to handle nullable fields, even keys.
        if value is None:
            return None

        # Parent can handle iterable fields and Django wrappers.
        value = super(DatabaseOperations, self).value_for_db(
            value, field, field_kind, db_type, lookup)

        # Create GAE db.Keys from Django keys.
        if db_type == 'key':
#            value = self.encode_for_db_key(value, field_kind)
            try:

                # We use model's table name as key kind, but this has
                # to be the table of the model of the instance that the
                # key identifies, that's why for ForeignKeys and other
                # relations we'll use the table of the model the field
                # refers to.
                if field.rel is not None:
                    db_table = field.rel.to._meta.db_table
                else:
                    db_table = field.model._meta.db_table

                value = key_from_path(db_table, value)
            except (BadArgumentError, BadValueError,):
                raise DatabaseError("Only strings and positive integers "
                                    "may be used as keys on GAE.")

        # Store all strings as unicode, use db.Text for longer content.
        elif db_type == 'string' or db_type == 'text':
            if isinstance(value, str):
                value = value.decode('utf-8')
            if db_type == 'text':
                value = Text(value)

        # Store all date / time values as datetimes, by using some
        # default time or date.
        elif db_type == 'date':
            value = datetime.datetime.combine(value, self.DEFAULT_TIME)
        elif db_type == 'time':
            value = datetime.datetime.combine(self.DEFAULT_DATE, value)

        # Store BlobField, DictField and EmbeddedModelField values as Blobs.
        elif db_type == 'bytes':
            value = Blob(value)

        return value

    def value_from_db(self, value, field, field_kind, db_type):
        """
        Undoes conversions done in value_for_db.
        """

        # We could have stored None for a null field.
        if value is None:
            return None

        # All keys were converted to the Key class.
        if db_type == 'key':
            assert isinstance(value, Key), \
                "GAE db.Key expected! Try changing to old storage, " \
                "dumping data, changing to new storage and reloading."
            assert value.parent() is None, "Parents are not yet supported!"
            value = value.id_or_name()
#            value = self.decode_from_db_key(value, field_kind)

        # Always retrieve strings as unicode (old datasets may
        # contain non-unicode strings).
        elif db_type == 'string' or db_type == 'text':
            if isinstance(value, str):
                value = value.decode('utf-8')
            else:
                value = unicode(value)

        # Dates and times are stored as datetimes, drop the added part.
        elif db_type == 'date':
            value = value.date()
        elif db_type == 'time':
            value = value.time()

        # Convert GAE Blobs to plain strings for Django.
        elif db_type == 'bytes':
            value = str(value)

        return super(DatabaseOperations, self).value_from_db(
            value, field, field_kind, db_type)

#    def value_for_db_key(self, value, field_kind):
#        """
#        Converts values to be used as entity keys to strings,
#        trying (but not fully succeeding) to preserve comparisons.
#        """

#        # Bools as positive integers.
#        if field_kind == 'BooleanField':
#            value = int(value) + 1

#        # Encode floats as strings.
#        elif field_kind == 'FloatField':
#            value = self.value_to_db_decimal(
#                decimal.Decimal(value), None, None)

#        # Integers as strings (string keys sort after int keys, so
#        # all need to be encoded to preserve comparisons).
#        elif field_kind in ('IntegerField', 'BigIntegerField',
#           'PositiveIntegerField', 'PositiveSmallIntegerField',
#           'SmallIntegerField'):
#            value = self.value_to_db_decimal(
#                decimal.Decimal(value), None, 0)

#        return value

#    def value_from_db_key(self, value, field_kind):
#        """
#        Decodes value previously encoded in a key.
#        """
#        if field_kind == 'BooleanField':
#            value = bool(value - 1)
#        elif field_kind == 'FloatField':
#            value = float(value)
#        elif field_kind in ('IntegerField', 'BigIntegerField',
#           'PositiveIntegerField', 'PositiveSmallIntegerField',
#           'SmallIntegerField'):
#            value = int(value)

#        return value


class DatabaseClient(NonrelDatabaseClient):
    pass


class DatabaseValidation(NonrelDatabaseValidation):
    pass


class DatabaseIntrospection(NonrelDatabaseIntrospection):

    def table_names(self):
        """
        Returns a list of names of all tables that exist in the
        database.
        """
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
        """
        Helper function to remove the current datastore and re-open the
        stubs.
        """
        if stub_manager.active_stubs == 'remote':
            import random
            import string
            code = ''.join([random.choice(string.ascii_letters)
                            for x in range(4)])
            print "\n\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            print "Warning! You're about to delete the *production* datastore!"
            print "Only models defined in your INSTALLED_APPS can be removed!"
            print "If you want to clear the whole datastore you have to use " \
                  "the datastore viewer in the dashboard. Also, in order to " \
                  "delete all unneeded indexes you have to run appcfg.py " \
                  "vacuum_indexes."
            print "In order to proceed you have to enter the following code:"
            print code
            response = raw_input("Repeat: ")
            if code == response:
                print "Deleting..."
                delete_all_entities()
                print "Datastore flushed! Please check your dashboard's " \
                      "datastore viewer for any remaining entities and " \
                      "remove all unneeded indexes with appcfg.py " \
                      "vacuum_indexes."
            else:
                print "Aborting."
                exit()
        elif stub_manager.active_stubs == 'test':
            stub_manager.deactivate_test_stubs()
            stub_manager.activate_test_stubs()
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
