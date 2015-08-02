try:
    import cloudstorage
except ImportError:
    cloudstorage = None

from django.core.files.base import ContentFile
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import unittest

from djangoappengine.storage import AppEngineStorage, CloudStorageInfo, BLOBSTORE_SERVICE, CLOUD_STORAGE_SERVICE

from google.appengine.api import files
from google.appengine.ext.blobstore import BlobInfo, BlobKey


class AppEngineStorageBaseTest(object):
    def test_file_accessed_time(self):
        self.assertRaises(NotImplementedError, self.storage.accessed_time, self.file_key)

    def test_file_created_time(self):
        ctime = self.storage.created_time(self.file_key)

        self.assertEqual(ctime, self.test_file_info.creation)

    def test_file_modified_time(self):
        self.assertRaises(NotImplementedError, self.storage.modified_time, self.file_key)

    def test_file_exists(self):
        self.assertTrue(self.storage.exists(self.file_key))

    def test_file_does_not_exist(self):
        self.assertFalse(self.storage.exists('abcdef'))

    def test_listdir(self):
        self.assertRaises(NotImplementedError, self.storage.listdir, '')

    def test_file_save_without_name(self):
        f = ContentFile('custom contents')
        f.name = 'test.file'

        storage_f_name = self.storage.save(None, f)

        info = self.file_info(storage_f_name)

        self.assertEqual(info.filename, f.name)

    def test_file_save_with_path(self):
        path = 'path/to/test.file'

        storage_f_name = self.storage.save(path,
                             ContentFile('file saved with path'))

        self.assertTrue(self.storage.exists(storage_f_name))
        self.assertEqual(self.storage.open(storage_f_name).read(),
            'file saved with path')

        info = self.file_info(storage_f_name)

        self.assertEqual(info.filename, path)

    def test_file_path(self):
        f = ContentFile('custom contents')
        f_name = self.storage.save('test.file', f)

        self.assertRaises(NotImplementedError, self.storage.path, f_name)


class BlobstoreStorageTest(AppEngineStorageBaseTest, TestCase):
    def setUp(self):
        super(BlobstoreStorageTest, self).setUp()

        self.storage = AppEngineStorage(storage_service=BLOBSTORE_SERVICE)

        file_name = files.blobstore.create()

        with files.open(file_name, 'a') as f:
            f.write('abcdef')

        files.finalize(file_name)

        self.blob_key = files.blobstore.get_blob_key(file_name)
        self.file_key = str(self.blob_key)
        self.test_file_info = self.file_info(self.file_key)

    def file_info(self, name):
        key = BlobKey(name.split('/', 1)[0])
        return BlobInfo(key)

    def test_file_url(self):
        url = self.storage.url(self.file_key)
        self.assertEqual(url, '/_ah/img/%s' % self.file_key)

@unittest.skipUnless(cloudstorage, 'cloudstorage not installed')
class GSStorageTest(AppEngineStorageBaseTest, TestCase):
    def setUp(self):
        super(GSStorageTest, self).setUp()

        self.storage = AppEngineStorage(storage_service=CLOUD_STORAGE_SERVICE, cloud_storage_bucket='test_bucket')

        file_name = '/test_bucket/file.test'
        with cloudstorage.open(file_name, 'w') as f:
            f.write('abcdef')

        self.file_key = '/gs' + file_name
        self.test_file_info = self.file_info(self.file_key)

    def file_info(self, name):
        return CloudStorageInfo(name)

    def test_file_url(self):
        url = self.storage.url(self.file_key)
        self.assertTrue(url.startswith('/_ah/img/encoded_gs_file:'))
