#!/usr/bin/env python
# -*- coding: utf8 -*-
# vim: ts=4 sw=4 et ai:

import pathlib
from setuptools import setup

base = pathlib.Path(__file__).parent

README = (base / 'README.md').read_text()

setup(
      name='tftpy3',
      version='0.1.0',
      description='Python TFTP library',
      long_description=README,
      long_description_content_type='text/markdown',
      author='Michael P. Soulier',
      author_email='msoulier@digitaltorque.ca',
      url='http://github.com/jcarswell/tftpy',
      packages=['tftpy'],
      project_urls={
          'Source': 'https://github.com/jcarswell/tftpy/',
          'Tracker': 'https://github.com/jcarswell/tftpy/issues',
      },
      python_requires='>=3.6',
      classifiers=[
        'Programming Language :: Python :: 3.6',
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Internet',
        ]
      )
