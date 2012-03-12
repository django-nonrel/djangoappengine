from functools import wraps
import sys

from django.db.models.fields import AutoField
from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.constants import LOOKUP_SEP, MULTI, SINGLE
from django.db.models.sql.where import AND, OR
from django.db.utils import DatabaseError, IntegrityError
from django.utils.tree import Node

from google.appengine.api.datastore import Entity, Query, MultiQuery, \
    Put, Get, Delete
from google.appengine.api.datastore_errors import Error as GAEError
from google.appengine.api.datastore_types import Key, Text

from djangotoolbox.db.basecompiler import (
    NonrelQuery,
    NonrelCompiler,
    NonrelInsertCompiler,
    NonrelUpdateCompiler,
    NonrelDeleteCompiler)

from .db_settings import get_model_indexes
from .expressions import ExpressionEvaluator
from .utils import commit_locked


# Valid query types (a dictionary is used for speedy lookups).
OPERATORS_MAP = {
    'exact': '=',
    'gt': '>',
    'gte': '>=',
    'lt': '<',
    'lte': '<=',

    # The following operators are supported with special code below.
    'isnull': None,
    'in': None,
    'startswith': None,
    'range': None,
    'year': None,
}

# GAE filters used for negated Django lookups.
NEGATION_MAP = {
    'gt': '<=',
    'gte': '<',
    'lt': '>=',
    'lte': '>',
    # TODO: Support: "'exact': '!='" (it might actually become
    #       individual '<' and '>' queries).
}

# In some places None is an allowed value, and we need to distinguish
# it from the lack of value.
NOT_PROVIDED = object()


def safe_call(func):
    """
    Causes the decorated function to reraise GAE datastore errors as
    Django DatabaseErrors.
    """

    @wraps(func)
    def _func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except GAEError, e:
            raise DatabaseError, DatabaseError(str(e)), sys.exc_info()[2]
    return _func


