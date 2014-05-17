import os

from google.appengine.api import apiproxy_stub_map
from google.appengine.api.app_identity import get_application_id

have_appserver = bool(apiproxy_stub_map.apiproxy.GetStub('datastore_v3'))

if have_appserver:
    appid = get_application_id()
else:
    try:
        from google.appengine.tools.devappserver2 import application_configuration
        from djangoappengine.boot import PROJECT_DIR
        appconfig = application_configuration.ApplicationConfiguration([PROJECT_DIR])
        appid = appconfig.app_id.replace('dev~', '')
    except ImportError, e:
        raise Exception("Could not get appid. Is your app.yaml file missing? "
                        "Error was: %s" % e)

on_production_server = have_appserver and \
    not os.environ.get('SERVER_SOFTWARE', '').lower().startswith('devel')
