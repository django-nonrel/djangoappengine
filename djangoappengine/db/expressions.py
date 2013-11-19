import django
from django.db.models.sql.expressions import SQLEvaluator
from django.db.models.expressions import ExpressionNode

if django.VERSION >= (1, 5):
    ExpressionNode_BITAND = ExpressionNode.BITAND
    ExpressionNode_BITOR = ExpressionNode.BITOR

    def find_col_by_node(cols, node):
        col = None
        for n, c in cols:
            if n is node:
                col = c
                break
        return col

else:
    ExpressionNode_BITAND = ExpressionNode.AND
    ExpressionNode_BITOR = ExpressionNode.OR

    def find_col_by_node(cols, node):
        return cols[node]

OPERATION_MAP = {
    ExpressionNode.ADD: lambda x, y: x + y,
    ExpressionNode.SUB: lambda x, y: x - y,
    ExpressionNode.MUL: lambda x, y: x * y,
    ExpressionNode.DIV: lambda x, y: x / y,
    ExpressionNode.MOD: lambda x, y: x % y,
    ExpressionNode_BITAND: lambda x, y: x & y,
    ExpressionNode_BITOR:  lambda x, y: x | y,
}


class ExpressionEvaluator(SQLEvaluator):

    def __init__(self, expression, query, entity, allow_joins=True):
        super(ExpressionEvaluator, self).__init__(expression, query,
                                                  allow_joins)
        self.entity = entity

    ##################################################
    # Vistor methods for final expression evaluation #
    ##################################################

    def evaluate_node(self, node, qn, connection):
        values = []
        for child in node.children:
            if hasattr(child, 'evaluate'):
                value = child.evaluate(self, qn, connection)
            else:
                value = child

            if value is not None:
                values.append(value)

        return OPERATION_MAP[node.connector](*values)

    def evaluate_leaf(self, node, qn, connection):
        col = find_col_by_node(self.cols, node)
        if col is None:
            raise ValueError("Given node not found")
        return self.entity[qn(col[1])]
