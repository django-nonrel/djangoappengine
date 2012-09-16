Changelog
=========

Version 0.X
-----------

* Added write support to ``BlobstoreStorage``
* Added high replication support to test framework. Use ``HIGH_REPLICATION``
  to your database options to enable.
* Added ``testserver`` command to start dev_appserver and install
  fixtures
* Added cross-group transaction option to ``@commit_locked`` decorator
* Fixed various sys.path issues (Thanks lukebpotato)
* Fixed CursorQuery class MRO issues (Thanks anentropic)
* Fixed booting to respect previously defined ``DJANGO_SETTINGS_MODULE``
  (Thanks madisona)

Version 0.9
-----------

* Added a ``STORE_RELATIONS_AS_DB_KEYS`` database options, making it
  possible to store foreign key values in the same way primary keys are
  stored (using ``google.appengine.ext.db.db.Key``)
* Added an index for contrib.admin's ``LogEntry.object_id`` allowing
  admin history to work
* Rewritten most of the code used for preparing fields' values for the
  datastore / deconverting values from the database
* Allow "--allow_skipped_files" to be used
