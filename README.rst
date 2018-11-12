**Currently only as placeholder (because a base package jtypes.jvm is still in development)**

jtypes.javabridge
=================

Python wrapper for the Java Native Interface.

Overview
========

  | **jtypes.javabridge** is a bridge between Python and Java, allowing these to intercommunicate.
  | It is an effort to allow python programs full access to Java class libraries.

  `PyPI record`_.

  | **jtypes.javabridge** is a lightweight Python package, based on the *ctypes* or *cffi* library.
  | It is an almost fully compliant implementation of Lee Kamentsky's and Vebjorn Ljosa's
    **Javabridge** package by reimplementing whole its functionality in a clean Python instead of
    Cython and C.

About javabridge:
-----------------

Borrowed from the `original website`_:

  | The **javabridge** Python package makes it easy to start a Java virtual
    machine (JVM) from Python and interact with it. Python code can interact
    with the JVM using a low-level API or a more convenient high-level API.

Requirements
============

- Java Runtime (JRE) or Java Development Kit (JDK), and NumPy (not mandatory but highly
  recommended).

Installation
============

Prerequisites:

+ Python 2.7 or higher or 3.4 or higher

  * http://www.python.org/
  * 2.7 and 3.6 are primary test environments.

+ pip and setuptools

  * http://pypi.python.org/pypi/pip
  * http://pypi.python.org/pypi/setuptools

To install run::

    python -m pip install --upgrade jtypes.javabridge

To ensure everything is running correctly you can run the tests using::

    python -m jt.javabridge.tests

Development
===========

Visit `development page`_

Installation from sources:

Clone the `sources`_ and run::

    python -m pip install ./jtypes.javabridge

or on development mode::

    python -m pip install --editable ./jtypes.javabridge

Prerequisites:

+ Development is strictly based on *tox*. To install it run::

    python -m pip install tox

License
=======

  | Copyright (c) 2014-2018, Adam Karpierz
  |
  | Licensed under the BSD license
  | http://opensource.org/licenses/BSD-3-Clause
  | Please refer to the accompanying LICENSE file.

Authors
=======

* Adam Karpierz <adam@karpierz.net>

.. _PyPI record: https://pypi.python.org/pypi/jtypes.javabridge
.. _original website: http://pythonhosted.org/javabridge
.. _development page: https://github.com/karpierz/jtypes.javabridge
.. _sources: https://github.com/karpierz/jtypes.javabridge
