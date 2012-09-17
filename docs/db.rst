Fields, queries and indexes
========================================

Supported and unsupported features
-----------------------------------------------------------
Field types
___________
All Django field types are fully supported except for the following:

* ``ImageField``
* ``ManyToManyField``

The following Django field options have no effect on App Engine:

* ``unique``
* ``unique_for_date``
* ``unique_for_month``
* ``unique_for_year``

Additionally djangotoolbox_ provides non-Django field types in ``djangotoolbox.fields`` which you can use on App Engine or other non-relational databases. These are

* ``ListField``
* ``BlobField``

The following App Engine properties can be emulated by using a ``CharField`` in Django-nonrel:

* ``CategoryProperty``
* ``LinkProperty``
* ``EmailProperty``
* ``IMProperty``
* ``PhoneNumberProperty``
* ``PostalAddressProperty``

QuerySet methods
______________________________
You can use the following field lookup types on all Fields except on ``TextField`` (unless you use indexes_) and ``BlobField``

* ``__exact`` equal to (the default)
* ``__lt`` less than
* ``__lte`` less than or equal to
* ``__gt`` greater than
* ``__gte`` greater than or equal to
* ``__in`` (up to 500 values on primary keys and 30 on other fields)
* ``__range`` inclusive on both boundaries
* ``__startswith`` needs a composite index if combined with other filters
* ``__year``
* ``__isnull`` requires django-dbindexer_ to work correctly on ``ForeignKey`` (you don't have to define any indexes for this to work)

Using django-dbindexer_ all remaining lookup types will automatically work too!

Additionally, you can use

* ``QuerySet.exclude()``
* ``Queryset.values()`` (only efficient on primary keys)
* ``Q``-objects
* ``QuerySet.count()``
* ``QuerySet.reverse()``
* ...

In all cases you have to keep general App Engine restrictions in mind.

Model inheritance only works with `abstract base classes`_:

.. sourcecode:: python

    class MyModel(models.Model):
        # ... fields ...
        class Meta:
            abstract = True # important!

    class ChildModel(MyModel):
        # works

In contrast, `multi-table inheritance`_ (i.e. inheritance from non-abstract models) will result in query errors. That's because multi-table inheritance, as the name implies, creates separate tables for each model in the inheritance hierarchy, so it requires JOINs to merge the results. This is not the same as `multiple inheritance`_ which is supported as long as you use abstract parent models.

Many advanced Django features are not supported at the moment. A few of them are:

* JOINs (with django-dbindexer simple JOINs will work)
* many-to-many relations
* aggregates
* transactions (but you can use ``run_in_transaction()`` from App Engine's SDK)
* ``QuerySet.select_related()``

Other
__________________________
Additionally, the following features from App Engine are not supported:

* entity groups (we don't yet have a ``GAEPKField``, but it should be trivial to add)
* batch puts (it's technically possible, but nobody found the time/need to implement it, yet)

Indexes
--------------------------------------------
It's possible to specify which fields should be indexed and which not. This also includes the possibility to convert a ``TextField`` into an indexed field like ``CharField``.

Managing per-field indexes
____________________________________________

An annoying problem when trying to reuse an existing Django app is that some apps use ``TextField`` instead of ``CharField`` and still want to filter on that field. On App Engine ``TextField`` is not indexed and thus can't be filtered against. One app which has this problem is django-openid-auth_. Previously, you had to modify the model source code directly and replace ``TextField`` with ``CharField`` where necessary. However, this is not a good solution because whenever you update the code you have to apply the patch, again. Now, djangoappengine_ provides a solution which allows you to configure indexes for individual fields without changing the models. By decoupling DB-specific indexes from the model definition we simplify maintenance and increase code portability.

Example
________________________________
Let's see how we can get django-openid-auth to work correctly without modifying the app's source code. First, you need to create a module which defines the indexing settings. Let's call it "gae_openid_settings.py":

.. sourcecode:: python

    from django_openid_auth.models import Association, UserOpenID

    FIELD_INDEXES = {
        Association: {'indexed': ['server_url', 'assoc_type']},
        UserOpenID: {'indexed': ['claimed_id']},
    }

Then, in your settings.py you have to specify the list of gae settings modules:

.. sourcecode:: python

    GAE_SETTINGS_MODULES = (
        'gae_openid_settings',
    )

That's it. Now the ``server_url``, ``assoc_type``, and ``claimed_id`` ``TextField``\s will behave like ``CharField`` and get indexed by the datastore.

Note that we didn't place the index definition in the ``django_openid_auth`` package. It's better to keep them separate because that way upgrades are easier: Just update the ``django_openid_auth`` folder. No need to re-add the index definition (and you can't mistakenly delete the index definition during updates).

Optimization
____________________________
You can also use this to optimize your models. For example, you might have fields which don't need to be indexed. The more indexes you have the slower ``Model.save()`` will be. Fields that shouldn't be indexed can be specified via ``'unindexed'``:

.. sourcecode:: python

    from myapp.models import MyContact

    FIELD_INDEXES = {
        MyContact: {
            'indexed': [...],
            'unindexed': ['creation_date', 'last_modified', ...],
        },
    }

This also has a nice extra advantage: If you specify a ``CharField`` as "unindexed" it will behave like a ``TextField`` and allow for storing strings that are longer than 500 bytes. This can also be useful when trying to integrate 3rd-party apps.


dbindexer index definitions
-------------------------------------------------------------
By default, djangoappengine installs ``__iexact`` indexes on ``User.username`` and ``User.email``.


High-replication datastore settings
-------------------------------------------------------------
In order to use ``manage.py remote`` with the high-replication datastore you need to add the following to the top of your ``settings.py``:

.. sourcecode:: python

    from djangoappengine.settings_base import *
    DATABASES['default']['HIGH_REPLICATION'] = True

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
.. _django-openid-auth: https://launchpad.net/django-openid-auth
