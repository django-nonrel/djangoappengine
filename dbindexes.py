from django.conf import settings

if 'django.contrib.auth' in settings.INSTALLED_APPS:
    from dbindexer.api import register_index
    from django.contrib.auth.models import User

    register_index(User, {
        'username': 'iexact',
        'email': 'iexact',
    })
