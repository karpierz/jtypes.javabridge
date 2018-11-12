'''test_cpython.py - test the JNI CPython class

python-javabridge is licensed under the BSD license.  See the
accompanying file LICENSE for details.

Copyright (c) 2003-2009 Massachusetts Institute of Technology
Copyright (c) 2009-2013 Broad Institute
All rights reserved.

'''
from __future__ import absolute_import
import unittest
import javabridge

class TestCPython(unittest.TestCase):
    def setUp(self):
        self.cpython = javabridge.JClassWrapper(
            "org.cellprofiler.javabridge.CPython")()

    def test_01_01_exec(self):
        self.cpython.execute("pass")
        # <AK> added
        with self.assertRaisesRegex(javabridge.JavaException, "Script was null"):
            self.cpython.execute(None)
        with self.assertRaisesRegex(javabridge.JavaException, "Python exception at"):
            self.cpython.execute("invalid syntax")
        # </AK>
        
    def test_01_02_locals(self):
        jlocals = javabridge.JClassWrapper('java.util.HashMap')()
        jref = javabridge.JClassWrapper('java.util.ArrayList')()
        jlocals.put("numerator", "6")
        jlocals.put("denominator", "2")
        code = """
global javabridge
import javabridge
def fn(numerator, denominator, answer):
    result = int(numerator) // int(denominator)  # <AK> was: /
    javabridge.call(answer, "add", "(Ljava/lang/Object;)Z", str(result))
fn(numerator, denominator, answer)
"""
        jlocals.put("code", code)
        jlocals.put("answer", jref.o)
        self.cpython.execute(code, jlocals.o, None)
        self.assertEqual(float(javabridge.to_string(jref.get(0))), 3)
        
    def test_01_03_globals(self):
        jglobals = javabridge.JClassWrapper('java.util.HashMap')()
        jref = javabridge.JClassWrapper('java.util.ArrayList')()
        jglobals.put("numerator", "6")
        jglobals.put("denominator", "2")
        jglobals.put("answer", jref.o)
        self.cpython.execute("""
global javabridge
import javabridge
def fn():
    result = int(numerator) // int(denominator)  # <AK> was: /
    javabridge.call(answer, "add", "(Ljava/lang/Object;)Z", str(result))
fn()
""", None, jglobals.o)
        self.assertEqual(float(javabridge.to_string(jref.get(0))), 3)

    def test_01_04_globals_equals_locals(self):
        jglobals = javabridge.JClassWrapper('java.util.HashMap')()
        jref = javabridge.JClassWrapper('java.util.ArrayList')()
        jglobals.put("numerator", "6")
        jglobals.put("denominator", "2")
        jglobals.put("answer", jref.o)
        #
        # The import will be added to "locals", but that will be the globals.
        #
        self.cpython.execute("""
import javabridge
def fn():
    result = int(numerator) // int(denominator)  # <AK> was: /
    javabridge.call(answer, "add", "(Ljava/lang/Object;)Z", str(result))
fn()
""", jglobals.o, jglobals.o)
        self.assertEqual(float(javabridge.to_string(jref.get(0))), 3)
