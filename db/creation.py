from djangotoolbox.db.creation import NonrelDatabaseCreation

from .db_settings import get_model_indexes
from .stubs import stub_manager


class _StringType(object):
    """
    Helper to dynamically determine field's db_type based on its
    indexing.
    """

    def __init__(self, field_type):
        self.field_type = field_type

    def __mod__(self, field):
        indexes = get_model_indexes(field['model'])
        if field['name'] in indexes['indexed']:
            return 'text'
        elif field['name'] in indexes['unindexed']:
            return 'longtext'
        return self.field_type


def get_data_types():
    data_types = NonrelDatabaseCreation.data_types.copy()
    for field_type, db_type in data_types.iteritems():
        if db_type in ('text', 'longtext'):
            data_types[field_type] = _StringType(db_type)
    return data_types


class DatabaseCreation(NonrelDatabaseCreation):

    # This dictionary maps Field objects to their associated GAE column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__ before being output.
    # If a column type is set to None, it won't be included in the output.
    data_types = get_data_types()

    def _create_test_db(self, *args, **kw):
        self._had_test_stubs = stub_manager.active_stubs != 'test'
        if self._had_test_stubs:
            stub_manager.activate_test_stubs()

    def _destroy_test_db(self, *args, **kw):
        if self._had_test_stubs:
            stub_manager.deactivate_test_stubs()
            stub_manager.setup_stubs(self.connection)
        del self._had_test_stubs
