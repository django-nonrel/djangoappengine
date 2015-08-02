import datetime
import email
import mimetypes
import urlparse

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import File
from django.core.files.storage import Storage
from django.core.files.uploadedfile import UploadedFile
from django.core.files.uploadhandler import FileUploadHandler, \
    StopFutureHandlers
from django.http import HttpResponse
from django.utils.encoding import smart_str, force_unicode, filepath_to_uri

try:
    import cloudstorage
except ImportError:
    cloudstorage = None

from google.appengine.api import files
from google.appengine.api.images import get_serving_url, NotImageError, \
    TransformationError, BlobKeyRequiredError
from google.appengine.ext.blobstore import BlobInfo, BlobKey, delete, \
    create_upload_url, BLOB_KEY_HEADER, BLOB_RANGE_HEADER, BlobReader, \
    create_gs_key, CLOUD_STORAGE_OBJECT_HEADER

APPENGINE_STORAGE_SERVICE_KEY = 'APPENGINE_STORAGE_SERVICE'
CLOUD_STORAGE_DEFAULT_BUCKET_KEY = 'CLOUD_STORAGE_DEFAULT_BUCKET'

BLOBSTORE_SERVICE = 'blobstore'
CLOUD_STORAGE_SERVICE = 'gs'

def prepare_upload(request, url, storage_service=None, cloud_storage_bucket=None, **kwargs):
    if not storage_service:
        storage_service = getattr(settings, APPENGINE_STORAGE_SERVICE_KEY, BLOBSTORE_SERVICE)

    upload_kwargs = {}
    if storage_service == 'gs':
        if not cloud_storage_bucket:
            cloud_storage_bucket = getattr(settings, CLOUD_STORAGE_DEFAULT_BUCKET_KEY, None)
        if not cloud_storage_bucket:
            raise ImproperlyConfigured("'cloud_storage_bucket' keyword argument or "
                "settings.CLOUD_STORAGE_DEFAULT_BUCKET must be set when using Google Cloud Storage.")
        upload_kwargs['gs_bucket_name'] = cloud_storage_bucket
    return create_upload_url(url, **upload_kwargs), {}


def serve_file(request, file, save_as, content_type, **kwargs):
    if hasattr(file, 'file') and hasattr(file.file, 'blobstore_info'):
        blobkey = file.file.blobstore_info.key()
    elif hasattr(file, 'blobstore_info'):
        blobkey = file.blobstore_info.key()
    else:
        raise ValueError("The provided file can't be served via the "
                         "App Engine Blobstore or Google Cloud Storage.")
    response = HttpResponse(content_type=content_type)
    response[BLOB_KEY_HEADER] = str(blobkey)
    response['Accept-Ranges'] = 'bytes'
    http_range = request.META.get('HTTP_RANGE')
    if http_range is not None:
        response[BLOB_RANGE_HEADER] = http_range
    if save_as:
        response['Content-Disposition'] = smart_str(
            u'attachment; filename=%s' % save_as)
    if file.size is not None:
        response['Content-Length'] = file.size
    return response


class AppEngineStorage(Storage):
    """
    Google App Engine storage backend.
    Supports Blobstore and Cloud Storage.
    """
    def __init__(self, storage_service=None, cloud_storage_bucket=None):
        super(AppEngineStorage, self).__init__()
        if not storage_service:
            storage_service = getattr(settings, APPENGINE_STORAGE_SERVICE_KEY, BLOBSTORE_SERVICE)
        if not cloud_storage_bucket:
            cloud_storage_bucket = getattr(settings, CLOUD_STORAGE_DEFAULT_BUCKET_KEY, None)

        if storage_service not in (BLOBSTORE_SERVICE, CLOUD_STORAGE_SERVICE):
            raise ImproperlyConfigured("APPENGINE_STORAGE_SERVICE must be either "
                "'gs' or 'blobstore', not %s." % storage_service)
        if storage_service == CLOUD_STORAGE_SERVICE and not cloud_storage_bucket:
            raise ImproperlyConfigured("CLOUD_STORAGE_DEFAULT_BUCKET must be set "
                "when using Google Cloud Storage.")

        self.storage_service = storage_service
        self.cloud_storage_bucket = cloud_storage_bucket

    def _open(self, name, mode='rb'):
        return AppEngineFile(name, mode, self)

    def _save(self, name, content):
        name = name.replace('\\', '/')

        if isinstance(content, (AppEngineFile, AppEngineUploadedFile)):
            data = content.blobstore_info
        elif hasattr(content, 'file') and \
             isinstance(content.file, (AppEngineFile, AppEngineUploadedFile)):
            data = content.file.blobstore_info
        elif isinstance(content, File):
            guessed_type = mimetypes.guess_type(name)[0]

            if self.storage_service == CLOUD_STORAGE_SERVICE:
                assert cloudstorage, 'cloudstorage module is not available.'

                file_name = '/%s/%s' % (self.cloud_storage_bucket, name)

                with cloudstorage.open(file_name, 'w', guessed_type or 'application/octet-stream') as f:
                    for chunk in content.chunks():
                        f.write(chunk)

                data = self._get_info('/gs' + file_name)
            else:
                # TODO deprecated

                file_name = files.blobstore.create(mime_type=guessed_type or 'application/octet-stream',
                                                   _blobinfo_uploaded_filename=name)

                with files.open(file_name, 'a') as f:
                    for chunk in content.chunks():
                        f.write(chunk)

                files.finalize(file_name)

                data = files.blobstore.get_blob_key(file_name)
        else:
            raise ValueError("The App Engine storage backend only supports "
                             "AppEngineFile instances or File instances.")

        if isinstance(data, CloudStorageInfo):
            return '/gs' + data.fullname

        if isinstance(data, BlobInfo):
            data = data.key()

        if isinstance(data, BlobKey):
            return '%s/%s' % (data, name.lstrip('/'))

        raise ValueError("Unknown type returned from saving: %s" % type(data))

    def delete(self, name):
        self._get_info(name).delete()

    def exists(self, name):
        info = self._get_info(name)
        return info is not None and (not hasattr(info, 'exists') or info.exists())

    def size(self, name):
        return self._get_info(name).size

    def url(self, name):
        try:
            info = self._get_info(name)
            if not info:
                raise BlobKeyRequiredError('No blob info found for %s.' % name)
            return get_serving_url(info.key())
        except (NotImageError, TransformationError):
            return None
        except BlobKeyRequiredError:
            if settings.DEBUG:
                return urlparse.urljoin(settings.MEDIA_URL, filepath_to_uri(name))
            else:
                raise

    def created_time(self, name):
        return self._get_info(name).creation

    def get_valid_name(self, name):
        return force_unicode(name).strip().replace('\\', '/')

    def get_available_name(self, name):
        return name.replace('\\', '/')

    def _get_info(self, name):
        if name.startswith('/gs/'):
            assert cloudstorage, 'cloudstorage module is not available.'
            return CloudStorageInfo(name)
        else:
            key = BlobKey(name.split('/', 1)[0])
            return BlobInfo.get(key)


