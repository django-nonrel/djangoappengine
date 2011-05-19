from django.db.models.sql.expressions import SQLEvaluator 

OPERATION_MAP = {
    '+': lambda x, y: x+y, 
    '-': lambda x, y: x-y,
    '*': lambda x, y: x*y,
    '/': lambda x, y: x/y,
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

            if value:
                values.append(value)

        return OPERATION_MAP[node.connector](*values)

    def evaluate_leaf(self, node, qn, connection):
        return self.entity[qn(self.cols[node][1])]