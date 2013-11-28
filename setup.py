from distutils.core import setup
import os

def get_packages(package):
    return [dirpath
            for dirpath, dirnames, filenames in os.walk(package)
            if os.path.exists(os.path.join(dirpath, '__init__.py'))]


DESCRIPTION = 'App Engine backends for Django-nonrel'
LONG_DESCRIPTION = None
try:
    LONG_DESCRIPTION = open('README.rst').read()
except:
    pass

setup(name='djangoappengine',
      version='1.6.0',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      author='Waldemar Kornewald',
      author_email='wkornewald@gmail.com',
      url='https://github.com/django-nonrel/djangoappengine',
      packages=get_packages('djangoappengine'),
      requires=['djangotoolbox (>=1.6.0)'],
      license='3-clause BSD',
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Environment :: Web Environment',
          'Framework :: Django',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.5',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Topic :: Database',
          'Topic :: Software Development :: Libraries :: Application Frameworks',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ],
)
