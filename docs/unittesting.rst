.. _unit-testing:

Unit testing
============

Unit testing of code that uses the *jtypes.javabridge* requires special care
because the JVM can only be run once: after you kill it, it cannot be restarted.
Therefore, the JVM cannot be started and stopped in the regular ``setUp()``
and ``tearDown()`` methods.

You should then be able to run the ``tests`` module::

    python -m jt.javabridge.tests

On some installations, setuptools's test command will also work::

    python setup.py test

If you prefer, these options can also be given on the command line::

    nosetests --with-javabridge=True --classpath=my-project/jars/foo.jar

or::

    python setup.py nosetests --with-javabridge=True --classpath=my-project/jars/foo.jar
