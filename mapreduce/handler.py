# Initialize Django
from djangoappengine.main.main import make_profileable
from django.utils.importlib import import_module
from django.conf import settings

# load all models.py to ensure signal handling installation or index loading
# of some apps
for app in settings.INSTALLED_APPS:
    try:
        import_module('%s.models' % app)
    except ImportError:
        pass

from google.appengine.ext.mapreduce.main import APP as application, main

main = make_profileable(main)

if __name__ == '__main__':
    main()
