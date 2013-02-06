from setuptools import find_packages, setup


DESCRIPTION = 'App Engine backends for Django-nonrel'
LONG_DESCRIPTION = None
try:
    LONG_DESCRIPTION = open('README.rst').read()
except:
    pass


setup(name='djangoappengine',
      version='1.0',
      packages=find_packages(exclude=['docs']),
      install_requires=['djangotoolbox'],
      author='Waldemar Kornewald',
      author_email='wkornewald@gmail.com',
      url='https://github.com/django-nonrel/djangoappengine',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      license='3-clause BSD',
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
