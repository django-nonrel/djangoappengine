# Initialize Django.
from djangoappengine import main
from django.utils.importlib import import_module
from django.conf import settings

# Load all models.py to ensure signal handling installation or index
# loading of some apps.
for app in settings.INSTALLED_APPS:
    try:
        import_module('%s.models' % app)
    except ImportError:
        pass
try:
    from mapreduce.main import APP as application, main
except ImportError:
    from google.appengine.ext.mapreduce.main import APP as application, main


if __name__ == '__main__':
    main()
