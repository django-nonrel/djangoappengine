from djangotoolbox.db.creation import NonrelDatabaseCreation

class DatabaseCreation(NonrelDatabaseCreation):
    # This dictionary maps Field objects to their associated GAE column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__ before being output.
    # If a column type is set to None, it won't be included in the output.

    # TODO: Add GAEKeyField and a correspoding db_type
#    data_types = NonrelDatabaseCreation.data_types
#    data_types.update({
#        'GAEKeyField': 'gae_key',
#    })

    def create_test_db(self, *args, **kw):
        """Destroys the test datastore. A new store will be recreated on demand"""
        self.destroy_test_db()
        self.connection.use_test_datastore = True
        self.connection.flush()

    def destroy_test_db(self, *args, **kw):
        """Destroys the test datastore files."""
        from .base import destroy_datastore, get_test_datastore_paths
        destroy_datastore(*get_test_datastore_paths())
