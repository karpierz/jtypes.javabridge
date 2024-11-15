'''test_javabridge.py - test the low-level interface

python-javabridge is licensed under the BSD license.  See the
accompanying file LICENSE for details.

Copyright (c) 2003-2009 Massachusetts Institute of Technology
Copyright (c) 2009-2013 Broad Institute
All rights reserved.

'''

__version__="$Revision$"

import os
import unittest
from collections import namedtuple  # <AK> added
# <AK> was:
# import numpy as np
try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

import javabridge
jb = javabridge

# <AK> added
from functools import partial
from jt.javabridge.__config__ import config
skipIfNumpyNotEnabled = partial(unittest.skipIf,
    not config.getboolean("NUMPY_ENABLED", True) or not np,
    "Numpy support is off or numpy is not available")
# </AK>


class TestJavabridge(unittest.TestCase):

    def setUp(self):
        self.env = javabridge.attach()
        # <AK> added (temporary!!!)
        if 0:#self.env.exception_occurred():
            import sys
            import jni
            print("\n@@ setUp", self.env.exception_occurred(), file=sys.stderr)
            self.env.exception_describe()
            print("@@ jni.Throwable.last", jni.Throwable.last, file=sys.stderr)
            #self.env.exception_clear()
            print("@@ /setUp", self.env.exception_occurred(),  file=sys.stderr)
        # </AK>
        self.env.exception_clear()  # <AK> added (temporary!!!)

    def tearDown(self):
        javabridge.detach()

    # <AK> added
    def test_00_01_jvm(self):
        save_JAVA_HOME = os.environ.get("JAVA_HOME")
        try:
            os.environ["JAVA_HOME"] = "non existent"
            with self.assertRaisesRegex(javabridge.JVMNotFoundError,
                                        "Can't find the Java Virtual Machine"):
                javabridge.start_vm()
        finally:
            if save_JAVA_HOME is not None: os.environ["JAVA_HOME"] = save_JAVA_HOME

    # <AK> added
    def test_00_02_version(self):
        self.assertTrue(repr(self.env).startswith("<JB_Env at 0x"))

    def test_01_01_version(self):
        major,minor = self.env.get_version()

    def test_01_02_find_class(self):
        string_class = self.env.find_class('java/lang/String')
        self.assertTrue(isinstance(string_class, jb.JB_Class))
        # <AK> added
        self.assertTrue(repr(string_class).startswith("<Java class at 0x"))
        # </AK>

    def test_01_03_00_new_string_utf(self):
        jstring = self.env.new_string_utf("Hello, world")
        self.assertTrue(isinstance(jstring, jb.JB_Object))
        # <AK> added
        rjstring = repr(jstring)
        self.assertTrue(rjstring.startswith("<Java object at 0x"))
        self.assertEqual(jstring.addr(),
                         str(int(rjstring.rpartition("<Java object at ")[2].partition(">")[0],
                                 base=16)))
        # </AK>

    def test_01_03_01_new_string_unicode(self):
        s = u"Hola ni\u00F1os"
        jstring = self.env.new_string(s)
        self.assertEqual(self.env.get_string_utf(jstring), s)

    def test_01_03_02_new_string_string(self):
        s = "Hello, world"
        jstring = self.env.new_string(s)
        self.assertEqual(self.env.get_string_utf(jstring), s)

    def test_01_03_03_new_string_zero_length(self):
        jstring = self.env.new_string(u"")
        self.assertEqual(self.env.get_string_utf(jstring), "")

    def test_01_04_00_get_string_utf(self):
        jstring = self.env.new_string_utf("Hello, world")
        pstring = self.env.get_string_utf(jstring)
        self.assertEqual(pstring, "Hello, world")

    def test_01_04_01_get_string(self):
        s = u"Hola ni\u00F1os"
        jstring = self.env.new_string(s)
        self.assertTrue(self.env.get_string(jstring), s)

    def test_01_05_get_object_class(self):
        jstring = self.env.new_string_utf("Hello, world")
        string_class = self.env.get_object_class(jstring)
        self.assertTrue(isinstance(string_class, jb.JB_Class))

    def test_01_06_deallocate_object(self):
        jstring = self.env.new_string_utf("Hello, world")
        del jstring

    def test_01_09_get_method_id(self):
        klass = self.env.find_class("java/lang/String")
        method_id = self.env.get_method_id(klass,'charAt','(I)C')
        self.assertTrue(method_id is not None)
        # <AK> added
        method_id = self.env.get_method_id(klass, 'charAt', '')
        self.assertTrue(method_id is None)
        with self.assertRaisesRegex(ValueError,
                                    "Class = None on call to get_method_id"):
            method_id = self.env.get_method_id(None, 'charAt', '(I)C')
        # </AK>

    def test_01_10_get_static_method_id(self):
        klass = self.env.find_class("java/lang/String")
        method_id = self.env.get_static_method_id(klass, 'copyValueOf','([C)Ljava/lang/String;')
        self.assertTrue(method_id is not None)
        # <AK> added
        method_id = self.env.get_static_method_id(klass, 'copyValueOf', '')
        self.assertTrue(method_id is None)
        # </AK>

    def test_01_11_new_object(self):
        klass = self.env.find_class("java/lang/Byte")
        method_id = self.env.get_method_id(klass, '<init>','(Ljava/lang/String;)V')
        jbyte = self.env.new_object(klass, method_id, self.env.new_string_utf("55"))
        self.assertTrue(jbyte is not None)

    def test_01_11_01_is_instance_of(self):
        klassByte = self.env.find_class("java/lang/Byte")
        method_id = self.env.get_method_id(klassByte, '<init>','(Ljava/lang/String;)V')
        jbyte = self.env.new_object(klassByte, method_id, self.env.new_string_utf("55"))
        klassNumber = self.env.find_class("java/lang/Number")
        self.assertTrue(self.env.is_instance_of(jbyte, klassNumber))
        # <AK> added
        self.assertTrue(javabridge.is_instance_of(jbyte, "java/lang/Number"))
        # </AK>

    def test_01_11_02_isnt_instance_of(self):
        klassByte = self.env.find_class("java/lang/Byte")
        method_id = self.env.get_method_id(klassByte, '<init>','(Ljava/lang/String;)V')
        jbyte = self.env.new_object(klassByte, method_id, self.env.new_string_utf("55"))
        klassString = self.env.find_class("java/lang/String")
        self.assertFalse(self.env.is_instance_of(jbyte, klassString))
        # <AK> added
        self.assertFalse(javabridge.is_instance_of(None, "java/lang/String"))
        # </AK>

    def test_01_12_get_static_field_id(self):
        klass = self.env.find_class("java/lang/Boolean")
        field_id = self.env.get_static_field_id(klass, "FALSE","Ljava/lang/Boolean;")
        self.assertTrue(field_id is not None)

    def test_01_13_get_byte_array_elements(self):
        pass # see test_03_09_call_method_array for test

    def test_01_14_get_object_array_elements(self):
        jstring = self.env.new_string_utf("Hello, world")
        klass = self.env.get_object_class(jstring)
        method_id = self.env.get_method_id(klass, 'split', '(Ljava/lang/String;)[Ljava/lang/String;')
        split = self.env.new_string_utf(", ")
        result = self.env.call_method(jstring, method_id, split)
        result = self.env.get_object_array_elements(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(self.env.get_string_utf(result[0]), "Hello")
        self.assertEqual(self.env.get_string_utf(result[1]), "world")

    @skipIfNumpyNotEnabled()  # <AK> added
    def test_01_15_make_byte_array(self):
        array = np.array([ord(x) for x in "Hello, world"],np.uint8)
        jarray = self.env.make_byte_array(array)
        klass = self.env.find_class("java/lang/String")
        method_id = self.env.get_method_id(klass, '<init>', '([B)V')
        result = self.env.new_object(klass, method_id, jarray)
        self.assertEqual(self.env.get_string_utf(result), "Hello, world")
        # <AK> added
        with self.assertRaisesRegex(MemoryError,
                                    "Failed to allocate byte array of size -1"):
            jarray = self.env.make_byte_array(namedtuple("fake_ndarray", ("shape",))((-1,)))
        # </AK>

    def test_01_16_get_array_length(self):
        jstring = self.env.new_string_utf("Hello, world")
        klass = self.env.get_object_class(jstring)
        method_id = self.env.get_method_id(klass, 'split', '(Ljava/lang/String;)[Ljava/lang/String;')
        split = self.env.new_string_utf(", ")
        result = self.env.call_method(jstring, method_id, split)
        self.assertEqual(self.env.get_array_length(result), 2)

    def test_01_17_make_object_array(self):
        klass = self.env.find_class("java/lang/String")
        jarray = self.env.make_object_array(15, klass)
        length = self.env.get_array_length(jarray)
        self.assertEqual(length, 15)
        # <AK> added
        with self.assertRaisesRegex(MemoryError,
                                    "Failed to allocate object array of size -1"):
            jarray = self.env.make_object_array(-1, klass)
        # </AK>

    def test_01_18_set_object_array_element(self):
        klass = self.env.find_class("java/lang/String")
        jarray = self.env.make_object_array(15, klass)
        for i in range(15):
            v = self.env.new_string_utf(str(i))
            self.env.set_object_array_element(jarray, i, v)
        result = self.env.get_object_array_elements(jarray)
        self.assertEqual(len(result), 15)
        for i, elem in enumerate(result):
            v = self.env.get_string_utf(elem)
            self.assertEqual(str(i), v)

    @skipIfNumpyNotEnabled()  # <AK> added
    def test_01_19_0_make_boolean_array(self):
        np.random.seed(1190)
        array = np.random.uniform(size=105) > .5
        jarray = self.env.make_boolean_array(array)
        result = self.env.get_boolean_array_elements(jarray)
        self.assertTrue(np.all(array == result))
        # <AK> added
        with self.assertRaisesRegex(MemoryError,
                                    "Failed to allocate boolean array of size -1"):
            jarray = self.env.make_boolean_array(namedtuple("fake_ndarray", ("shape",))((-1,)))
        # </AK>

    @skipIfNumpyNotEnabled()  # <AK> added
    def test_01_19_make_short_array(self):
        np.random.seed(119)
        array = (np.random.uniform(size=10) * 65535 - 32768).astype(np.int16)
        array = np.unique(array)
        array.sort()
        jarray = self.env.make_short_array(array)
        klass = self.env.find_class("java/util/Arrays")
        method_id = self.env.get_static_method_id(klass, "binarySearch",
                                                  "([SS)I")
        for i, value in enumerate(array):
            self.assertEqual(i, self.env.call_static_method(
                klass, method_id, jarray, array[i]))
        # <AK> added
        with self.assertRaisesRegex(MemoryError,
                                    "Failed to allocate short array of size -1"):
            jarray = self.env.make_short_array(namedtuple("fake_ndarray", ("shape",))((-1,)))
        # </AK>

    @skipIfNumpyNotEnabled()  # <AK> added
    def test_01_20_make_int_array(self):
        np.random.seed(120)
        array = (np.random.uniform(size=10) * (2.0 ** 32-1) - (2.0 ** 31)).astype(np.int32)
        array = np.unique(array)
        array.sort()
        jarray = self.env.make_int_array(array)
        klass = self.env.find_class("java/util/Arrays")
        method_id = self.env.get_static_method_id(klass, "binarySearch",
                                                  "([II)I")
        for i, value in enumerate(array):
            self.assertEqual(i, self.env.call_static_method(
                klass, method_id, jarray, array[i]))
        # <AK> added
        with self.assertRaisesRegex(MemoryError,
                                    "Failed to allocate int array of size -1"):
            jarray = self.env.make_int_array(namedtuple("fake_ndarray", ("shape",))((-1,)))
        # </AK>

    @skipIfNumpyNotEnabled()  # <AK> added
    def test_01_21_make_long_array(self):
        np.random.seed(121)
        array = (np.random.uniform(size=10) * (2.0 ** 64) - (2.0 ** 63)).astype(np.int64)
        array = np.unique(array)
        array.sort()
        jarray = self.env.make_long_array(array)
        klass = self.env.find_class("java/util/Arrays")
        method_id = self.env.get_static_method_id(klass, "binarySearch",
                                                  "([JJ)I")
        for i, value in enumerate(array):
            self.assertEqual(i, self.env.call_static_method(
                klass, method_id, jarray, array[i]))
        # <AK> added
        with self.assertRaisesRegex(MemoryError,
                                    "Failed to allocate long array of size -1"):
            jarray = self.env.make_long_array(namedtuple("fake_ndarray", ("shape",))((-1,)))
        # </AK>

    @skipIfNumpyNotEnabled()  # <AK> added
    def test_01_22_make_float_array(self):
        np.random.seed(122)
        array = np.random.uniform(size=10).astype(np.float32)
        array = np.unique(array)
        array.sort()
        jarray = self.env.make_float_array(array)
        klass = self.env.find_class("java/util/Arrays")
        method_id = self.env.get_static_method_id(klass, "binarySearch",
                                                  "([FF)I")
        for i, value in enumerate(array):
            self.assertEqual(i, self.env.call_static_method(
                klass, method_id, jarray, array[i]))
        # <AK> added
        with self.assertRaisesRegex(MemoryError,
                                    "Failed to allocate float array of size -1"):
            jarray = self.env.make_float_array(namedtuple("fake_ndarray", ("shape",))((-1,)))
        # </AK>

    @skipIfNumpyNotEnabled()  # <AK> added
    def test_01_23_make_double_array(self):
        np.random.seed(123)
        array = np.random.uniform(size=10).astype(np.float64)
        array = np.unique(array)
        array.sort()
        jarray = self.env.make_double_array(array)
        klass = self.env.find_class("java/util/Arrays")
        method_id = self.env.get_static_method_id(klass, "binarySearch",
                                                  "([DD)I")
        for i, value in enumerate(array):
            self.assertEqual(i, self.env.call_static_method(
                klass, method_id, jarray, array[i]))
        # <AK> added
        with self.assertRaisesRegex(MemoryError,
                                    "Failed to allocate double array of size -1"):
            jarray = self.env.make_double_array(namedtuple("fake_ndarray", ("shape",))((-1,)))
        # </AK>

    @skipIfNumpyNotEnabled()  # <AK> added
    def test_01_24_get_short_array_elements(self):
        np.random.seed(124)
        array = (np.random.uniform(size=10) * 65535 - 32768).astype(np.int16)
        jarray = self.env.make_short_array(array)
        result = self.env.get_short_array_elements(jarray)
        self.assertTrue(np.all(array == result))

    @skipIfNumpyNotEnabled()  # <AK> added
    def test_01_25_get_int_array_elements(self):
        np.random.seed(125)
        array = (np.random.uniform(size=10) * (2.0 ** 32-1) - (2.0 ** 31)).astype(np.int32)
        jarray = self.env.make_int_array(array)
        result = self.env.get_int_array_elements(jarray)
        self.assertTrue(np.all(array == result))

    @skipIfNumpyNotEnabled()  # <AK> added
    def test_01_26_get_long_array_elements(self):
        np.random.seed(126)
        array = (np.random.uniform(size=10) * (2.0 ** 64) - (2.0 ** 63)).astype(np.int64)
        jarray = self.env.make_long_array(array)
        result = self.env.get_long_array_elements(jarray)
        self.assertTrue(np.all(array == result))

    @skipIfNumpyNotEnabled()  # <AK> added
    def test_01_27_get_float_array_elements(self):
        np.random.seed(127)
        array = np.random.uniform(size=10).astype(np.float32)
        jarray = self.env.make_float_array(array)
        result = self.env.get_float_array_elements(jarray)
        self.assertTrue(np.all(array == result))

    @skipIfNumpyNotEnabled()  # <AK> added
    def test_01_28_get_double_array_elements(self):
        np.random.seed(128)
        array = np.random.uniform(size=10).astype(np.float64)
        jarray = self.env.make_double_array(array)
        result = self.env.get_double_array_elements(jarray)
        self.assertTrue(np.all(array == result))

    def test_02_01_exception_did_not_occur(self):
        self.assertTrue(self.env.exception_occurred() is None)

    def test_02_02_exception_occurred(self):
        klass = self.env.find_class("java/lang/String")
        self.env.get_method_id(klass,'copyValueOf','([C)Ljava/lang/String;')
        x = self.env.exception_occurred()
        self.assertTrue(isinstance(x, jb.JB_Object))
        self.env.exception_describe()
        self.env.exception_clear()
        self.assertTrue(self.env.exception_occurred() is None)

    # <AK> added
    def test_03_00_call_method(self):
        klass = self.env.find_class("java/lang/Byte")
        ctor_id = self.env.get_method_id(klass, '<init>','(Ljava/lang/String;)V')
        jbyte = self.env.new_object(klass, ctor_id, self.env.new_string_utf("55"))
        with self.assertRaisesRegex(ValueError,
                                    "Method ID is None - check your method ID call"):
            self.env.call_method(jbyte, None)
        method_id = self.env.get_static_method_id(klass, 'compare','(BB)I')
        with self.assertRaisesRegex(ValueError,
                                    "call_method called with a static method. "
                                    "Use call_static_method instead"):
            self.env.call_method(jbyte, method_id)

    def test_03_01_call_method_char(self):
        jstring = self.env.new_string_utf("Hello, world")
        klass = self.env.get_object_class(jstring)
        method_id = self.env.get_method_id(klass, 'charAt', '(I)C')

        for i, c in enumerate("Hello, world"):
            self.assertEqual(c, self.env.call_method(jstring, method_id, i))

    def test_03_02_call_method_bool(self):
        jstring = self.env.new_string_utf("Hello, world")
        klass = self.env.get_object_class(jstring)
        method_id = self.env.get_method_id(klass, 'equals', '(Ljava/lang/Object;)Z')
        self.assertTrue(self.env.call_method(jstring, method_id, jstring))
        self.assertFalse(self.env.call_method(jstring, method_id, self.env.new_string_utf("Foo")))
        # <AK> added
        with self.assertRaisesRegex(ValueError, "Method ID is None"):
            self.env.call_method(jstring, None, jstring)
        # </AK>

    def test_03_03_call_method_byte(self):
        klass = self.env.find_class("java/lang/Byte")
        method_id = self.env.get_method_id(klass, '<init>','(Ljava/lang/String;)V')
        jbyte = self.env.new_object(klass, method_id, self.env.new_string_utf("55"))
        method_id = self.env.get_method_id(klass, 'byteValue','()B')
        self.assertEqual(self.env.call_method(jbyte, method_id), 55)

    def test_03_04_call_method_short(self):
        klass = self.env.find_class("java/lang/Short")
        method_id = self.env.get_method_id(klass, '<init>','(Ljava/lang/String;)V')
        jshort = self.env.new_object(klass, method_id, self.env.new_string_utf("55"))
        method_id = self.env.get_method_id(klass, 'shortValue','()S')
        self.assertEqual(self.env.call_method(jshort, method_id), 55)

    def test_03_05_call_method_int(self):
        klass = self.env.find_class("java/lang/Integer")
        method_id = self.env.get_method_id(klass, '<init>','(Ljava/lang/String;)V')
        jint = self.env.new_object(klass, method_id, self.env.new_string_utf("65537"))
        method_id = self.env.get_method_id(klass, 'intValue','()I')
        self.assertEqual(self.env.call_method(jint, method_id), 65537)

    def test_03_06_call_method_long(self):
        klass = self.env.find_class("java/lang/Long")
        method_id = self.env.get_method_id(klass, '<init>','(Ljava/lang/String;)V')
        jlong = self.env.new_object(klass, method_id, self.env.new_string_utf("4611686018427387904"))
        method_id = self.env.get_method_id(klass, 'longValue','()J')
        self.assertEqual(self.env.call_method(jlong, method_id), 4611686018427387904)

    def test_03_07_call_method_float(self):
        klass = self.env.find_class("java/lang/Float")
        method_id = self.env.get_method_id(klass, '<init>','(Ljava/lang/String;)V')
        jfloat = self.env.new_object(klass, method_id, self.env.new_string_utf("55.3"))
        method_id = self.env.get_method_id(klass, 'floatValue','()F')
        self.assertAlmostEqual(self.env.call_method(jfloat, method_id), 55.3,5)

    def test_03_08_call_method_double(self):
        klass = self.env.find_class("java/lang/Double")
        method_id = self.env.get_method_id(klass, '<init>','(Ljava/lang/String;)V')
        jdouble = self.env.new_object(klass, method_id, self.env.new_string_utf("-55.64"))
        method_id = self.env.get_method_id(klass, 'doubleValue','()D')
        self.assertAlmostEqual(self.env.call_method(jdouble, method_id), -55.64)

    @skipIfNumpyNotEnabled()  # <AK> added
    def test_03_09_call_method_array(self):
        s = "Hello, world"
        jstring = self.env.new_string_utf(s)
        klass = self.env.get_object_class(jstring)
        method_id = self.env.get_method_id(klass, 'getBytes', '()[B')
        result = self.env.call_method(jstring, method_id)
        self.assertTrue(isinstance(result, jb.JB_Object))
        a = self.env.get_byte_array_elements(result)
        self.assertEqual(np.array(s, "S%d" % len(s)).tostring(), a.tostring())

    def test_03_10_call_method_object(self):
        hello = self.env.new_string_utf("Hello, ")
        world = self.env.new_string_utf("world")
        klass = self.env.get_object_class(hello)
        method_id = self.env.get_method_id(klass, 'concat', '(Ljava/lang/String;)Ljava/lang/String;')
        result = self.env.call_method(hello, method_id, world)
        self.assertEqual("Hello, world", self.env.get_string_utf(result))

    # <AK> added
    def test_04_00_call_static(self):
        klass = self.env.find_class("java/lang/Byte")
        with self.assertRaisesRegex(ValueError,
                                    "Method ID is None - check your method ID call"):
            self.env.call_static_method(klass, None)
        method_id = self.env.get_method_id(klass, 'byteValue','()B')
        with self.assertRaisesRegex(ValueError,
                                    "call_static_method called with an object method. "
                                    "Use call_method instead"):
            self.env.call_static_method(klass, method_id)

    def test_04_01_call_static_bool(self):
        klass = self.env.find_class("java/lang/Boolean")
        method_id = self.env.get_static_method_id(klass, "parseBoolean",'(Ljava/lang/String;)Z')
        self.assertTrue(method_id is not None)
        self.assertFalse(self.env.call_static_method(
            klass, method_id, self.env.new_string_utf("false")))
        self.assertTrue(self.env.call_static_method(
            klass, method_id, self.env.new_string_utf("true")))
        # <AK> added
        with self.assertRaisesRegex(ValueError, "Method ID is None"):
            self.env.call_static_method(klass, None, self.env.new_string_utf("true"))
        # </AK>

    def test_04_02_call_static_byte(self):
        klass = self.env.find_class("java/lang/Byte")
        method_id = self.env.get_static_method_id(klass, "parseByte",'(Ljava/lang/String;)B')
        number = self.env.new_string_utf("55")
        self.assertEqual(self.env.call_static_method(klass, method_id, number), 55)

    def test_04_03_call_static_short(self):
        klass = self.env.find_class("java/lang/Short")
        method_id = self.env.get_static_method_id(klass, "parseShort",'(Ljava/lang/String;)S')
        number = self.env.new_string_utf("-55")
        self.assertEqual(self.env.call_static_method(klass, method_id, number), -55)

    def test_04_04_call_static_int(self):
        klass = self.env.find_class("java/lang/Integer")
        method_id = self.env.get_static_method_id(klass, "parseInt",'(Ljava/lang/String;)I')
        number = self.env.new_string_utf("55")
        self.assertEqual(self.env.call_static_method(klass, method_id, number), 55)

    def test_04_05_call_static_long(self):
        klass = self.env.find_class("java/lang/Long")
        method_id = self.env.get_static_method_id(klass, "parseLong",'(Ljava/lang/String;)J')
        number = self.env.new_string_utf("-55")
        self.assertEqual(self.env.call_static_method(klass, method_id, number), -55)

    def test_04_06_call_static_float(self):
        klass = self.env.find_class("java/lang/Float")
        method_id = self.env.get_static_method_id(klass, "parseFloat",'(Ljava/lang/String;)F')
        number = self.env.new_string_utf("-55.25")
        self.assertAlmostEqual(self.env.call_static_method(klass, method_id, number), -55.25)

    def test_04_07_call_static_double(self):
        klass = self.env.find_class("java/lang/Double")
        method_id = self.env.get_static_method_id(klass, "parseDouble",'(Ljava/lang/String;)D')
        number = self.env.new_string_utf("55.6")
        self.assertAlmostEqual(self.env.call_static_method(klass, method_id, number), 55.6)

    def test_04_08_call_static_object(self):
        klass = self.env.find_class("java/lang/String")
        method_id = self.env.get_static_method_id(klass, "valueOf",'(Z)Ljava/lang/String;')
        result = self.env.call_static_method(klass, method_id, True)
        self.assertEqual(self.env.get_string_utf(result), "true")

    def test_04_09_call_static_char(self):
        klass = self.env.find_class("java/lang/Character")
        method_id = self.env.get_static_method_id(klass, "toLowerCase", "(C)C")
        result = self.env.call_static_method(klass, method_id, "X")
        self.assertEqual(result, "x")

    def test_04_10_call_static_array(self):
        jstring = self.env.new_string_utf("Hello, world")
        klass = self.env.get_object_class(jstring)
        method_id = self.env.get_method_id(klass, "toCharArray","()[C")
        chars = self.env.call_method(jstring, method_id)
        method_id = self.env.get_static_method_id(klass, "copyValueOf","([C)Ljava/lang/String;")
        result = self.env.call_static_method(klass, method_id, chars)
        self.assertEqual(self.env.get_string_utf(result), "Hello, world")

    def test_05_01_get_static_object_field(self):
        klass = self.env.find_class("java/lang/Boolean")
        field_id = self.env.get_static_field_id(klass, "FALSE","Ljava/lang/Boolean;")
        result = self.env.get_static_object_field(klass, field_id)
        method_id = self.env.get_method_id(klass, "booleanValue","()Z")
        self.assertFalse(self.env.call_method(result, method_id))

    def test_05_02_get_static_boolean_field(self):
        pass # can't find any examples

    def test_05_03_get_static_byte_field(self):
        klass = self.env.find_class("java/io/ObjectStreamConstants")
        field_id = self.env.get_static_field_id(klass, "SC_EXTERNALIZABLE","B")
        result = self.env.get_static_byte_field(klass, field_id)
        self.assertEqual(result, 4)

    def test_05_04_get_static_short_field(self):
        klass = self.env.find_class("java/io/ObjectStreamConstants")
        field_id = self.env.get_static_field_id(klass, "STREAM_MAGIC","S")
        result = self.env.get_static_short_field(klass, field_id)
        self.assertEqual(result, -21267) # 0xaced see https://docs.oracle.com/javase/6/docs/platform/serialization/spec/protocol.html

    def test_05_05_get_static_int_field(self):
        klass = self.env.find_class("java/io/ObjectStreamConstants")
        field_id = self.env.get_static_field_id(klass, "PROTOCOL_VERSION_1","I")
        result = self.env.get_static_int_field(klass, field_id)
        self.assertEqual(result, 1)

    def test_05_06_get_static_long_field(self):
        klass = self.env.find_class("java/security/Key")
        field_id = self.env.get_static_field_id(klass, "serialVersionUID", "J")
        result = self.env.get_static_long_field(klass, field_id)
        self.assertEqual(result, 6603384152749567654)

    def test_05_07_get_static_float_field(self):
        klass = self.env.find_class("java/lang/Float")
        field_id = self.env.get_static_field_id(klass, "MAX_VALUE","F")
        result = self.env.get_static_float_field(klass, field_id)
        self.assertAlmostEqual(result, 3.4028234663852886 * 10.0**38)

    def test_05_08_get_static_double_field(self):
        klass = self.env.find_class("java/lang/Math")
        field_id = self.env.get_static_field_id(klass, "PI","D")
        result = self.env.get_static_double_field(klass, field_id)
        self.assertAlmostEqual(result, 3.141592653589793)

    def test_06_01_class_as_object(self):
        klass_map = self.env.find_class("java/util/Map")
        klass_map_obj = klass_map.as_class_object()
        klass_klass = self.env.find_class("java/lang/Class")
        method_getname = self.env.get_method_id(
            klass_klass, "getName", "()Ljava/lang/String;")
        jstring = self.env.call_method(klass_map_obj, method_getname)
        self.assertEqual(self.env.get_string_utf(jstring), "java.util.Map")
