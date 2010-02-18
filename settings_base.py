from djangoappengine.utils import on_production_server, have_appserver

DEBUG = not on_production_server
TEMPLATE_DEBUG = DEBUG

ROOT_URLCONF = 'urls'

DATABASES = {
    'default': {
        'ENGINE': 'djangoappengine.db',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
        'SUPPORTS_TRANSACTIONS': False,
    },
}

if on_production_server:
    EMAIL_BACKEND = 'djangoappengine.mail.AsyncEmailBackend'
else:
    EMAIL_BACKEND = 'djangoappengine.mail.EmailBackend'

FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
FILE_UPLOAD_HANDLERS = (
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
)

CACHE_BACKEND = 'memcached://?timeout=0'
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

if not on_production_server:
    INTERNAL_IPS = ('127.0.0.1',)
