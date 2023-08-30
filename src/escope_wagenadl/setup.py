#!/usr/bin/env python

from distutils.core import setup

setup(name='EScope',
      version='2.0.0',
      description='EScope and ESpark',
      author='Daniel Wagenaar',
      author_email='daw@caltech.edu',
      url='http://www.danielwagenaar.net',
      packages=['escopelib'],
      scripts=['escope-postinst.py', 'escope', 'espark',  ],
     )
