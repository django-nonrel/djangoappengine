import logging
import os
import sys

PROJECT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Overrides for os.environ
env_ext = {'DJANGO_SETTINGS_MODULE': 'settings'}

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
                 '/usr/local/google_appengine',
                 '/Applications/GoogleAppEngineLauncher.app/Contents/Resources/GoogleAppEngine-default.bundle/Contents/Resources/google_appengine']
        for path in os.environ.get('PATH', '').split(os.pathsep):
            path = path.rstrip(os.sep)
            if path.endswith('google_appengine'):
                paths.append(path)
        if os.name in ('nt', 'dos'):
            path = r'%(PROGRAMFILES)s\Google\google_appengine' % os.environ
            paths.append(path)
        # Loop through all possible paths and look for the SDK dir.
        sdk_path = None
        for path in paths:
            path = os.path.realpath(path)
            if os.path.exists(path):
                sdk_path = path
                break
        if sdk_path is None:
            # The SDK could not be found in any known location.
            sys.stderr.write('The Google App Engine SDK could not be found!\n'
                             "Make sure it's accessible via your PATH "
                             "environment and called google_appengine.")
            sys.exit(1)
        # Add the SDK and the libraries within it to the system path.
        extra_paths = [sdk_path]
        lib = os.path.join(sdk_path, 'lib')
        # Automatically add all packages in the SDK's lib folder:
        for dir in os.listdir(lib):
            path = os.path.join(lib, dir)
            # Package can be under 'lib/<pkg>/<pkg>/' or 'lib/<pkg>/lib/<pkg>/'
            detect = (os.path.join(path, dir), os.path.join(path, 'lib', dir))
            for path in detect:
                if os.path.isdir(path) and not dir == 'django':
                    extra_paths.append(os.path.dirname(path))
                    break
        sys.path = extra_paths + sys.path
        from google.appengine.api import apiproxy_stub_map

    setup_project()
    from .utils import have_appserver
    if have_appserver:
        # App Engine's threading.local is broken
        setup_threading()
    setup_logging()

    if not have_appserver:
        # Patch Django to support loading management commands from zip files
        from django.core import management
        management.find_commands = find_commands

def find_commands(management_dir):
    """
    Given a path to a management directory, returns a list of all the command
    names that are available.
    This version works for django deployments which are file based or
    contained in a ZIP (in sys.path).

    Returns an empty list if no commands are defined.
    """
    import pkgutil
    return [modname for importer, modname, ispkg in pkgutil.iter_modules(
                [os.path.join(management_dir, 'commands')]) if not ispkg]

def setup_threading():
    # XXX: GAE's threading.local doesn't work correctly with subclassing
    try:
        from django.utils._threading_local import local
        import threading
        threading.local = local
    except ImportError:
        pass

def setup_logging():
    # Fix Python 2.6 logging module
    logging.logMultiprocessing = 0

    # Enable logging
    level = logging.DEBUG
    from .utils import have_appserver
    if have_appserver:
        # We can't import settings at this point when running a normal
        # manage.py command because this module gets imported from settings.py
        from django.conf import settings
        if not settings.DEBUG:
            level = logging.INFO
    logging.getLogger().setLevel(level)

def setup_project():
    from .utils import have_appserver, on_production_server
    if have_appserver:
        # This fixes a pwd import bug for os.path.expanduser()
        env_ext['HOME'] = PROJECT_DIR

    # The dev_appserver creates a sandbox which restricts access to certain
    # modules and builtins in order to emulate the production environment.
    # Here we get the subprocess module back into the dev_appserver sandbox.
    # This module is just too important for development.
    # Also we add the compiler/parser module back and enable https connections
    # (seem to be broken on Windows because the _ssl module is disallowed).
    if not have_appserver:
        from google.appengine.tools import dev_appserver
        try:
            # Backup os.environ. It gets overwritten by the dev_appserver,
            # but it's needed by the subprocess module.
            env = dev_appserver.DEFAULT_ENV
            dev_appserver.DEFAULT_ENV = os.environ.copy()
            dev_appserver.DEFAULT_ENV.update(env)
            # Backup the buffer() builtin. The subprocess in Python 2.5 on
            # Linux and OS X uses needs it, but the dev_appserver removes it.
            dev_appserver.buffer = buffer
        except AttributeError:
            logging.warn('Could not patch the default environment. '
                         'The subprocess module will not work correctly.')

        try:
            # Allow importing compiler/parser and _ssl modules (for https)
            dev_appserver.HardenedModulesHook._WHITE_LIST_C_MODULES.extend(
                ('parser', '_ssl'))
        except AttributeError:
            logging.warn('Could not patch modules whitelist. '
                         'The compiler and parser modules will not work and '
                         'SSL support is disabled.')
    elif not on_production_server:
        try:
            # Restore the real subprocess module
            from google.appengine.api.mail_stub import subprocess
            sys.modules['subprocess'] = subprocess
            # Re-inject the buffer() builtin into the subprocess module
            from google.appengine.tools import dev_appserver
            subprocess.buffer = dev_appserver.buffer
        except Exception, e:
            logging.warn('Could not add the subprocess module to the sandbox: %s' % e)

    os.environ.update(env_ext)

    extra_paths = [PROJECT_DIR, os.path.join(os.path.dirname(__file__), 'lib')]
    zip_packages_dir = os.path.join(PROJECT_DIR, 'zip-packages')

    # We support zipped packages in the common and project folders.
    if os.path.isdir(zip_packages_dir):
        for zip_package in os.listdir(zip_packages_dir):
            extra_paths.append(os.path.join(zip_packages_dir, zip_package))

    # App Engine causes main.py to be reloaded if an exception gets raised
    # on the first request of a main.py instance, so don't call setup_project()
    # multiple times. We ensure this indirectly by checking if we've already
    # modified sys.path.
    if len(sys.path) < len(extra_paths) or \
            sys.path[:len(extra_paths)] != extra_paths:

        sys.path = extra_paths + sys.path
