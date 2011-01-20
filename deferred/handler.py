# Initialize Django
from djangoappengine.main.main import make_profileable

from google.appengine.ext.deferred.handler import main

main = make_profileable(main)

if __name__ == '__main__':
    main()