class GAEQuery(NonrelQuery):
    """
    A simple App Engine query: no joins, no distinct, etc.
    """

    # ----------------------------------------------
    # Public API
    # ----------------------------------------------

    def __init__(self, compiler, fields):
        super(GAEQuery, self).__init__(compiler, fields)
        self.inequality_field = None
        self.included_pks = None
        self.excluded_pks = ()
        self.has_negated_exact_filter = False
        self.ordering = []
        self.db_table = self.query.get_meta().db_table
        self.pks_only = (len(fields) == 1 and fields[0].primary_key)
        start_cursor = getattr(self.query, '_gae_start_cursor', None)
        end_cursor = getattr(self.query, '_gae_end_cursor', None)
        self.gae_query = [Query(self.db_table, keys_only=self.pks_only,
                                cursor=start_cursor, end_cursor=end_cursor)]

    # This is needed for debugging.
    def __repr__(self):
        return '<GAEQuery: %r ORDER %r>' % (self.gae_query, self.ordering)

    @safe_call
    def fetch(self, low_mark, high_mark):
        query = self._build_query()
        executed = False
        if self.excluded_pks and high_mark is not None:
            high_mark += len(self.excluded_pks)
        if self.included_pks is not None:
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
            try:
                self.query._gae_cursor = query.GetCompiledCursor()
            except:
                pass

    @safe_call
    def count(self, limit=NOT_PROVIDED):
        if self.included_pks is not None:
            return len(self.get_matching_pk(0, limit))
        if self.excluded_pks:
            return len(list(self.fetch(0, 2000)))
        # The datastore's Count() method has a 'limit' kwarg, which has
        # a default value (obviously).  This value can be overridden to
        # anything you like, and importantly can be overridden to
        # unlimited by passing a value of None.  Hence *this* method
        # has a default value of NOT_PROVIDED, rather than a default
        # value of None
        kw = {}
        if limit is not NOT_PROVIDED:
            kw['limit'] = limit
        return self._build_query().Count(**kw)

    @safe_call
    def delete(self):
        if self.included_pks is not None:
            keys = [key for key in self.included_pks if key is not None]
        else:
            keys = self.fetch()
        if keys:
            Delete(keys)

    @safe_call
    def order_by(self, ordering):

        # GAE doesn't have any kind of natural ordering?
        if not isinstance(ordering, bool):
            for field, ascending in ordering:
                column = '__key__' if field.primary_key else field.column
                direction = Query.ASCENDING if ascending else Query.DESCENDING
                self.ordering.append((column, direction))


    @safe_call
    def add_filter(self, field, lookup_type, negated, value):
        """
        This function is used by the default add_filters()
        implementation.
        """
        if lookup_type not in OPERATORS_MAP:
            raise DatabaseError("Lookup type %r isn't supported." %
                                lookup_type)

        # GAE does not let you store empty lists, so we can tell
        # upfront that queriying for one will return nothing.
        if value in ([], ()):
            self.included_pks = []
            return

        # Optimization: batch-get by key; this is only suitable for
        # primary keys, not for anything that uses the key type.
        if field.primary_key and lookup_type in ('exact', 'in'):
            if self.included_pks is not None:
                raise DatabaseError("You can't apply multiple AND "
                                    "filters on the primary key. "
                                    "Did you mean __in=[...]?")
            if not isinstance(value, (tuple, list)):
                value = [value]
            pks = [pk for pk in value if pk is not None]
            if negated:
                self.excluded_pks = pks
            else:
                self.included_pks = pks
            return

        # We check for negation after lookup_type isnull because it
        # simplifies the code. All following lookup_type checks assume
        # that they're not negated.
        if lookup_type == 'isnull':
            if (negated and value) or not value:
                # TODO/XXX: Is everything greater than None?
                op = '>'
            else:
                op = '='
            value = None
        elif negated and lookup_type == 'exact':
            if self.has_negated_exact_filter:
                raise DatabaseError("You can't exclude more than one __exact "
                                    "filter.")
            self.has_negated_exact_filter = True
            self._combine_filters(field, (('<', value), ('>', value)))
            return
        elif negated:
            try:
                op = NEGATION_MAP[lookup_type]
            except KeyError:
                raise DatabaseError("Lookup type %r can't be negated." %
                                    lookup_type)
            if self.inequality_field and field != self.inequality_field:
                raise DatabaseError("Can't have inequality filters on "
                                    "multiple fields (here: %r and %r)." %
                                    (field, self.inequality_field))
            self.inequality_field = field
        elif lookup_type == 'in':
            # Create sub-query combinations, one for each value.
            if len(self.gae_query) * len(value) > 30:
                raise DatabaseError("You can't query against more than "
                                    "30 __in filter value combinations.")
            op_values = [('=', v) for v in value]
            self._combine_filters(field, op_values)
            return
        elif lookup_type == 'startswith':
            # Lookup argument was converted to [arg, arg + u'\ufffd'].
            self._add_filter(field, '>=', value[0])
            self._add_filter(field, '<=', value[1])
            return
        elif lookup_type in ('range', 'year'):
            self._add_filter(field, '>=', value[0])
            op = '<=' if lookup_type == 'range' else '<'
            self._add_filter(field, op, value[1])
            return
        else:
            op = OPERATORS_MAP[lookup_type]

        self._add_filter(field, op, value)

    # ----------------------------------------------
    # Internal API
    # ----------------------------------------------

    def _add_filter(self, field, op, value):
        for query in self.gae_query:

            # GAE uses a special property name for primary key filters.
            if field.primary_key:
                column = '__key__'
            else:
                column = field.column
            key = '%s %s' % (column, op)

            if isinstance(value, Text):
                raise DatabaseError("TextField is not indexed, by default, "
                                    "so you can't filter on it. Please add "
                                    "an index definition for the field %s "
                                    "on the model %s.%s as described here:\n"
                                    "http://www.allbuttonspressed.com/blog/django/2010/07/Managing-per-field-indexes-on-App-Engine" %
                                    (column, self.query.model.__module__,
                                     self.query.model.__name__))
            if key in query:
                existing_value = query[key]
                if isinstance(existing_value, list):
                    existing_value.append(value)
                else:
                    query[key] = [existing_value, value]
            else:
                query[key] = value

    def _combine_filters(self, field, op_values):
        gae_query = self.gae_query
        combined = []
        for query in gae_query:
            for op, value in op_values:
                self.gae_query = [Query(self.db_table,
                                        keys_only=self.pks_only)]
                self.gae_query[0].update(query)
                self._add_filter(field, op, value)
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
        for query in self.gae_query:
            query.Order(*self.ordering)
        if len(self.gae_query) > 1:
            return MultiQuery(self.gae_query, self.ordering)
        return self.gae_query[0]

    def get_matching_pk(self, low_mark=0, high_mark=None):
        if not self.included_pks:
            return []
        results = [result for result in Get(self.included_pks)
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
        """
        Checks if the GAE entity fetched from the database satisfies
        the current query's constraints.
        """
        item = dict(entity)
        item[self.query.get_meta().pk.column] = entity.key()
        return self._matches_filters(item, self.query.where)


class SQLCompiler(NonrelCompiler):
    """
    Base class for all GAE compilers.
    """
    query_class = GAEQuery


class SQLInsertCompiler(NonrelInsertCompiler, SQLCompiler):

    @safe_call
    def insert(self, data, return_id=False):
        opts = self.query.get_meta()
        unindexed_fields = get_model_indexes(self.query.model)['unindexed']
        kwds = {'unindexed_properties': []}
        properties = {}
        for field, value in data.iteritems():

            # The value will already be a db.Key, but the Entity
            # constructor takes a name or id of the key, and will
            # automatically create a new key if neither is given.
            if field.primary_key:
                if value is not None:
                    kwds['id'] = value.id()
                    kwds['name'] = value.name()

            # GAE does not store empty lists (and even does not allow
            # passing empty lists to Entity.update) so skip them.
            elif isinstance(value, (tuple, list)) and not len(value):
                continue

            # Use column names as property names.
            else:
                properties[field.column] = value

            if field in unindexed_fields:
                kwds['unindexed_properties'].append(field.column)

        entity = Entity(opts.db_table, **kwds)
        entity.update(properties)
        return Put(entity)


class SQLUpdateCompiler(NonrelUpdateCompiler, SQLCompiler):

    def execute_sql(self, result_type=MULTI):
        # Modify query to fetch pks only and then execute the query
        # to get all pks.
        pk_field = self.query.model._meta.pk
        self.query.add_immediate_loading([pk_field.name])
        pks = [row for row in self.results_iter()]
        self.update_entities(pks, pk_field)
        return len(pks)

    def update_entities(self, pks, pk_field):
        for pk in pks:
            self.update_entity(pk[0], pk_field)

    @commit_locked
    def update_entity(self, pk, pk_field):
        gae_query = self.build_query()
        entity = Get(self.ops.value_for_db(pk, pk_field))

        if not gae_query.matches_filters(entity):
            return

        for field, _, value in self.query.values:
            if hasattr(value, 'prepare_database_save'):
                value = value.prepare_database_save(field)
            else:
                value = field.get_db_prep_save(value,
                                               connection=self.connection)

            if hasattr(value, 'evaluate'):
                assert not value.negated
                assert not value.subtree_parents
                value = ExpressionEvaluator(value, self.query, entity,
                                            allow_joins=False)

            if hasattr(value, 'as_sql'):
                value = value.as_sql(lambda n: n, self.connection)

            entity[field.column] = self.ops.value_for_db(value, field)

        Put(entity)


class SQLDeleteCompiler(NonrelDeleteCompiler, SQLCompiler):
    pass
