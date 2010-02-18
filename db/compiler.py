import datetime
import sys

from django.conf import settings
from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.constants import LOOKUP_SEP, MULTI, SINGLE
from django.db.models.sql.where import AND, OR
from django.db.utils import DatabaseError, IntegrityError
from django.utils.tree import Node

from google.appengine.api.datastore import Entity, Query, Put, Get, Delete, Key
from google.appengine.api.datastore_errors import Error as GAEError
from google.appengine.api.datastore_types import Text, Category, Email, Link, \
    PhoneNumber, PostalAddress, Text, Blob, ByteString, GeoPt, IM, Key, \
    Rating, BlobKey

from .basecompiler import NonrelCompiler

# Valid query types (a dictionary is used for speedy lookups).
OPERATORS_MAP = {
    'exact': '=',
    'gt': '>',
    'gte': '>=',
    'lt': '<',
    'lte': '<=',

    # The following operators are supported with special code below:
    'isnull': None,
    'startswith': None,

    # TODO: support these filters
    # in, range
}

NEGATION_MAP = {
    'gt': '<=',
    'gte': '<',
    'lt': '>=',
    'lte': '>',
    # TODO: support these filters
    #'exact': '!=', # this might actually become individual '<' and '>' queries
}

class SQLCompiler(NonrelCompiler):
    """
    A simple App Engine query: no joins, no distinct, etc.
    """

    # ----------------------------------------------
    # Public API
    # ----------------------------------------------
    def execute_sql(self, result_type=MULTI):
        """
        Handles aggregate/count queries
        """
        aggregates = self.query.aggregate_select.values()
        # Simulate a count()
        if aggregates:
            assert len(aggregates) == 1
            aggregate = aggregates[0]
            assert isinstance(aggregate, sqlaggregates.Count)
            meta = self.query.get_meta()
            assert aggregate.col == '*' or aggregate.col == (meta.db_table, meta.pk.column)
            try:
                count = self.get_count()
            except GAEError, e:
                raise DatabaseError, DatabaseError(*tuple(e)), sys.exc_info()[2]
            if result_type is SINGLE:
                return [count]
            elif result_type is MULTI:
                return [[count]]
        raise NotImplementedError('The App Engine backend only supports count() queries')

    def results_iter(self):
        """
        Returns an iterator over the results from executing this query.
        """
        try:
            fields = None
            if fields is None:
                fields = self.get_fields()

            pks_only = False
            if len(fields) == 1 and fields[0].primary_key:
                pks_only = True

            query, pk_filters = self.build_query(pks_only=pks_only)

            if pk_filters:
                results = self.get_matching_pk(pk_filters)
            else:
                low_mark, high_mark = self.limits
                if high_mark is None:
                    results = query.Run(offset=low_mark, prefetch_count=25,
                                        next_count=75)
                elif high_mark > low_mark:
                    results = query.Get(high_mark - low_mark, low_mark)
                else:
                    results = ()

            for entity in results:
                yield self._make_result(entity, fields)
        except GAEError, e:
            raise DatabaseError, DatabaseError(*tuple(e)), sys.exc_info()[2]

    def has_results(self):
        return self.get_count(check_exists=True)

    # ----------------------------------------------
    # Internal API
    # ----------------------------------------------
    def get_count(self, check_exists=False):
        """
        Counts matches using the current filter constraints.
        """
        query, pk_filters = self.build_query()

        if pk_filters:
            return len(self.get_matching_pk(pk_filters))

        if check_exists:
            high_mark = 1
        else:
            high_mark = self.limits[1]

        return query.Count(high_mark)

    def _make_result(self, entity, fields):
        if isinstance(entity, Key):
            key = entity
            entity = {}
        else:
            key = entity.key()

        entity[self.query.get_meta().pk.column] = key
        # TODO: support lazy loading of fields
        result = []
        for field in fields:
            if not field.null and entity.get(field.column,
                    field.get_default()) is None:
                raise ValueError("Non-nullable field %s can't be None!" % field.name)
            result.append(self.convert_value_from_db(field.db_type(
                connection=self.connection), entity.get(field.column, field.get_default())))
        return result

    def build_query(self, pks_only=False):
        query = Query(self.query.get_meta().db_table, keys_only=pks_only)
        self.negated = False
        self.inequality_field = None

        pk_filters = self._add_filters_to_query(query, self.query.where)

        del self.negated
        del self.inequality_field

        # TODO: Add select_related (maybe as separate class/layer, though)

        ordering = []
        for order in self._get_ordering():
            if order == '?':
                raise Error("Randomized ordering isn't supported on App Engine")
            if LOOKUP_SEP in order:
                raise DatabaseError("Ordering can't span tables on App Engine (%s)" % order)
            if order.startswith('-'):
                order, direction = order[1:], Query.DESCENDING
            else:
                direction = Query.ASCENDING
            if order in (self.query.get_meta().pk.column, 'pk'):
                order = '__key__'
            ordering.append((order, direction))
        query.Order(*ordering)

        # This at least satisfies the most basic unit tests
        if settings.DEBUG:
            self.connection.queries.append({'sql': '%r ORDER %r' % (query, ordering)})
        return query, pk_filters

    def _add_filters_to_query(self, query, filters):
        pk_filters = []
        if filters.negated:
            self.negated = not self.negated

        if not self.negated and filters.connector != AND:
            raise DatabaseError("Only AND filters are supported")

        # Remove unneeded children from tree
        children = self._get_children(filters.children)

        if self.negated and filters.connector != OR and len(children) > 1:
            raise DatabaseError("When negating a whole filter subgroup (e.g., a Q "
                            "object) the subgroup filters must be connected "
                            "via OR, so the App Engine backend can convert "
                            "them like this: "
                            '"not (a OR b) => (not a) AND (not b)".')

        for child in children:
            if isinstance(child, Node):
                sub_pk_filters = self._add_filters_to_query(query, child)
                if sub_pk_filters:
                    if pk_filters:
                        raise DatabaseError("You can't apply multiple AND filters "
                                        "on the primary key. "
                                        "Did you mean __in=[...]?")
                    pk_filters = sub_pk_filters
                continue

            constraint, lookup_type, annotation, value = child
            assert hasattr(constraint, 'process')
            packed, value = constraint.process(lookup_type, value, self.connection)
            alias, column, db_type = packed
            value = self._normalize_lookup_value(value, annotation, lookup_type)

            # TODO: Add more reliable check that also works with JOINs
            is_primary_key = column == self.query.get_meta().pk.column
            # TODO: fill with real data
            joins = None
            db_table = self.query.get_meta().db_table

            if joins:
                raise DatabaseError("Joins aren't supported")

            if lookup_type == 'startswith':
                value = value[:-1]

            # Emulated/converted lookups
            if is_primary_key:
                column = '__key__'
                if lookup_type in ('exact', 'in'):
                    # Optimization: batch-get by key
                    if self.negated:
                        raise DatabaseError("You can't negate equality lookups on "
                                        "the primary key.")
                    if not isinstance(value, (tuple, list)):
                        value = [value]
                    pk_filters = [create_key(db_table, pk) for pk in value if pk]
                    continue
                else:
                    # XXX: set db_type to 'gae_key' in order to allow
                    # convert_value_for_db to recognize the value to be a Key and
                    # not a str. Otherwise the key would be converted back to a
                    # unicode (see convert_value_for_db)
                    db_type = 'gae_key'
                    if not isinstance(value, (basestring, int, long)):
                        raise DatabaseError("Lookup values on primary keys have to be"
                                        " a string or an integer.")
                    value = create_key(db_table, value)

            if lookup_type not in OPERATORS_MAP:
                raise DatabaseError("Lookup type %r isn't supported" % lookup_type)

            if lookup_type == 'isnull':
                if (self.negated and value) or not value:
                    # TODO/XXX: is everything greater than None?
                    op = '>'
                else:
                    op = '='
                value = None
            elif self.negated:
                try:
                    op = NEGATION_MAP[lookup_type]
                except KeyError:
                    raise DatabaseError("Lookup type %r can't be negated" % lookup_type)
                if self.inequality_field and column != self.inequality_field:
                    raise DatabaseError("Can't have inequality filters on multiple "
                        "columns (here: %r and %r)" % (self.inequality_field, column))
                self.inequality_field = column
            elif lookup_type == 'startswith':
                op = '>='
                query["%s %s" % (column, op)] = self.convert_value_for_db(
                    db_type, value)
                op = '<='
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
                query["%s %s" % (column, op)] = self.convert_value_for_db(
                    db_type, value)
                continue
            else:
                op = OPERATORS_MAP[lookup_type]

            query["%s %s" % (column, op)] = self.convert_value_for_db(db_type,
                value)

        if filters.negated:
            self.negated = not self.negated

        return pk_filters

    @property
    def limits(self):
        return self.query.low_mark, self.query.high_mark

    def get_matching_pk(self, pk_filters):
        pk_filters = [key for key in pk_filters if key is not None]
        if not pk_filters:
            return []

        results = [result for result in Get(pk_filters)
                   if result is not None
                       and self.matches_filters(result)]
        if self._get_ordering():
            results.sort(cmp=self.order_pk_filtered)
        low_mark, high_mark = self.limits
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

    def convert_value_from_db(self, db_type, value):
        if isinstance(value, (list, tuple)) and len(value) and \
                db_type.startswith('ListField:'):
            db_sub_type = db_type.split('ListField:')[1]
            for i, val in enumerate(value):
                value[i] = self.convert_value_from_db(db_sub_type, val)

        # the following GAE database types are all unicode subclasses, cast them
        # to unicode so they appear like pure unicode instances for django
        if isinstance(value, (Category, Email, Link, PhoneNumber, PostalAddress,
                Text, unicode)):
            value = unicode(value)
        # always retrieve strings as unicode (it is possible that old datasets
        # contain non unicode strings, nevertheless work with unicode ones)
        elif isinstance(value, str):
            value = value.decode('utf-8')
