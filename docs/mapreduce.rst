MapReduce
===========================

Overview
---------------------------------------------
Djangoappengine provides a few classes and utilities to make working with Google App Engine's MapReduce library easier. There are many tutorials and documents on MapReduce in general, as well as on the specifics of App Engine's MapReduce library.

* `MapReduce Wikipedia page <http://en.wikipedia.org/wiki/MapReduce>`__
* `Original Google MapReduce paper <http://research.google.com/archive/mapreduce.html>`__
* `App Engine MapReduce library <http://code.google.com/p/appengine-mapreduce/>`__
* `Getting started guide for Python MapReduce <http://code.google.com/p/appengine-mapreduce/wiki/GettingStartedInPython>`__

Djangoappengine provides two modules to simplify running MapReduce jobs over Django models. DjangoModelMapreduce and DjangoModelMap are helper functions that quickly allow you to create a mapreduce or a simple map job. These functions make use of DjangoModelInputReader, an InputReader subclass, which returns model instances for a given Django model.

Installation
---------------------------------------------
Checkout the mapreduce folder into your application directory:

.. sourcecode:: sh

   svn checkout http://appengine-mapreduce.googlecode.com/svn/trunk/python/src/mapreduce

Add the mapreduce handlers to your app.yaml:

.. sourcecode:: yaml

    handlers:
    - url: /mapreduce/pipeline/images
      static_dir: mapreduce/lib/pipeline/ui/images

    - url: /mapreduce(/.*)?
      script: djangoappengine.mapreduce.handler.application
      login: admin

DjangoModelMapreduce and DjangoModelMap
---------------------------------------------
DjangoModelMapreduce and DjangoModelMap are helper functions which return MapreducePipeline and MapperPipeline instances, respectively.

DjangoModelMap allows you to specify a model class and a single function called a mapper. The mapper function can do anything to your model instance, including When running the pipeline, the mapper function is called on each instance of your model class. As an example, consider this simple model:

.. sourcecode:: python

    class User(models.Model):
        name = models.CharField()
        city = models.CharField()
        age = models.IntegerField()

A mapper class which output the name and age of each User in a tab-delimited format looks like this:

.. sourcecode:: python

    from djangoappengine.mapreduce import pipeline as django_pipeline
    from mapreduce import base_handler

    def name_age(user):
        yield "%s\t%s\n" % (user.name, user.age)

    class UserNameAgePipeline(base_handler.PipelineBase):
        def run(self):
            yield django_pipeline.DjangoModelMap(User, name_age)


A mapreduce class which outputs the average age of the users in each city looks like this:

.. sourcecode:: python

    from djangoappengine.mapreduce import pipeline as django_pipeline
    from mapreduce import base_handler

    def avg_age_mapper(user):
        yield (user.city, user.age)

    def avg_age_reducer(city, age_list):
        yield "%s\t%s\n" % (city, float(sum(age_list))/len(age_list))

    class AverageAgePipeline(base_handler.PipelineBase):
        def run(self):
            yield django_pipeline.DjangoModelMapreduce(User, avg_age_mapper, avg_age_reducer)
