jtypes.javabridge documentation
===============================

.. include:: README.rst

jtypes.javabridge: running and interacting with the JVM from Python
===================================================================

The jtypes.javabridge Python package makes it easy to start a Java virtual machine (JVM)
from Python and interact with it. Python code can interact with the JVM using a low-level
API or a more convenient high-level API.

jtypes.javabridge is an almost fully compliant implementation of Lee Kamentsky's and
Vebjorn Ljosa's good known Javabridge package.

`PyPI record <https://pypi.python.org/pypi/jtypes.javabridge>`_

Original javabridge was developed for `CellProfiler <http://cellprofiler.org/>`_, where it is
used together with `python-bioformats <http://github.com/CellProfiler/python-bioformats/>`_
to interface to various Java code, including `Bio-Formats <http://loci.wisc.edu/software/bio-
formats>`_ and `ImageJ <http://developer.imagej.net/>`_.

`Original documentation <http://pythonhosted.org/javabridge/>`_ 

Contents:

.. toctree::
   :maxdepth: 2

   installation.rst
   hello.rst
   start_kill.rst
   javascript.rst
   highlevel.rst
   lowlevel.rst
   java2python.rst
   unittesting.rst
   developers.rst

   CHANGES.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
