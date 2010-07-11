from .db_settings import FIELD_INDEXES
from djangotoolbox.db.creation import NonrelDatabaseCreation

# TODO: add support for specifying index for non-string fields
class StringType(object):
    def __init__(self, internal_type):
        self.internal_type = internal_type

    def __mod__(self, field):
        app_label = field['model']._meta.app_label
        name = field['model']._meta.object_name
        path = '%s.%s.%s' % (app_label, name, field['name'])
        index = FIELD_INDEXES.get(path)
        if index is True:
            return 'text'
        elif index is False:
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
