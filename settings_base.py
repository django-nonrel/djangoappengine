# Initialize App Engine SDK if necessary
try:
    from google.appengine.api import apiproxy_stub_map
except ImportError:
    from .boot import setup_env
    setup_env()

from djangoappengine.utils import on_production_server, have_appserver

DEBUG = not on_production_server
TEMPLATE_DEBUG = DEBUG

ROOT_URLCONF = 'urls'

DATABASES = {
    'default': {
        'ENGINE': 'djangoappengine.db',

        # Other settings which you might want to override in your settings.py

        # Activates high-replication support for remote_api
        # 'HIGH_REPLICATION': True,

        # Switch to the App Engine for Business domain
        # 'DOMAIN': 'googleplex.com',

        'DEV_APPSERVER_OPTIONS': {
            # Optional parameters for development environment

            # Emulate the high-replication datastore locally
            # 'high_replication' : True,

            # Use the SQLite backend for local storage (instead of default
            # in-memory datastore). Useful for testing with larger datasets
            # or when debugging concurrency/async issues (separate processes
            # will share a common db state, rather than syncing on startup).
            # 'use_sqlite': True,
            }
    },
}

if on_production_server:
    EMAIL_BACKEND = 'djangoappengine.mail.AsyncEmailBackend'
else:
    EMAIL_BACKEND = 'djangoappengine.mail.EmailBackend'

# Specify a queue name for the async. email backend
EMAIL_QUEUE_NAME = 'default'

PREPARE_UPLOAD_BACKEND = 'djangoappengine.storage.prepare_upload'
SERVE_FILE_BACKEND = 'djangoappengine.storage.serve_file'
DEFAULT_FILE_STORAGE = 'djangoappengine.storage.BlobstoreStorage'
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
FILE_UPLOAD_HANDLERS = (
    'djangoappengine.storage.BlobstoreFileUploadHandler',
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'TIMEOUT': 0,
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

if not on_production_server:
    INTERNAL_IPS = ('127.0.0.1',)
