Email, caching and other services
===========================

Email handling
---------------------------------------------
You can (and should) use Django's mail API instead of App Engine's mail API. The App Engine email backend is already enabled in the default settings (``from djangoappengine.settings_base import *``).

Emails will be deferred to the task queue specified in the EMAIL_QUEUE_NAME setting. If you run the dev appserver with --disable_task_running then you'll see the tasks being deposited in the queue. You can manually execute those tasks from the GUI at /_ah/admin/tasks.

If you execute the dev appserver with the options ``--smtp_host=localhost --smtp_port=1025`` and run the dev smtp server in a terminal with ``python -m smtpd -n -c DebuggingServer localhost:1025`` then you'll see emails delivered to that terminal for debug.

Cache API
---------------------------------------------
You can (and should) use Django's cache API instead of App Engine's memcache module. The memcache backend is already enabled in the default settings.

Sessions
---------------------------------------------
You can use Django's session API in your code. The ``cached_db`` session backend is already enabled in the default settings.

Authentication
-----------------------------------------------
You can (and probably should) use ``django.contrib.auth`` directly in your code. We don't recommend to use App Engine's Google Accounts API. This will lock you into App Engine unnecessarily. Use Django's auth API, instead. If you want to support Google Accounts you can do so via OpenID. Django has several apps which provide OpenID support via Django's auth API. This also allows you to support Yahoo and other login options in the future and you're independent of App Engine. Take a look at `Google OpenID Sample Store`_ to see an example of what OpenID login for Google Accounts looks like.

Note that username uniqueness is only checked at the form level (and by Django's model validation API if you explicitly use that). Since App Engine doesn't support uniqueness constraints at the DB level it's possible, though very unlikely, that two users register the same username at exactly the same time. Your registration confirmation/activation mechanism (i.e., user receives mail to activate his account) must handle such cases correctly. For example, the activation model could store the username as its primary key, so you can be sure that only one of the created users is activated.

The django-permission-backend-nonrel repository contains fixes for Django's auth to make permissions and groups work on GAE (including the auth admin screens).

File uploads/downloads
---------------------------------------------
See django-filetransfers_ for an abstract file upload/download API for ``FileField`` which works with the Blobstore_ and X-Sendfile and other solutions. The required backends for the App Engine Blobstore are already enabled in the default settings.

Background tasks
---------------------------------------------
**Contributors:** We've started an experimental API for abstracting background tasks, so the same code can work with App Engine and Celery and others. Please help us finish and improve the API here: https://bitbucket.org/wkornewald/django-defer

Make sure that your ``app.yaml`` specifies the correct ``deferred`` handler. It should be:

.. sourcecode:: yaml

    - url: /_ah/queue/deferred
      script: djangoappengine/deferred/handler.py
      login: admin

This custom handler initializes ``djangoappengine`` before it passes the request to App Engine's internal ``deferred`` handler.

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
