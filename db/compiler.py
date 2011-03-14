from .db_settings import get_model_indexes

import datetime
import sys

from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.constants import LOOKUP_SEP, MULTI, SINGLE
from django.db.models.sql.where import AND, OR
from django.db.utils import DatabaseError, IntegrityError
from django.utils.tree import Node

from functools import wraps

from google.appengine.api.datastore import Entity, Query, MultiQuery, \
    Put, Get, Delete, Key
from google.appengine.api.datastore_errors import Error as GAEError
from google.appengine.api.datastore_types import Text, Category, Email, Link, \
    PhoneNumber, PostalAddress, Text, Blob, ByteString, GeoPt, IM, Key, \
    Rating, BlobKey

from djangotoolbox.db.basecompiler import NonrelQuery, NonrelCompiler, \
    NonrelInsertCompiler, NonrelUpdateCompiler, NonrelDeleteCompiler

import cPickle as pickle

import decimal

# Valid query types (a dictionary is used for speedy lookups).
OPERATORS_MAP = {
    'exact': '=',
    'gt': '>',
    'gte': '>=',
    'lt': '<',
    'lte': '<=',

    # The following operators are supported with special code below:
    'isnull': None,
    'in': None,
    'startswith': None,
    'range': None,
    'year': None,
}

NEGATION_MAP = {
    'gt': '<=',
    'gte': '<',
    'lt': '>=',
    'lte': '>',
    # TODO: support these filters
    #'exact': '!=', # this might actually become individual '<' and '>' queries
}

def safe_call(func):
    @wraps(func)
    def _func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except GAEError, e:
            raise DatabaseError, DatabaseError(str(e)), sys.exc_info()[2]
    return _func