class CloudStorageInfo(object):
    def __init__(self, name):
        self.fullname = name[3:]
        self.filename = self.fullname.split('/', 2)[2]

    def delete(self):
        cloudstorage.delete(self.fullname)

    def exists(self):
        try:
            cloudstorage.stat(self.fullname)
            return True
        except cloudstorage.NotFoundError:
            return False

    def key(self):
        return create_gs_key('/gs' + self.fullname)

    def open(self):
        return cloudstorage.open(self.fullname, 'r')

    @property
    def creation(self):
        return datetime.datetime.fromtimestamp(cloudstorage.stat(self.fullname).st_ctime)

    @property
    def size(self):
        return cloudstorage.stat(self.fullname).st_size


class AppEngineFile(File):
    def __init__(self, name, mode, storage):
        self.name = name
        self._storage = storage
        self._mode = mode
        self.blobstore_info = storage._get_info(name)

    @property
    def size(self):
        return self.blobstore_info.size

    def write(self, content):
        raise NotImplementedError()

    @property
    def file(self):
        if not hasattr(self, '_file'):
            self._file = self.blobstore_info.open()
        return self._file

class AppEngineFileUploadHandler(FileUploadHandler):
    """
    File upload handler for Google App Engine. Supports both
    Blobstore and Google Cloud Storage
    """

    def new_file(self, *args, **kwargs):
        super(AppEngineFileUploadHandler, self).new_file(*args, **kwargs)
        blobkey = self.content_type_extra.get('blob-key')
        self.activated = blobkey is not None
        if self.activated:
            self.blobkey = BlobKey(blobkey)
            self.filename = kwargs.get('file_name', None)
            self.file = StringIO()
            raise StopFutureHandlers()

    def receive_data_chunk(self, raw_data, start):
        """
        Add the data to the StringIO file.
        """
        if self.activated:
            self.file.write(raw_data)
        else:
            return raw_data

    def file_complete(self, file_size):
        """
        Return a file object if we're activated.
        """
        if not self.activated:
            return

        self.file.seek(0)
        upload_content = email.message_from_file(self.file)

        def get_value(dict, name):
            value = dict.get(name, None)
            if value is None:
                raise Exception('Missing field %s.' % (field_name, name))
            return value

        content_type = get_value(upload_content, 'content-type')
        size = get_value(upload_content, 'content-length')
        gs_object_name = upload_content.get(CLOUD_STORAGE_OBJECT_HEADER, None)

        kwargs = {
            'blob_key': self.blobkey,
            'name': self.file_name,
            'content_type': content_type,
            'size': int(size),
            'charset': self.charset,
        }

        return AppEngineUploadedFile(**kwargs)


class AppEngineUploadedFile(UploadedFile):
    """
    A file uploaded via App Engine's upload mechanism.
    """

    def __init__(self, **kwargs):
        gs_object_name = kwargs.pop('gs_object_name', None)
        blob_key = kwargs.pop('blob_key', None)
        if gs_object_name:
            self.blobstore_info = CloudStorageInfo(gs_object_name)
        elif blob_key:
            self.blobstore_info = BlobInfo(blob_key)
        else:
            raise ValueError('A gs_object_name or blob_key is required.')

        super(AppEngineUploadedFile, self).__init__(self.blobstore_info.open(), **kwargs)

    def open(self, mode=None):
        pass

    def chunks(self, chunk_size=1024 * 128):
        self.file.seek(0)
        while True:
            content = self.read(chunk_size)
            if not content:
                break
            yield content

    def multiple_chunks(self, chunk_size=1024 * 128):
        return True

# Backwards compatibility
BlobstoreStorage = AppEngineStorage
DevBlobstoreStorage = AppEngineStorage
BlobstoreFile = AppEngineFile
BlobstoreFileUploadHandler = AppEngineFileUploadHandler
BlobstoreUploadedFile = AppEngineUploadedFile
