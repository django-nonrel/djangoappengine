from mapreduce import mapper_pipeline
from mapreduce import mapreduce_pipeline

def _convert_func_to_string(func):
    return '%s.%s' % (func.__module__, func.__name__)

def _convert_model_to_string(model):
    return '%s.%s' % (model.__module__, model.__name__)

def DjangoModelMapreduce(model,
                         mapper,
                         reducer,
                         keys_only=False,
                         output_writer="mapreduce.output_writers.BlobstoreOutputWriter",
                         extra_mapper_params=None,
                         extra_reducer_params=None):
    """
    A simple wrapper function for creating mapreduce jobs over a Django model.

    Args:
        model:  A Django model class
        mapper: A top-level function that takes a single argument,
            and yields zero or many two-tuples strings
        reducer: A top-level function that takes two arguments
            and yields zero or more values
        output_writer: An optional OutputWriter subclass name,
            defaults to 'mapreduce.output_writers.BlobstoreOutputWriter'
        extra_mapper_params: An optional dictionary of values to pass to the Mapper
        extra_reducer_params: An optional dictionary of values to pass to the Reducer
    """

    if keys_only:
        input_reader_spec = "mapreduce.input_readers.DatastoreKeyInputReader"
        mapper_params = { "entity_kind": model._meta.db_table }
    else:
        input_reader_spec = "djangoappengine.mapreduce.input_readers.DjangoModelInputReader"
        mapper_params = { "entity_kind": _convert_model_to_string(model) }

    if extra_mapper_params:
        mapper_params.update(extra_mapper_params)

    reducer_params = { "mime_type": "text/plain" }
    if extra_reducer_params:
        reducer_params.update(extra_reducer_params)

    mapper_spec = _convert_func_to_string(mapper)
    reducer_spec = _convert_func_to_string(reducer)

    return mapreduce_pipeline.MapreducePipeline(
        "%s-%s-%s-mapreduce" % (model._meta.object_name, mapper_spec, reducer_spec),
        mapper_spec,
        reducer_spec,
        input_reader_spec,
        output_writer,
        mapper_params=mapper_params,
        reducer_params=reducer_params)

def DjangoModelMap(model,
                   mapper_func,
                   keys_only=False,
                   output_writer="mapreduce.output_writers.BlobstoreOutputWriter",
                   params=None):
    """
    A simple wrapper function for running a mapper function over Django model instances.

    Args:
        model:  A Django model class
        mapper: A top-level function that takes a single argument,
            and yields zero or many two-tuples strings
        keys_only: Selects which input reader to use
            if True, then we use 'mapreduce.input_readers.DatastoreKeyInputReader',
            if False, then 'djangoappengine.mapreduce.input_readers.DjangoModelInputReader',
            defaults to False
        params: An optional dictionary of values to pass to the Mapper
    """

    if keys_only:
        input_reader_spec = "mapreduce.input_readers.DatastoreKeyInputReader"
        mapper_params = { "entity_kind": model._meta.db_table, "mime_type": "text/plain" }
    else:
        input_reader_spec = "djangoappengine.mapreduce.input_readers.DjangoModelInputReader"
        mapper_params = { "entity_kind": _convert_model_to_string(model), "mime_type": "text/plain" }

    if params:
        mapper_params.update(params)

    mapper_spec = _convert_func_to_string(mapper_func)

    return mapper_pipeline.MapperPipeline(
        "%s-%s-mapper" % (model._meta.object_name, mapper_spec),
        mapper_spec,
        input_reader_spec,
        output_writer_spec=output_writer,
        params=mapper_params)
