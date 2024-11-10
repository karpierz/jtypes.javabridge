jtypes.javabridge
=================

Python wrapper for the Java Native Interface.

Overview
========

The |package_bold| package makes it easy to start a Java virtual machine (JVM)
from Python and interact with it. Python code can interact with the JVM using
a low-level API or a more convenient high-level API.

`PyPI record`_.

`Documentation`_.

| |package_bold| is an almost fully compliant implementation of Lee Kamentsky's
  and Vebjorn Ljosa's good known **Javabridge** package by reimplementing whole
  its functionality in a clean Python instead of Cython and C.
| |package_bold| package is closely based on the `jvm`_ and `jni`_ Python packages.

About javabridge:
-----------------

Borrowed from the `original website`_:

| The **javabridge** Python package makes it easy to start a Java virtual machine
  (JVM) from Python and interact with it.
| Python code can interact with the JVM using a low-level API or a more convenient
  high-level API.

The **javabridge** was developed for and is used by the cell image analysis
software `CellProfiler <https://cellprofiler.org/>`_ together with
`python-bioformats <https://github.com/CellProfiler/python-bioformats/>`_
to interface to various Java code, including `Bio-Formats <https://loci.wisc.edu/
software/bio-formats>`_ and `ImageJ <https://developer.imagej.net/>`_.

Requirements
============

- Java Runtime (JRE) or Java Development Kit (JDK), and NumPy (not mandatory but
  highly recommended).

Installation
============

Prerequisites:

+ Python 3.9 or higher

  * https://www.python.org/
  * Java 11 is a primary test environment.

+ pip and setuptools

  * https://pypi.org/project/pip/
  * https://pypi.org/project/setuptools/

To install run:

  .. parsed-literal::

    python -m pip install --upgrade |package|

Development
===========

Prerequisites:

+ Development is strictly based on *tox*. To install it run::

    python -m pip install --upgrade tox

Visit `Development page`_.

Installation from sources:

clone the sources:

  .. parsed-literal::

    git clone |respository| |package|

and run:

  .. parsed-literal::

    python -m pip install ./|package|

or on development mode:

  .. parsed-literal::

    python -m pip install --editable ./|package|

License
=======

  | |copyright|
  | Licensed under the BSD license
  | https://opensource.org/licenses/BSD-3-Clause
  | Please refer to the accompanying LICENSE file.

Authors
=======

* Adam Karpierz <adam@karpierz.net>

.. |package| replace:: jtypes.javabridge
.. |package_bold| replace:: **jtypes.javabridge**
.. |copyright| replace:: Copyright (c) 2014-2024, Adam Karpierz
.. |respository| replace:: https://github.com/karpierz/jtypes.javabridge.git
.. _Development page: https://github.com/karpierz/jtypes.javabridge
.. _PyPI record: https://pypi.org/project/jtypes.javabridge/
.. _Documentation: https://jtypesjavabridge.readthedocs.io/
.. _jvm: https://pypi.org/project/jvm/
.. _jni: https://pypi.org/project/jni/
.. _original website: https://pythonhosted.org/javabridge/