#        elif isinstance(value, Blob):
#        elif isinstance(value, ByteString):
#        TODO: convert GeoPt to a field used by geo-django (or some other geo
#        app for django)
#        elif isinstance(value, GeoPt):
#        elif isinstance(value, IM):
        # for now we do not support KeyFields thus a Key has to be the own
        # primary key
        elif isinstance(value, Key):
            # TODO: GAE: support parents via GAEKeyField
            assert value.parent() is None, "Parents are not yet supported!"
            if db_type == 'integer':
                if value.id() == None:
                    raise DatabaseError('Wrong type for Key. Excepted integer found' \
                        'None or string')
                else:
                    value = value.id()
            elif db_type == 'text':
                if value.name() == None:
                    raise DatabaseError('Wrong type for Key. Excepted string found' \
                        'None or id')
                else:
                    value = value.name()
            else:
                raise DatabaseError("%s fields cannot be keys on GAE" % db_type)
#        TODO: Use long in order to simulate decimal?
#        elif isinstance(value, long):
#        elif isinstance(value, Rating):
#        elif isinstance(value, users.User):
#        elif isinstance(value, BlobKey):

        # here we have to check the db_type because GAE always stores datetime
        # instances
        elif db_type == 'date' and isinstance(value, datetime.datetime):
            value = value.date()
        elif db_type == 'time' and isinstance(value, datetime.datetime):
            value = value.time()
        elif db_type == 'datetime' and isinstance(value, datetime.datetime):
            value = value
        return value

    def convert_value_for_db(self, db_type, value):
        if isinstance(value, (list, tuple)) and len(value) and \
                db_type.startswith('ListField:'):
            db_sub_type = db_type.split('ListField:')[1]
            for i, val in enumerate(value):
                value[i] = self.convert_value_for_db(db_sub_type, val)
        # long text fields cannot be indexed on GAE so use GAE's database type
        # Text
        if db_type == 'gae_key':
            return value
        if db_type == 'longtext':
            value = Text((isinstance(value, str) and value.decode('utf-8')) or value)
        elif db_type == 'text':
            value = (isinstance(value, str) and value.decode('utf-8')) or value
        # the following types (CommaSeparatedIntegerField, Emailfield, SlugField,
        # UrlField) will not be recogniced cause they inherit from
        # CharField and CharField overrides get_internal_type such that we will
        # get 'text' as the db_type even if we provide some different mapping in
        # creation.DatabaseCreation.data_types
