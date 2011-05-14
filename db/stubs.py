from ..utils import appid, have_appserver
from google.appengine.ext.testbed import Testbed
from urllib2 import HTTPError, URLError
import logging
import time

REMOTE_API_SCRIPT = '$PYTHON_LIB/google/appengine/ext/remote_api/handler.py'

def auth_func():
    import getpass
    return raw_input('Login via Google Account (see note above if login fails): '), getpass.getpass('Password: ')

def rpc_server_factory(*args, ** kwargs):
    from google.appengine.tools import appengine_rpc
    kwargs['save_cookies'] = True
    return appengine_rpc.HttpRpcServer(*args, ** kwargs)

class StubManager(object):
    def __init__(self):
        self.testbed = Testbed()
        self.active_stubs = None
        self.pre_test_stubs = None

    def setup_stubs(self, connection):
        if self.active_stubs is not None:
            return
        if not have_appserver:
            self.setup_local_stubs(connection)

    def activate_test_stubs(self):
        if self.active_stubs == 'test':
            return
        self.testbed.activate()
        self.pre_test_stubs = self.active_stubs
        self.active_stubs = 'test'
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        self.testbed.init_urlfetch_stub()
        self.testbed.init_user_stub()
        self.testbed.init_xmpp_stub()
        self.testbed.init_channel_stub()

    def deactivate_test_stubs(self):
        if self.active_stubs == 'test':
            self.testbed.deactivate()
            self.active_stubs = self.pre_test_stubs

    def setup_local_stubs(self, connection):
        if self.active_stubs == 'local':
            return
        from .base import get_datastore_paths
        from google.appengine.tools import dev_appserver_main
        args = dev_appserver_main.DEFAULT_ARGS.copy()
        args.update(get_datastore_paths(connection.settings_dict))
        log_level = logging.getLogger().getEffectiveLevel()
        logging.getLogger().setLevel(logging.WARNING)
        from google.appengine.tools import dev_appserver
        dev_appserver.SetupStubs(appid, **args)
        logging.getLogger().setLevel(log_level)
        self.active_stubs = 'local'

    def setup_remote_stubs(self, connection):
        if self.active_stubs == 'remote':
            return
        if not connection.remote_api_path:
            from ..utils import appconfig
            for handler in appconfig.handlers:
                if handler.script == REMOTE_API_SCRIPT:
                    connection.remote_api_path = handler.url.split('(', 1)[0]
                    break
        server = '%s.%s' % (connection.remote_app_id, connection.domain)
        remote_url = 'https://%s%s' % (server, connection.remote_api_path)
        logging.info('Setting up remote_api for "%s" at %s' %
                     (connection.remote_app_id, remote_url))
        if not have_appserver:
            print('Connecting to remote_api handler.\n\n'
                  'IMPORTANT: Check your login method settings in the '
                  'App Engine Dashboard if you have problems logging in. '
                  'Login is only supported for Google Accounts.\n')
        from google.appengine.ext.remote_api import remote_api_stub
        remote_api_stub.ConfigureRemoteApi(None,
            connection.remote_api_path, auth_func, servername=server,
            secure=connection.secure_remote_api,
            rpc_server_factory=rpc_server_factory)
        retry_delay = 1
        while retry_delay <= 16:
            try:
                remote_api_stub.MaybeInvokeAuthentication()
            except HTTPError, e:
                if not have_appserver:
                    print 'Retrying in %d seconds...' % retry_delay
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                break
        else:
            try:
                remote_api_stub.MaybeInvokeAuthentication()
            except HTTPError, e:
                raise URLError("%s\n"
                               "Couldn't reach remote_api handler at %s.\n"
                               "Make sure you've deployed your project and "
                               "installed a remote_api handler in app.yaml. "
                               "Note that login is only supported for "
                               "Google Accounts. Make sure you've configured "
                               "the correct authentication method in the "
                               "App Engine Dashboard."
                               % (e, remote_url))
        logging.info('Now using the remote datastore for "%s" at %s' %
                     (connection.remote_app_id, remote_url))
        self.active_stubs = 'remote'

stub_manager = StubManager()