class GAEQuery(NonrelQuery):
    # ----------------------------------------------
    # Public API
    # ----------------------------------------------
    def __init__(self, compiler, fields):
        super(GAEQuery, self).__init__(compiler, fields)
        self.inequality_field = None
        self.pk_filters = None
        self.excluded_pks = ()
        self.has_negated_exact_filter = False
        self.ordering = ()
        self.gae_ordering = []
        pks_only = False
        if len(fields) == 1 and fields[0].primary_key:
            pks_only = True
        self.db_table = self.query.get_meta().db_table
        self.pks_only = pks_only
        start_cursor = getattr(self.query, '_gae_start_cursor', None)
        end_cursor = getattr(self.query, '_gae_end_cursor', None)
        self.gae_query = [Query(self.db_table, keys_only=self.pks_only,
                                cursor=start_cursor, end_cursor=end_cursor)]

    # This is needed for debugging
    def __repr__(self):
        return '<GAEQuery: %r ORDER %r>' % (self.gae_query, self.ordering)

    @safe_call
    def fetch(self, low_mark, high_mark):
        query = self._build_query()
        executed = False
        if self.excluded_pks and high_mark is not None:
            high_mark += len(self.excluded_pks)
        if self.pk_filters is not None:
            results = self.get_matching_pk(low_mark, high_mark)
        else:
            if high_mark is None:
                kw = {}
                if low_mark:
                    kw['offset'] = low_mark
                results = query.Run(**kw)
                executed = True
            elif high_mark > low_mark:
                results = query.Get(high_mark - low_mark, low_mark)
                executed = True
            else:
                results = ()

        for entity in results:
            if isinstance(entity, Key):
                key = entity
            else:
                key = entity.key()
            if key in self.excluded_pks:
                continue
            yield self._make_entity(entity)

        if executed and not isinstance(query, MultiQuery):
            self.query._gae_cursor = query.GetCompiledCursor()

    @safe_call
    def count(self, limit=None):
        if self.pk_filters is not None:
            return len(self.get_matching_pk(0, limit))
        if self.excluded_pks:
            return len(list(self.fetch(0, 2000)))
        kw = {}
        if limit is not None:
            kw['limit'] = limit
        return self._build_query().Count(**kw)

    @safe_call
    def delete(self):
        if self.pk_filters is not None:
            keys = [key for key in self.pk_filters if key is not None]
        else:
            keys = self.fetch()
        if keys:
            Delete(keys)

    @safe_call
    def order_by(self, ordering):
        self.ordering = ordering
        for order in self.ordering:
            if order.startswith('-'):
                order, direction = order[1:], Query.DESCENDING
            else:
                direction = Query.ASCENDING
            if order == self.query.get_meta().pk.column:
                order = '__key__'
            self.gae_ordering.append((order, direction))

    # This function is used by the default add_filters() implementation
    @safe_call
    def add_filter(self, column, lookup_type, negated, db_type, value):
        if value in ([], ()):
            self.pk_filters = []
            return

        # Emulated/converted lookups
        if column == self.query.get_meta().pk.column:
            column = '__key__'
            db_table = self.query.get_meta().db_table
            if lookup_type in ('exact', 'in'):
                # Optimization: batch-get by key
                if self.pk_filters is not None:
                    raise DatabaseError("You can't apply multiple AND filters "
                                        "on the primary key. "
                                        "Did you mean __in=[...]?")
                if not isinstance(value, (tuple, list)):
                    value = [value]
                pks = [create_key(db_table, pk) for pk in value if pk]
                if negated:
                    self.excluded_pks = pks
                else:
                    self.pk_filters = pks
                return
            else:
                # XXX: set db_type to 'gae_key' in order to allow
                # convert_value_for_db to recognize the value to be a Key and
                # not a str. Otherwise the key would be converted back to a
                # unicode (see convert_value_for_db)
                db_type = 'gae_key'
                key_type_error = 'Lookup values on primary keys have to be' \
                                 'a string or an integer.'
                if lookup_type == 'range':
                    if isinstance(value,(list, tuple)) and not(isinstance(
                            value[0], (basestring, int, long)) and \
                            isinstance(value[1], (basestring, int, long))):
                        raise DatabaseError(key_type_error)
                elif not isinstance(value,(basestring, int, long)):
                    raise DatabaseError(key_type_error)
                # for lookup type range we have to deal with a list
                if lookup_type == 'range':
                    value[0] = create_key(db_table, value[0])
                    value[1] = create_key(db_table, value[1])
                else:
                    value = create_key(db_table, value)
        if lookup_type not in OPERATORS_MAP:
            raise DatabaseError("Lookup type %r isn't supported" % lookup_type)

        # We check for negation after lookup_type isnull because it
        # simplifies the code. All following lookup_type checks assume
        # that they're not negated.
        if lookup_type == 'isnull':
            if (negated and value) or not value:
                # TODO/XXX: is everything greater than None?
                op = '>'
            else:
                op = '='
            value = None
        elif negated and lookup_type == 'exact':
            if self.has_negated_exact_filter:
                raise DatabaseError("You can't exclude more than one __exact "
                                    "filter")
            self.has_negated_exact_filter = True
            self._combine_filters(column, db_type,
                                  (('<', value), ('>', value)))
            return
        elif negated:
            try:
                op = NEGATION_MAP[lookup_type]
            except KeyError:
                raise DatabaseError("Lookup type %r can't be negated" % lookup_type)
            if self.inequality_field and column != self.inequality_field:
                raise DatabaseError("Can't have inequality filters on multiple "
                    "columns (here: %r and %r)" % (self.inequality_field, column))
            self.inequality_field = column
        elif lookup_type == 'in':
            # Create sub-query combinations, one for each value
            if len(self.gae_query) * len(value) > 30:
                raise DatabaseError("You can't query against more than "
                                    "30 __in filter value combinations")
            op_values = [('=', v) for v in value]
            self._combine_filters(column, db_type, op_values)
            return
        elif lookup_type == 'startswith':
            self._add_filter(column, '>=', db_type, value)
            if isinstance(value, str):
                value = value.decode('utf8')
            if isinstance(value, Key):
                value = list(value.to_path())
                if isinstance(value[-1], str):
                    value[-1] = value[-1].decode('utf8')
                value[-1] += u'\ufffd'
                value = Key.from_path(*value)
            else:
                value += u'\ufffd'
            self._add_filter(column, '<=', db_type, value)
            return
        elif lookup_type in ('range', 'year'):
            self._add_filter(column, '>=', db_type, value[0])
            op = '<=' if lookup_type == 'range' else '<'
            self._add_filter(column, op, db_type, value[1])
            return
        else:
            op = OPERATORS_MAP[lookup_type]

        self._add_filter(column, op, db_type, value)

    # ----------------------------------------------
    # Internal API
    # ----------------------------------------------
    def _add_filter(self, column, op, db_type, value):
        for query in self.gae_query:
            key = '%s %s' % (column, op)
            value = self.convert_value_for_db(db_type, value)
            if isinstance(value, Text):
                raise DatabaseError('TextField is not indexed, by default, '
                                    "so you can't filter on it. Please add "
                                    'an index definition for the column %s '
                                    'on the model %s.%s as described here:\n'
                                    'http://www.allbuttonspressed.com/blog/django/2010/07/Managing-per-field-indexes-on-App-Engine'
                                    % (column, self.query.model.__module__, self.query.model.__name__))
            if key in query:
                existing_value = query[key]
                if isinstance(existing_value, list):
                    existing_value.append(value)
                else:
                    query[key] = [existing_value, value]
            else:
                query[key] = value

    def _combine_filters(self, column, db_type, op_values):
        gae_query = self.gae_query
        combined = []
        for query in gae_query:
            for op, value in op_values:
                self.gae_query = [Query(self.db_table,
                                        keys_only=self.pks_only)]
                self.gae_query[0].update(query)
                self._add_filter(column, op, db_type, value)
                combined.append(self.gae_query[0])
        self.gae_query = combined

    def _make_entity(self, entity):
        if isinstance(entity, Key):
            key = entity
            entity = {}
        else:
            key = entity.key()

        entity[self.query.get_meta().pk.column] = key
        return entity

    @safe_call
    def _build_query(self):
        if len(self.gae_query) > 1:
            for i in self.gae_query:
                i.Order(*self.gae_ordering)
            return MultiQuery(self.gae_query, self.gae_ordering)
        query = self.gae_query[0]
        query.Order(*self.gae_ordering)
        return query

    def get_matching_pk(self, low_mark=0, high_mark=None):
        if not self.pk_filters:
            return []

        results = [result for result in Get(self.pk_filters)
                   if result is not None and
                       self.matches_filters(result)]
        if self.ordering:
            results.sort(cmp=self.order_pk_filtered)
        if high_mark is not None and high_mark < len(results) - 1:
            results = results[:high_mark]
        if low_mark:
            results = results[low_mark:]
        return results

    def order_pk_filtered(self, lhs, rhs):
        left = dict(lhs)
        left[self.query.get_meta().pk.column] = lhs.key().to_path()
        right = dict(rhs)
        right[self.query.get_meta().pk.column] = rhs.key().to_path()
        return self._order_in_memory(left, right)

    def matches_filters(self, entity):
        item = dict(entity)
        pk = self.query.get_meta().pk
        value = self.convert_value_from_db(pk.db_type(connection=self.connection),
            entity.key())
        item[pk.column] = value
        result = self._matches_filters(item, self.query.where)
        return result

