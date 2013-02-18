Django admin
===============

The native django admin site is a compelling reason to use django nonrel on the appengine, rather than webapp2 with native GAE datastore bindings.

However, there are limitations to be aware of when running contrib.admin against the GAE datastore instead of a rich SQL database:

* inequality queries against one index only
* need to use dbindexer to access 'contains'
* need to use dbindexer to index date/datetime fields used for date filters

Some of the consequences of the above restrictions:
* can't find users created before 2012 sorted by name
* can't find users like "Peter" sorted by date joined
* can't sort by multiple columns

For end-users this does lead to a limited admin site compared with 'relational' django. You may find that alternative/custom screens need to be implemented to meet all users' requirements on GAE (if they can be satisfied at all).

indexes.yaml
------------------
Beware of adding all the suggested composite indexes to your indexes.yaml when you use the admin site. It's easy to rack up the maximum 200 indexes and find that you struggle to add new functionality that needs further indexes.
Instead, digest the `Google index documentation`_ and aim to exploit the zigzag merge query planner to reduce the number of indexes needed. This is particularly useful when you want to use several admin filters.

Sorting and searching
------------------
You may have an admin screen for some model sorted by 'name'. But users may also want to be able to search for an article, which depends on an inequality query against a dbindexer icontains index (a model's generated 'idxf_name_l_icontains' field).
Since the datastore can't query against two inequality relations, you can't simply have this in your admin definition:

.. sourcecode:: python

    search_fields = ('name',)
    ordering = ('name',)

This fails when you use the search, because that query is an inequality against dbindexer's generated 'idxf_name_l_icontains' field, which the datastore can't handle at the same time as sorting (inequality) against the 'name' field.

A useful pattern to get round this is to make your admin screen's ordering vary depending on whether a search is in action or not:

.. sourcecode:: python

    search_fields = ('name',)
    def get_ordering(self, request):
        if 'q' in request.GET and request.GET['q'] != '':
            return ('idxf_name_l_icontains',)
        return ('name',)
    
In other words, don't specify the admin 'ordering' variable, but defer to the 'get_ordering' method, which sorts by name if no search is in action, or by the dbindexer field if it is.

Filters and sorting and searching
------------------
Date/datetime filters do work if you define some indexes using dbindexer, but you can't apply a date filter (which uses an inequality query for some of the options) at the same time as a search. And the sort order for a filtered model must match the filter. For example:

.. sourcecode:: python

    list_filter = ('expired', OwnedFranchiseRegionFilter, 'status', 'start_date',)
    ordering = ('-start_date',)

where 'start_date' is a Datefield and the other filters are simple equality filters. In this case, the admin screen cannot be ordered by name, and we can't enable search by name.

.. _Google index documentation: https://developers.google.com/appengine/articles/indexselection
