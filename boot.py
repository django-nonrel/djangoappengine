import os, sys

# We allow a two-level project structure where your root folder contains
# project-specific apps and the "common" subfolder contains common apps.
COMMON_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
PROJECT_DIR = os.path.dirname(COMMON_DIR)
if os.path.basename(COMMON_DIR) == 'common-apps':
    MAIN_DIRS = (PROJECT_DIR, COMMON_DIR)
else:
    PROJECT_DIR = COMMON_DIR
    MAIN_DIRS = (PROJECT_DIR,)

# Overrides for os.environ
env_ext = {}
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    env_ext['DJANGO_SETTINGS_MODULE'] = 'settings'

def setup_env():
    """Configures app engine environment for command-line apps."""
    # Try to import the appengine code from the system path.
    try:
        from google.appengine.api import apiproxy_stub_map
    except ImportError:
        for k in [k for k in sys.modules if k.startswith('google')]:
            del sys.modules[k]

        # Not on the system path. Build a list of alternative paths where it
        # may be. First look within the project for a local copy, then look for
        # where the Mac OS SDK installs it.
        paths = [os.path.join(PROJECT_DIR, '.google_appengine'),
                 os.path.join(COMMON_DIR, '.google_appengine'),
                 '/usr/local/google_appengine',
                 '/Applications/GoogleAppEngineLauncher.app/Contents/Resources/GoogleAppEngine-default.bundle/Contents/Resources/google_appengine']
        for path in os.environ.get('PATH', '').replace(';', ':').split(':'):
            path = path.rstrip(os.sep)
            if path.endswith('google_appengine'):
                paths.append(path)
        if os.name in ('nt', 'dos'):
            prefix = '%(PROGRAMFILES)s' % os.environ
            paths.append(prefix + r'\Google\google_appengine')
        # Loop through all possible paths and look for the SDK dir.
        SDK_PATH = None
        for sdk_path in paths:
            sdk_path = os.path.realpath(sdk_path)
            if os.path.exists(sdk_path):
                SDK_PATH = sdk_path
                break
        if SDK_PATH is None:
            # The SDK could not be found in any known location.
            sys.stderr.write('The Google App Engine SDK could not be found!\n'
                             "Make sure it's accessible via your PATH "
                             "environment and called google_appengine.")
            sys.exit(1)
        # Add the SDK and the libraries within it to the system path.
        EXTRA_PATHS = [SDK_PATH]
        lib = os.path.join(SDK_PATH, 'lib')
        # Automatically add all packages in the SDK's lib folder:
        for dir in os.listdir(lib):
            path = os.path.join(lib, dir)
            # Package can be under 'lib/<pkg>/<pkg>/' or 'lib/<pkg>/lib/<pkg>/'
            detect = (os.path.join(path, dir), os.path.join(path, 'lib', dir))
            for path in detect:
                if os.path.isdir(path) and not dir == 'django':
                    EXTRA_PATHS.append(os.path.dirname(path))
                    break
        sys.path = EXTRA_PATHS + sys.path
        from google.appengine.api import apiproxy_stub_map

    setup_project()
    setup_logging()

def setup_threading():
    # XXX: GAE's threading.local doesn't work correctly with subclassing
    try:
        from django.utils._threading_local import local
        import threading
        threading.local = local
    except ImportError:
        pass

def setup_logging():
    import logging

    # Fix Python 2.6 logging module
    logging.logMultiprocessing = 0

    # Enable logging
    from django.conf import settings
    if settings.DEBUG:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

def setup_project():
    from .utils import have_appserver
    if have_appserver:
        # This fixes a pwd import bug for os.path.expanduser()
        global env_ext
        env_ext['HOME'] = PROJECT_DIR

    os.environ.update(env_ext)

    EXTRA_PATHS = list(MAIN_DIRS)
    EXTRA_PATHS.append(os.path.dirname(PROJECT_DIR))
    EXTRA_PATHS.append(os.path.join(os.path.dirname(__file__), 'lib'))

    ZIP_PACKAGES_DIRS = tuple(os.path.join(dir, 'zip-packages')
                              for dir in MAIN_DIRS)

    # We support zipped packages in the common and project folders.
    for packages_dir in ZIP_PACKAGES_DIRS:
        if os.path.isdir(packages_dir):
            for zip_package in os.listdir(packages_dir):
                EXTRA_PATHS.append(os.path.join(packages_dir, zip_package))

    # App Engine causes main.py to be reloaded if an exception gets raised
    # on the first request of a main.py instance, so don't call setup_project()
    # multiple times. We ensure this indirectly by checking if we've already
    # modified sys.path.
    if len(sys.path) < len(EXTRA_PATHS) or \
            sys.path[:len(EXTRA_PATHS)] != EXTRA_PATHS:

        sys.path = EXTRA_PATHS + sys.path
