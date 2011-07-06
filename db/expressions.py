from django.db.models.sql.expressions import SQLEvaluator
from django.db.models.expressions import ExpressionNode

OPERATION_MAP = {
    ExpressionNode.ADD: lambda x, y: x+y, 
    ExpressionNode.SUB: lambda x, y: x-y,
    ExpressionNode.MUL: lambda x, y: x*y,
    ExpressionNode.DIV: lambda x, y: x/y,
    ExpressionNode.MOD: lambda x, y: x%y,
    ExpressionNode.AND: lambda x, y: x&y,
    ExpressionNode.OR: lambda x, y: x|y,
}

class ExpressionEvaluator(SQLEvaluator):
    def __init__(self, expression, query, entity, allow_joins=True):
        super(ExpressionEvaluator, self).__init__(expression, query, allow_joins)
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
        return self.entity[qn(self.cols[node][1])]