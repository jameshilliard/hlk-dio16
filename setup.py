#!/usr/bin/env python

from setuptools import setup

setup(
        name='hlk-dio16',
        version='0.0.1',
        description='Python client for HLK-DIO16',
        url='https://github.com/jameshilliard/hlk-dio16',
        author='James Hilliard',
        author_email='james.hilliard1@gmail.com',
        license='MIT',
        packages=[
            'hlk_dio16',
            'hlk_dio16.tools'
            ],
        )
