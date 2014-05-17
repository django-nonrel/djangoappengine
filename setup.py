from setuptools import find_packages, setup


DESCRIPTION = 'App Engine backends for Django-nonrel'
LONG_DESCRIPTION = None
try:
    LONG_DESCRIPTION = open('README.rst').read()
except:
    pass

setup(name='djangoappengine',
      version='1.6.3',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      author='Waldemar Kornewald',
      author_email='wkornewald@gmail.com',
      url='https://github.com/django-nonrel/djangoappengine',
      packages=find_packages(exclude=['docs']),
      include_package_data=True,
      install_requires=['djangotoolbox>=1.6.0'],
      zip_safe=False,
      license='3-clause BSD',
      test_suite='djangoappengine.tests',
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
