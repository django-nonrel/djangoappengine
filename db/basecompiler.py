from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.constants import LOOKUP_SEP
from django.db.models.sql.where import AND, OR
from django.db.utils import DatabaseError, IntegrityError
from django.utils.tree import Node
import random

EMULATED_OPS = {
    'exact': lambda x, y: x == y,
    'iexact': lambda x, y: x.lower() == y.lower(),
    'startswith': lambda x, y: x.startswith(y),
    'istartswith': lambda x, y: x.lower().startswith(y.lower()),
    'isnull': lambda x, y: x is None if y else x is not None,
    'in': lambda x, y: x in y,
    'lt': lambda x, y: x < y,
    'lte': lambda x, y: x <= y,
    'gt': lambda x, y: x > y,
    'gte': lambda x, y: x >= y,
}

class NonrelCompiler(SQLCompiler):
    """
    Base class for non-relational compilers. Provides in-memory filter matching
    and ordering. Entities are assumed to be dictionaries where the keys are
    column names.
    """

    def get_fields(self):
        """
        Returns the fields which should get loaded from the backend by self.query        
        """
        # We only set this up here because
        # related_select_fields isn't populated until
        # execute_sql() has been called.
        if self.query.select_fields:
            fields = self.query.select_fields + self.query.related_select_fields
        else:
            fields = self.query.model._meta.fields
        # If the field was deferred, exclude it from being passed
        # into `resolve_columns` because it wasn't selected.
        only_load = self.deferred_to_columns()
        if only_load:
            db_table = self.query.model._meta.db_table
            fields = [f for f in fields if db_table in only_load and
                      f.column in only_load[db_table]]
        return fields

    def _normalize_lookup_value(self, value, annotation, lookup_type):
        # Django fields always return a list (see Field.get_db_prep_lookup)
        # except if get_db_prep_lookup got overridden by a subclass
        if lookup_type != 'in' and isinstance(value, (tuple, list)):
            if len(value) > 1:
                raise DatabaseError('Filter lookup type was: %s. Expected the '
                                'filters value not to be a list. Only "in"-filters '
                                'can be used with lists.'
                                % lookup_type)
            elif lookup_type == 'isnull':
                value = annotation
            else:
                value = value[0]

        if isinstance(value, unicode):
            value = unicode(value)
        elif isinstance(value, str):
            value = str(value)

        return value

    def _get_children(self, children):
        # Filter out nodes that were automatically added by sql.Query, but are
        # not necessary with emulated negation handling code
        result = []
        for child in children:
            if isinstance(child, Node) and child.negated and \
                    len(child.children) == 1 and \
                    isinstance(child.children[0], tuple):
                node, lookup_type, annotation, value = child.children[0]
                if lookup_type == 'isnull' and value == True and node.field is None:
                    continue
            result.append(child)
        return result

    def _matches_filters(self, entity, filters):
        # Filters without rules match everything
        if not filters.children:
            return True

        result = filters.connector == AND

        for child in filters.children:
            if isinstance(child, Node):
                submatch = self._matches_filters(entity, child)
            else:
                constraint, lookup_type, annotation, value = child
                packed, value = constraint.process(lookup_type, value, self.connection)
                alias, column, db_type = packed

                # Django fields always return a list (see Field.get_db_prep_lookup)
                # except if get_db_prep_lookup got overridden by a subclass
                if lookup_type != 'in' and isinstance(value, (tuple, list)):
                    if len(value) > 1:
                        raise TypeError('Filter lookup type was: %s. Expected the '
                                        'filters value not to be a list. Only "in"-filters '
                                        'can be used with lists.'
                                        % lookup_type)
                    elif lookup_type == 'isnull':
                        value = annotation
                    else:
                        value = value[0]

                submatch = EMULATED_OPS[lookup_type](entity[column], value)

            if filters.connector == OR and submatch:
                result = True
                break
            elif filters.connector == AND and not submatch:
                result = False
                break

        if filters.negated:
            return not result
        return result

    def _get_ordering(self):
        # TODO: Support JOINs
        if not self.query.default_ordering:
            ordering = self.query.order_by
        else:
            ordering = self.query.order_by or self.query.get_meta().ordering
        result = []
        for order in ordering:
            if order == '?':
                result.append(order)
                continue
            order = order.lstrip('+')

            descending = order.startswith('-')
            name = order.lstrip('-')
            if name == 'pk':
                name = self.query.get_meta().pk.name
                order = '-' + name if descending else name

            if self.query.standard_ordering:
                result.append(order)
            else:
                if descending:
                    result.append(name)
                else:
                    result.append('-' + name)
        return result

    def _order_in_memory(self, lhs, rhs):
        ordering = []
        for order in self._get_ordering():
            if LOOKUP_SEP in order:
                raise TypeError("JOINs in ordering not supported (%s)" % order)
            if order == '?':
                result = random.choice([1, 0, -1])
            else:
                column = order.lstrip('-')
                result = cmp(lhs.get(column), rhs.get(column))
                if order.startswith('-'):
                    result *= -1
            if result != 0:
                return result
        return 0
