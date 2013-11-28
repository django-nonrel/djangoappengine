Installation
========================
Make sure you've installed the `App Engine SDK`_. On Windows simply use the default installation path. On Linux you can put it in /usr/local/google_appengine. On MacOS it should work if you put it in your Applications folder. Alternatively, on all systems you can add the google_appengine folder to your PATH (not PYTHONPATH) environment variable.

Create a new directory for your project.

Download the following zip files:

* `django-nonrel <https://github.com/django-nonrel/django/zipball/nonrel-1.5>`__ (or `clone it <https://github.com/django-nonrel/django.git>`__)
* `djangoappengine <https://github.com/django-nonrel/djangoappengine/zipball/master>`__ (or `clone it <https://github.com/django-nonrel/djangoappengine.git>`__)
* `djangotoolbox <https://github.com/django-nonrel/djangotoolbox/zipball/master>`__ (or `clone it <https://github.com/django-nonrel/djangotoolbox.git>`__)
* `django-autoload <http://bitbucket.org/twanschik/django-autoload/get/tip.zip>`__ (or `clone it <https://bitbucket.org/twanschik/django-autoload>`__)
* `django-dbindexer <https://github.com/django-nonrel/django-dbindexer/zipball/master>`__ (or `clone it <https://github.com/django-nonrel/django-dbindexer.git>`__)

Unzip everything into your project directory.

To create a standard project structure, run this command from within your project directory:

    python django/bin/django-admin.py startproject --name=app.yaml --template=djangoappengine/conf/project_template myapp .

That's it. Your project structure should look like this:

* <project>/autoload
* <project>/dbindexer
* <project>/django
* <project>/djangoappengine
* <project>/djangotoolbox

To start the local dev server, run this command:

    ./manage.py runserver

Alternatively, you can of course clone the respective repositories and create symbolic links instead of copying the folders to your project. That might be easier if you have a lot of projects and don't want to update each one manually.

.. _djangotoolbox: https://github.com/django-nonrel/djangotoolbox
.. _testapp: https://github.com/django-nonrel/django-testapp
.. _django-testapp: https://github.com/django-nonrel/django-testapp
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
