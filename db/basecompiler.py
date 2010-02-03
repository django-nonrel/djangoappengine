from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.constants import LOOKUP_SEP
from django.db.models.sql.where import AND, OR
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