#        elif db_type == 'email':
#            value = Email((isinstance(value, str) and value.decode('utf-8')) or \
#                value)
#        elif db_type == 'link':
#            value = Link((isinstance(value, str) and value.decode('utf-8')) or \
#                value)
        # always store unicode strings
        elif type(value) is str:
            value = value.decode('utf-8')
        # here we have to check the db_type because GAE always stores datetimes
        elif db_type == 'date' or db_type == 'time' or db_type == 'datetime':
            value = to_datetime(value)
        return value

class SQLInsertCompiler(SQLCompiler):
    def execute_sql(self, return_id=False):
        kwds = {}
        data = {}
        for (field, value), column in zip(self.query.values, self.query.columns):
            if field is not None:
                if not field.null and value is None:
                    raise ValueError("You can't set %s (a non-nullable field) "
                                     "to None!" % field.name)
                value = self.convert_value_for_db(field.db_type(connection=self.connection),
                    value)
            if column == self.query.get_meta().pk.name:
                if isinstance(value, basestring):
                    kwds['name'] = value
                else:
                    kwds['id'] = value
            # gae does not store emty lists (and even does not allow passing empty
            # lists to Entity.update) so skip them
            elif isinstance(value, (tuple, list)) and not len(value):
                continue
            else:
                data[column] = value

        try:
            entity = Entity(self.query.get_meta().db_table, **kwds)
            entity.update(data)
            key = Put(entity)
            return key.id_or_name()
        except GAEError, e:
            raise DatabaseError, DatabaseError(*tuple(e)), sys.exc_info()[2]

class SQLUpdateCompiler(SQLCompiler):
    def execute_sql(self, result_type=MULTI):
        # TODO: Implement me
        print 'NO UPDATE'
        pass

class SQLDeleteCompiler(SQLCompiler):
    def execute_sql(self, result_type=MULTI):
        try:
            query, pk_filters = self.build_query()
            assert not query, 'Deletion queries must only consist of pk filters!'
            if pk_filters:
                Delete([key for key in pk_filters if key is not None])
        except GAEError, e:
            raise DatabaseError, DatabaseError(*tuple(e)), sys.exc_info()[2]

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

def empty_iter():
    """
    Returns an iterator containing no results.
    """
    yield iter([]).next()

def create_key(db_table, value):
    if isinstance(value, (int, long)) and value < 1:
        return None
    return Key.from_path(db_table, value)
