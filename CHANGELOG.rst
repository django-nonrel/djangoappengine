Changelog
=========

Version 0.X
-----------

* Added a ``STORE_RELATIONS_AS_DB_KEYS`` database options, making it
  possible to store foreign key values in the same way primary keys are
  stored (using ``google.appengine.ext.db.db.Key``)
* Added an index for contrib.admin's ``LogEntry.object_id`` allowing
  admin history to work
* Rewritten most of the code used for preparing fields' values for the
  datastore / deconverting values from the database
* Allow "--allow_skipped_files" to be used
