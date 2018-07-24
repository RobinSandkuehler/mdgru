#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name="mdgru",
    version="0.1.201805190007",
    description="Segmentation Suite for multi-dimensional gated recurrent units (MDGRU)",
    long_description="Details can be found in the Readme file",
    author="Simon Andermatt",
    author_email="simon.andermatt@unibas.ch",
    url="https://github.com/zubata88/mdgru",
    packages=["mdgru"],
    license="LGPL",
    python_requires='>=3.5',
    install_requires=["nibabel", "numpy", "scipy", "pydicom", "matplotlib", "scikit-image", "tensorflow-gpu>=1.8"],
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Programming Language :: Python :: 3',
    ],
)