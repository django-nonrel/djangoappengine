Running djangoappengine
=============================

Management commands
---------------------------------------------
You can directly use Django's manage.py commands. For example, run ``manage.py createsuperuser`` to create a new admin user and ``manage.py runserver`` to start the development server.

**Important:**  Don't use dev_appserver.py directly. This won't work as expected because ``manage.py runserver`` uses a customized dev_appserver.py configuration. Also, never run ``manage.py runserver`` together with other management commands at the same time. The changes won't take effect. That's an App Engine SDK limitation which might get fixed in a later release.

With djangoappengine you get a few extra manage.py commands:

* ``manage.py remote`` allows you to execute a command on the production database (e.g., ``manage.py remote shell`` or ``manage.py remote createsuperuser``)
* ``manage.py deploy`` uploads your project to App Engine (use this instead of ``appcfg.py update``)

Note that you can only use ``manage.py remote`` if your app is deployed and if you have enabled authentication via the Google Accounts API in your app settings in the App Engine Dashboard. Also, if you use a custom app.yaml you have to make sure that it contains the remote_api handler. Running 'remote' executes your *local code*, but proxies your datastore access against the *remote datastore*.


App Engine for Business
-------------------------------------------------------------
In order to use ``manage.py remote`` with the ``googleplex.com`` domain you need to add the following to the top of your ``settings.py``:

.. sourcecode:: python

    from djangoappengine.settings_base import *
    DATABASES['default']['DOMAIN'] = 'googleplex.com'

Checking whether you're on the production server
------------------------------------------------------------------------------------------

.. sourcecode:: python

    from djangoappengine.utils import on_production_server, have_appserver

When you're running on the production server ``on_production_server`` is ``True``. When you're running either the development or production server ``have_appserver`` is ``True`` and for any other ``manage.py`` command it's ``False``.

Zip packages
---------------------------------------------
**Important:** Your instances will load slower when using zip packages because zipped Python files are not precompiled. Also, i18n doesn't work with zip packages. Zipping should only be a **last resort**! If you hit the 3000 files limit you should better try to reduce the number of files by, e.g., deleting unused packages from Django's "contrib" folder. Only when **nothing** (!) else works you should consider zip packages.

Since you can't upload more than 10000 files on App Engine you sometimes have to create zipped packages. Luckily, djangoappengine can help you with integrating those zip packages. Simply create a "zip-packages" directory in your project folder and move your zip packages there. They'll automatically get added to ``sys.path``.

In order to create a zip package simply select a Python package (e.g., a Django app) and zip it. However, keep in mind that only Python modules can be loaded transparently from such a zip file. You can't easily access templates and JavaScript files from a zip package, for example. In order to be able to access the templates you should move the templates into your global "templates" folder within your project before zipping the Python package.

.. _djangotoolbox: https://github.com/django-nonrel/djangotoolbox
.. _django-nonrel: http://django-nonrel.org/
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
