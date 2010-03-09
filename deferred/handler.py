import os, sys

parent_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Initialize Django
from djangoappengine.main import main as gaemain

# Import and run the actual handler
from google.appengine.ext.deferred.handler import main
if __name__ == '__main__':
    main()
