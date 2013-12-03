Installation
========================
Make sure you've installed the `App Engine SDK`_. On Windows simply use the default installation path. On Linux you can put it in ``/usr/local/google_appengine``. On MacOS it should work if you put it in your Applications folder. Alternatively, on all systems you can add the google_appengine folder to your ``PATH`` (not ``PYTHONPATH``) environment variable.

.. note::

    Since Google App Engine runs your Python code from within a sandbox, some standard Python installation methods are unavailable.
    For example, you cannot install django or other Python modules in your system's Python library. All code for your app must be
    installed in your project directory.

Create a new directory for your project.

Download the following zip files:

* `django-nonrel <https://github.com/django-nonrel/django/zipball/nonrel-1.5>`__
* `djangoappengine <https://github.com/django-nonrel/djangoappengine/zipball/master>`__
* `djangotoolbox <https://github.com/django-nonrel/djangotoolbox/zipball/master>`__
* `django-autoload <http://bitbucket.org/twanschik/django-autoload/get/tip.zip>`__
* `django-dbindexer <https://github.com/django-nonrel/django-dbindexer/zipball/master>`__

Unzip everything and copy the modules into your project directory.


Now you need to create a django project. Djangoappengine includes a project template which you can generate using the ``django-admin.py`` command. Run this command from within your project directory to create a new project:

.. sourcecode:: sh

    PYTHONPATH=. python django/bin/django-admin.py startproject \
       --name=app.yaml --template=djangoappengine/conf/project_template myapp .

That's it. Your project structure should look like this:

* ``<project>/autoload``
* ``<project>/dbindexer``
* ``<project>/django``
* ``<project>/djangoappengine``
* ``<project>/djangotoolbox``

To start the local dev server, run this command:

.. sourcecode:: sh

    ./manage.py runserver

.. note::

   You can also clone the Git repositories and copy the modules from there into your project. The repositories are available here:
   `django-nonrel <https://github.com/django-nonrel/django>`__,
   `djangoappengine <https://github.com/django-nonrel/djangoappengine>`__,
   `djangotoolbox <https://github.com/django-nonrel/djangotoolbox>`__,
   `django-autoload <https://bitbucket.org/twanschik/django-autoload>`__,
   `django-dbindexer <https://github.com/django-nonrel/django-dbindexer>`__. Alternatively, you can of course clone the respective repositories and create symbolic links instead of copying the folders to your project. That might be easier if you have a lot of projects and don't want to update each one manually.


.. _djangotoolbox: https://github.com/django-nonrel/djangotoolbox
.. _django-nonrel: http://django-nonrel.github.com/
.. _djangoappengine: https://github.com/django-nonrel/djangoappengine
.. _source: https://github.com/django-nonrel/djangoappengine
.. _App Engine SDK: https://developers.google.com/appengine/downloads
.. _abstract base classes: http://docs.djangoproject.com/en/dev/topics/db/models/#abstract-base-classes
.. _multi-table inheritance: http://docs.djangoproject.com/en/dev/topics/db/models/#multi-table-inheritance
.. _multiple inheritance: http://docs.djangoproject.com/en/dev/topics/db/models/#multiple-inheritance
.. _Managing per-field indexes on App Engine: http://www.allbuttonspressed.com/blog/django/2010/07/Managing-per-field-indexes-on-App-Engine
.. _django-dbindexer: https://github.com/django-nonrel/django-dbindexer
.. _Google OpenID Sample Store: https://sites.google.com/site/oauthgoog/Home/openidsamplesite
.. _django-filetransfers: http://www.allbuttonspressed.com/projects/django-filetransfers
.. _Blobstore: https://developers.google.com/appengine/docs/python/blobstore/overview
.. _discussion group: http://groups.google.com/group/django-non-relational
