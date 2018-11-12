# Copyright (c) 2014-2018, Adam Karpierz
# Licensed under the BSD license
# http://opensource.org/licenses/BSD-3-Clause

from __future__ import absolute_import, print_function

import unittest
import sys
import os
import importlib
import logging

from . import test_dir

test_java = os.path.join(test_dir, "java")


def test_suite(names=None, omit=("run",)):

    from . import __name__ as pkg_name
    from . import __path__ as pkg_path
    import unittest
    import pkgutil
    if names is None:
        names = [name for _, name, _ in pkgutil.iter_modules(pkg_path)
                 if name != "__main__" and name not in omit]
    names = [".".join((pkg_name, name)) for name in names]
    tests = unittest.defaultTestLoader.loadTestsFromNames(names)
    return tests


def main():

    sys.modules["javabridge"]           = importlib.import_module("jt.javabridge")
    sys.modules["javabridge.__about__"] = importlib.import_module("jt.javabridge.__about__")
    sys.modules["javabridge.jutil"]     = importlib.import_module("jt.javabridge.jutil")
    sys.modules["javabridge.locate"]    = importlib.import_module("jt.javabridge.locate")
    sys.modules["javabridge.wrappers"]  = importlib.import_module("jt.javabridge.wrappers")

    print("Running testsuite", "\n", file=sys.stderr)

    import javabridge as jb

    with jb.vm(class_path=[os.path.join(test_java, "classes")] + jb.JARS,
               max_heap_size="512M"):
        tests = test_suite(sys.argv[1:] or None)
        result = unittest.TextTestRunner(verbosity=2).run(tests)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__.rpartition(".")[-1] == "__main__":
    # logging.basicConfig(level=logging.INFO)
    # logging.basicConfig(level=logging.DEBUG)
    main()
