Changelog
=========

Version 1.6.3 (TBD)
-------------

* Add 'require_indexes' option to database 'DEV_APPSERVER_OPTIONS' to throw
  exception if datastore index is missing. This is useful for unit testing.
  (Thanks jacobg)
* Fixed import error when launching from GoogleAppEngineLauncher
* Fixed project_template packaging (Thanks fmierlo)

Version 1.6.2 (Mar 22, 2014)
-------------

* Fixed import errors caused by renamed dev_appserver in SDK 1.9.1

Version 1.6.1 (Nov 29, 2013)
-------------

* Fixed packaging issues

Version 1.6.0
-------------

Note: This is release includes support for Django versions 1.4, 1.5 and 1.6.
You no longer need to use a separate version for each Django version.

* Added support for Django 1.6

Version 1.5.0
-------------

* Added support for Django 1.5
* Added continuous integration using Travis CI

Version 1.4.0
-------------

Note: This is the first release with a new version scheme. The major and
minor numbers matches the supported Django version.

* Added support for Django 1.4
* Added App Engine MapReduce helpers, requires mapreduce r452 or greater
* Added ``set_config`` function to ``db.utils`` to add Datastore config
  options, such as ``batch_size`` and ``read_policy``
* Added Django Admin documentation (Thanks smeyfroi)
* Added ``--blobstore_path`` option to ``runserver.py`` (Thanks karamfil)
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

Version 0.9.0
-------------

* Added a ``STORE_RELATIONS_AS_DB_KEYS`` database options, making it
  possible to store foreign key values in the same way primary keys are
  stored (using ``google.appengine.ext.db.db.Key``)
* Added an index for contrib.admin's ``LogEntry.object_id`` allowing
  admin history to work
* Rewritten most of the code used for preparing fields' values for the
  datastore / deconverting values from the database
* Allow "--allow_skipped_files" to be used
