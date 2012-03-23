from setuptools import find_packages, setup


DESCRIPTION = 'App Engine backends for Django-nonrel'
LONG_DESCRIPTION = None
try:
    LONG_DESCRIPTION = open('README.rst').read()
except:
    pass


setup(name='djangoappengine',
      version='1.0',
      package_dir={'djangoappengine': '.'},
      packages=['djangoappengine'] + ['djangoappengine.' + name
                                      for name in find_packages()],
      author='Waldemar Kornewald',
      author_email='wkornewald@gmail.com',
      url='http://www.allbuttonspressed.com/projects/djangoappengine',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      platforms=['any'],
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Environment :: Web Environment',
          'Framework :: Django',
          'Intended Audience :: Developers',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Software Development :: Libraries :: Application Frameworks',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'License :: OSI Approved :: BSD License',
        ],
)