class SQLCompiler(NonrelCompiler):
    """
    A simple App Engine query: no joins, no distinct, etc.
    """
    query_class = GAEQuery

    def convert_value_from_db(self, db_type, value):
        if isinstance(value, (list, tuple, set)) and \
                db_type.startswith(('ListField:', 'SetField:')):
            db_sub_type = db_type.split(':', 1)[1]
            value = [self.convert_value_from_db(db_sub_type, subvalue)
                     for subvalue in value]

        if db_type.startswith('SetField:') and value is not None:
            value = set(value)

        if db_type.startswith('DictField:') and value is not None:
            value = pickle.loads(value)
            if ':' in db_type:
                db_sub_type = db_type.split(':', 1)[1]
                value = dict((key, self.convert_value_from_db(db_sub_type, value[key]))
                             for key in value)

        # the following GAE database types are all unicode subclasses, cast them
        # to unicode so they appear like pure unicode instances for django
        if isinstance(value, basestring) and value and db_type.startswith('decimal'):
            value = decimal.Decimal(value)
        elif isinstance(value, (Category, Email, Link, PhoneNumber, PostalAddress,
                Text, unicode)):
            value = unicode(value)
        elif isinstance(value, Blob):
            value = str(value)
        elif isinstance(value, str):
            # always retrieve strings as unicode (it is possible that old datasets
            # contain non unicode strings, nevertheless work with unicode ones)
            value = value.decode('utf-8')
        elif isinstance(value, Key):
            # for now we do not support KeyFields thus a Key has to be the own
            # primary key
            # TODO: GAE: support parents via GAEKeyField
            assert value.parent() is None, "Parents are not yet supported!"
            if db_type == 'integer':
                if value.id() is None:
                    raise DatabaseError('Wrong type for Key. Expected integer, found'
                        'None')
                else:
                    value = value.id()
            elif db_type == 'text':
                if value.name() is None:
                    raise DatabaseError('Wrong type for Key. Expected string, found'
                        'None')
                else:
                    value = value.name()
            else:
                raise DatabaseError("%s fields cannot be keys on GAE" % db_type)
        elif db_type == 'date' and isinstance(value, datetime.datetime):
            value = value.date()
        elif db_type == 'time' and isinstance(value, datetime.datetime):
            value = value.time()
        return value

    def convert_value_for_db(self, db_type, value):
        if isinstance(value, unicode):
            value = unicode(value)
        elif isinstance(value, str):
            value = str(value)
        elif isinstance(value, (list, tuple, set)) and \
                db_type.startswith(('ListField:', 'SetField:')):
            db_sub_type = db_type.split(':', 1)[1]
            value = [self.convert_value_for_db(db_sub_type, subvalue)
                     for subvalue in value]
        elif isinstance(value, decimal.Decimal) and db_type.startswith("decimal:"):
            value = self.connection.ops.value_to_db_decimal(value, *eval(db_type[8:]))
        elif isinstance(value, dict) and db_type.startswith('DictField:'):
            if ':' in db_type:
                db_sub_type = db_type.split(':', 1)[1]
                value = dict([(key, self.convert_value_for_db(db_sub_type, value[key]))
                              for key in value])
            value = Blob(pickle.dumps(value))

        if db_type == 'gae_key':
            return value
        elif db_type == 'longtext':
            # long text fields cannot be indexed on GAE so use GAE's database
            # type Text
            value = Text((isinstance(value, str) and value.decode('utf-8')) or value)
        elif db_type == 'text':
            value = (isinstance(value, str) and value.decode('utf-8')) or value
        elif db_type == 'blob':
            value = Blob(value)
        elif type(value) is str:
            # always store unicode strings
            value = value.decode('utf-8')
        elif db_type == 'date' or db_type == 'time' or db_type == 'datetime':
            # here we have to check the db_type because GAE always stores datetimes
            value = to_datetime(value)
        return value

