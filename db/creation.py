from .db_settings import get_indexes
from djangotoolbox.db.creation import NonrelDatabaseCreation

class StringType(object):
    def __init__(self, internal_type):
        self.internal_type = internal_type

    def __mod__(self, field):
        indexes = get_indexes().get(field['model'], {})
        if field['name'] in indexes.get('indexed', ()):
            return 'text'
        elif field['name'] in indexes.get('unindexed', ()):
            return 'longtext'
        return self.internal_type

def get_data_types():
    # TODO: Add GAEKeyField and a corresponding db_type
    string_types = ('text', 'longtext')
    data_types = NonrelDatabaseCreation.data_types.copy()
    for name, field_type in data_types.items():
        if field_type in string_types:
            data_types[name] = StringType(field_type)
    return data_types

class DatabaseCreation(NonrelDatabaseCreation):
    # This dictionary maps Field objects to their associated GAE column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__ before being output.
    # If a column type is set to None, it won't be included in the output.

    data_types = get_data_types()

    def create_test_db(self, *args, **kw):
        """Destroys the test datastore. A new store will be recreated on demand"""
        self.destroy_test_db()
        self.connection.use_test_datastore = True
        self.connection.flush()

    def destroy_test_db(self, *args, **kw):
        """Destroys the test datastore files."""
        from .base import destroy_datastore, get_test_datastore_paths
        destroy_datastore(*get_test_datastore_paths())
