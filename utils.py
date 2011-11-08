from google.appengine.api import apiproxy_stub_map
from google.appengine.api.app_identity import get_application_id
import os

have_appserver = bool(apiproxy_stub_map.apiproxy.GetStub('datastore_v3'))

if have_appserver:
    appid = get_application_id()
else:
    try:
        from google.appengine.tools import dev_appserver
        from .boot import PROJECT_DIR
        appconfig = dev_appserver.LoadAppConfig(PROJECT_DIR, {},
                                                default_partition='dev')[0]
        appid = appconfig.application.split('~', 1)[-1]
    except ImportError, e:
        raise Exception('Could not get appid. Is your app.yaml file missing? '
                        'Error was: %s' % e)

on_production_server = have_appserver and \
    not os.environ.get('SERVER_SOFTWARE', '').lower().startswith('devel')