class SQLInsertCompiler(NonrelInsertCompiler, SQLCompiler):
    @safe_call
    def insert(self, data, return_id=False):
        gae_data = {}
        opts = self.query.get_meta()
        unindexed_fields = get_model_indexes(self.query.model)['unindexed']
        unindexed_cols = [opts.get_field(name).column
                          for name in unindexed_fields]
        kwds = {'unindexed_properties': unindexed_cols}
        for column, value in data.items():
            if column == opts.pk.column:
                if isinstance(value, basestring):
                    kwds['name'] = value
                else:
                    kwds['id'] = value
            elif isinstance(value, (tuple, list)) and not len(value):
                # gae does not store emty lists (and even does not allow passing empty
                # lists to Entity.update) so skip them
                continue
            else:
                gae_data[column] = value

        entity = Entity(self.query.get_meta().db_table, **kwds)
        entity.update(gae_data)
        key = Put(entity)
        return key.id_or_name()

class SQLUpdateCompiler(NonrelUpdateCompiler, SQLCompiler):
    pass

class SQLDeleteCompiler(NonrelDeleteCompiler, SQLCompiler):
    pass

def to_datetime(value):
    """Convert a time or date to a datetime for datastore storage.

    Args:
    value: A datetime.time, datetime.date or string object.

    Returns:
    A datetime object with date set to 1970-01-01 if value is a datetime.time
    A datetime object with date set to value.year - value.month - value.day and
    time set to 0:00 if value is a datetime.date
    """

    if value is None:
        return value
    elif isinstance(value, datetime.datetime):
        return value
    elif isinstance(value, datetime.date):
        return datetime.datetime(value.year, value.month, value.day)
    elif isinstance(value, datetime.time):
        return datetime.datetime(1970, 1, 1, value.hour, value.minute,
            value.second, value.microsecond)

def create_key(db_table, value):
    if isinstance(value, (int, long)) and value < 1:
        return None
    return Key.from_path(db_table, value)
