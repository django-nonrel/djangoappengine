from django.conf import settings
from django.utils.importlib import import_module
from django.http import HttpResponse

def warmup(request):
    """
    Provides default procedure for handling warmup requests on App Engine.
    Just add this view to your main urls.py.
    """
    for app in settings.INSTALLED_APPS:
        for name in ('urls', 'views'):
            try:
                import_module('%s.%s' % (app, name))
            except ImportError:
                pass
    content_type = 'text/plain; charset=%s' % settings.DEFAULT_CHARSET
    return HttpResponse('Warmup done', content_type=content_type)
