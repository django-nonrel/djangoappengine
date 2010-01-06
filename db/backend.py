import datetime
from django.conf import settings
from django.core import exceptions
from django.db.backends import BaseQueryBackend
from django.db.models.sql.datastructures import Empty
from django.db.models.sql.where import AND, OR
from django.utils.tree import Node
from google.appengine.api.datastore import Entity, Query, Put, Get, Delete, Key
from google.appengine.api.datastore_types import Text, Category, Email, Link, \
    PhoneNumber, PostalAddress, Text, Blob, ByteString, GeoPt, IM, Key, \
    Rating, BlobKey

# Valid query types (a dictionary is used for speedy lookups).
OPERATORS_MAP = {
    'exact': '=',
    'gt': '>',
    'gte': '>=',
    'lt': '<',
    'lte': '<=',
    'isnull': None,

    # The following operators are supported with special code below:
    # TODO: support these filters
    # in, range, startswith
}

NEGATION_MAP = {
    'gt': '<=',
    'gte': '<',
    'lt': '>=',
    'lte': '>',
    # TODO: support these filters
    #'exact': '!=', # this might actually become individual '<' and '>' queries
}

class QueryBackend(BaseQueryBackend):
    """
    A simple App Engine query: no joins, no distinct, etc.
    """
    operators_map = OPERATORS_MAP
    negation_map = NEGATION_MAP

    # ----------------------------------------------
    # Public API
    # ----------------------------------------------
    def results_iter(self):
        """
        Returns an iterator over the results from executing this query.
        """
        query, pk_filters, gae_filters = self.build_query()

        if pk_filters:
            results = self.get_matching_pk(pk_filters, gae_filters)
        else:
            low_mark, high_mark = self.limits
            results = query.Get(high_mark - low_mark, low_mark)

        for entity in results:
            # TODO: GAE: support parents via GAEKeyField
            assert entity.key().parent() is None, "Parents are not yet supported!"
            entity[self.querydata.get_meta().pk.column] = entity.key().id_or_name()
            # TODO: support lazy loading of fields
            result = []
            for field in self.querydata.get_meta().local_fields:
                if not field.null and entity.get(field.column,
                        field.default) is None:
                    raise ValueError("Non-nullable field %s can't be None!" % field.name)
                result.append(self.convert_value_from_db(field.db_type(),
                    entity.get(field.column, field.default)))
            yield result

    def get_count(self, check_exists=False):
        """
        Counts matches using the current filter constraints.
        """
        query, pk_filters, gae_filters = self.build_query()

        if pk_filters:
            return len(self.get_matching_pk(pk_filters, gae_filters))

        if check_exists:
            low_mark = 0
            high_mark = 1
        else:
            low_mark, high_mark = self.limits

        number = query.Count(high_mark)
        number = max(0, number - low_mark)
        return number

    def has_results(self):
        return self.get_count(check_exists=True)

    def insert(self, insert_values, raw_values=False, return_id=False):
        # Validate that non-nullable fields are not set to None
        for field, value in insert_values:
            if not field.null and value is None:
                raise ValueError("You can't set %s (a non-nullable field) to None!" % field.name)
        return self.insert_or_update(insert_values, raw_values, return_id)

    def delete_batch(self, pk_list):
        db_table = self.querydata.get_meta().db_table
        Delete([key for key in [create_key(db_table, pk) for pk in pk_list]
                if key is not None])

    # ----------------------------------------------
    # Internal API
    # ----------------------------------------------
    def insert_or_update(self, insert_values, raw_values, return_id):
        kwds = {}
        data = {}
        for field, value in insert_values:
            value = self.convert_value_for_db(field.db_type(), value)
            if field.primary_key:
                if isinstance(value, basestring):
                    kwds['name'] = value
                else:
                    kwds['id'] = value
            else:
                data[field.column] = value
        entity = Entity(self.querydata.get_meta().db_table, **kwds)
        entity.update(data)
        key = Put(entity)
        if return_id:
            return key.id_or_name()

    def build_query(self):
        query = Query(self.querydata.get_meta().db_table)
        # TODO/CLEANUP: The negation handling code could be moved into a separate base class
        # since it's reusable between non-relational backends.
        self.negated = False
        self.inequality_field = None

        pk_filters, gae_filters = self._add_filters_to_query(query, self.querydata.filters)

        del self.negated
        del self.inequality_field

        # TODO: Add select_related (maybe as separate class/layer, though)

        ordering = []
        for order in self.querydata.get_ordering():
            if order == '?':
                raise TypeError("Randomized ordering isn't supported by App Engine")
            if order.startswith('-'):
                order, direction = order[1:], Query.DESCENDING
            else:
                direction = Query.ASCENDING
            if order in (self.querydata.get_meta().pk.column, 'pk'):
                order = '__key__'
            ordering.append((order, direction))
        query.Order(*ordering)

        # TODO: FIXME: GAE: This at least satisfies the most basic unit tests
        if settings.DEBUG:
            from django import db
            db.connection.queries.append({})
        return query, pk_filters, gae_filters

    def _add_filters_to_query(self, query, filters):
        pk_filters, gae_filters = [], []
        if filters.negated:
            self.negated = not self.negated

        if not self.negated and filters.connector != AND:
            raise TypeError("Only AND filters are supported")
        if self.negated and filters.connector != OR and len(filters.children) > 1:
            raise TypeError("When negating a whole filter subgroup (e.g., a Q object) the "
                            "subgroup filters must be connected via OR ,so the App Engine "
                            "backend can convert them like this: "
                            '"not (a OR b) => (not a) AND (not b)".')

        for child in filters.children:
            if isinstance(child, Node):
                sub_pk_filters, sub_gae_filters = self._add_filters_to_query(
                    query, child)
                if sub_pk_filters:
                    if pk_filters:
                        raise TypeError("You can't apply multiple AND filters "
                                        "on the primary key. "
                                        "Did you mean __in=[...]?")
                    pk_filters = sub_pk_filters
                gae_filters.extend(sub_gae_filters)
                continue

            joins, db_table, column, is_primary_key, lookup_type, \
                field, value = child
            db_type = field.db_type()
            value = field.get_db_prep_lookup(lookup_type, value,
                connection=self.connection, prepared=True)

            if joins:
                raise TypeError("Joins aren't supported")

            # Django fields always return a list (see Field.get_db_prep_lookup)
            # except if get_db_prep_lookup got overridden by a subclass
            if lookup_type != 'in' and isinstance(value, (tuple, list)):
                if len(value) > 1:
                    raise TypeError('Filter lookup type was: %s. Expected the '
                                    'filters value not to be a list. Only "in"-filters '
                                    'can be used with lists.'
                                    % lookup_type)
                elif lookup_type == 'isnull':
                    value = None
                else:
                    value = value[0]

            # Emulated/converted lookups
            if is_primary_key:
                column = '__key__'
                if lookup_type in ('exact', 'in'):
                    if self.negated:
                        raise TypeError("You can't negate equality lookups on "
                                        "the primary key.")
                    if not isinstance(value, (tuple, list)):
                        value = [value]
                    pk_filters = [create_key(db_table, pk) for pk in value]
                    continue
                else:
                    # XXX: set db_type to 'gae_key' in order to allow
                    # convert_value_for_db to recognize the value to be a Key and
                    # not a str. Otherwise the key would be converted back to a
                    # unicode (see convert_value_for_db)
                    db_type = 'gae_key'
                    if not isinstance(value, (basestring, int, long)):
                        raise TypeError("Lookup values on primary keys have to be"
                                        " a string or an integer.")
                    value = create_key(db_table, value)

            if lookup_type not in self.operators_map:
                raise TypeError("Lookup type %r isn't supported" % lookup_type)

            if lookup_type == 'isnull':
                if self.negated:
                    # anything is greater than None
                    op = '>'
                else:
                    op = '='
            elif self.negated:
                try:
                    op = self.negation_map[lookup_type]
                except KeyError:
                    raise TypeError("Lookup type %r can't be negated" % lookup_type)
                if self.inequality_field and column != self.inequality_field:
                    raise TypeError("Can't have inequality filters on multiple "
                        "columns (here: %r and %r)" % (self.inequality_field, column))
                self.inequality_field = column
            else:
                op = self.operators_map[lookup_type]

            gae_filters.append((column, op, value))
            query["%s %s" % (column, op)] = self.convert_value_for_db(db_type,
                value)

        if filters.negated:
            self.negated = not self.negated

        return pk_filters, gae_filters

    @property
    def limits(self):
        high_mark = 301
        if self.querydata.high_mark is not None:
            high_mark = self.querydata.high_mark
        return self.querydata.low_mark, high_mark

    def get_matching_pk(self, pk_filters, gae_filters):
        pk_filters = [key for key in pk_filters if key is not None]
        if not pk_filters:
            return []

        results = [result for result in Get(pk_filters)
                   if result is not None
                       and matches_gae_filters(result, gae_filters)]
        if self.querydata.get_ordering():
            results.sort(cmp=self.order_pk_filtered)
        low_mark, high_mark = self.limits
        if high_mark < len(results) - 1:
            results = results[:high_mark]
        if low_mark:
            results = results[low_mark:]
        return results

    def order_pk_filtered(self, lhs, rhs):
        # TODO/CLEANUP: In-memory sorting should be moved into QueryData since it's reusable
        ordering = []
        for order in self.querydata.get_ordering():
            if order == '?':
                raise TypeError("Randomized ordering isn't supported by App Engine")
            column = order.lstrip('-')
            if column in (self.querydata.get_meta().pk.column, 'pk'):
                result = cmp(lhs.key().to_path(), rhs.key().to_path())
            else:
                result = cmp(lhs.get(column), rhs.get(column))
            if order.startswith('-'):
                result *= -1
            if result != 0:
                return result
        return 0

    def convert_value_from_db(self, db_type, value):
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
        elif isinstance(value, Key) and data_type == 'integer':
            if value.id() == None:
                raise TypeError('Wrong type for Key. Excepted integer found' \
                    'None or string')
            else:
                value = value.id()
        elif isinstance(value, Key) and data_type == 'text':
            if value.name() == None:
                raise TypeError('Wrong type for Key. Excepted string found' \
                    'None or id')
            else:
                value = value.name()
        elif isinstance(value, Key) and data_type == 'longtext':
            raise TypeError("Long text fields cannot be keys on GAE")
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

# TODO/CLEANUP: Filter emulation should become part of QueryData because it's backend independent
EMULATED_OPS = {
    '=': lambda x, y: x == y,
    'in': lambda x, y: x in y,
    '<': lambda x, y: x < y,
    '<=': lambda x, y: x <= y,
    '>': lambda x, y: x > y,
    '>=': lambda x, y: x >= y,
}

def matches_gae_filters(entity, gae_filters):
    for column, op, value in gae_filters:
        if op not in EMULATED_OPS:
            raise ValueError('Invalid App Engine filter: %s %s' % (filter, value))
        if not EMULATED_OPS[op](entity[column], value):
            return False
    return True
