'''test_wrappers.py test JWrapper and JClassWrapper

python-javabridge is licensed under the BSD license.  See the
accompanying file LICENSE for details.

Copyright (c) 2003-2009 Massachusetts Institute of Technology
Copyright (c) 2009-2013 Broad Institute
All rights reserved.

'''
import unittest
import javabridge as J

class TestJWrapper(unittest.TestCase):
    def test_01_01_init(self):
        jobj = J.get_env().new_string(u"Hello, world.")
        obj = J.JWrapper(jobj)
        self.assertEqual(jobj, obj.o)
        # <AK> added
        self.assertEqual(repr(obj),
                         "Instance of java.lang.String: Hello, world.")
        # </AK>

    def test_01_02_call_noargs(self):
        jobj = J.get_env().new_string(u"Hello, world.")
        obj = J.JWrapper(jobj)
        self.assertEqual(obj.toLowerCase(), "hello, world.")

    def test_01_03_call_args(self):
        jobj = J.get_env().new_string(u"Hello, world.")
        obj = J.JWrapper(jobj)
        result = obj.replace("Hello,", "Goodbye cruel")
        self.assertEqual(result, "Goodbye cruel world.")
        # <AK> added
        with self.assertRaisesRegex(TypeError,
                                    "No matching method found for replace"):
            obj.replace()
        # </AK>

    def test_01_04_call_varargs(self):
        sclass = J.JWrapper(J.class_for_name("java.lang.String"));
        for constructor in J.get_env().get_object_array_elements(
            sclass.getConstructors().o):
            wconstructor = J.JWrapper(constructor)
            parameter_types = J.get_env().get_object_array_elements(
                wconstructor.getParameterTypes().o)
            c1 = sclass.getConstructor(*parameter_types)
            self.assertTrue(c1.equals(constructor))

    def test_02_01_get_field(self):
        obj = J.JClassWrapper("org.cellprofiler.javabridge.test.RealRect")(
            1.5, 2.5, 3.5, 4.5)
        self.assertEqual(obj.x, 1.5)
        # <AK> added
        with self.assertRaises(AttributeError):
            field = obj.NoSuchField
        with self.assertRaises(AttributeError):
            field = obj.fs_double
        # </AK>

    def test_02_02_set_field(self):
        obj = J.JClassWrapper("org.cellprofiler.javabridge.test.RealRect")(
            1.5, 2.5, 3.5, 4.5)
        obj.x = 2.5
        self.assertEqual(obj.x, 2.5)
        # <AK> added
        with self.assertRaises(AttributeError):
            field = obj.NoSuchField
        obj.NoSuchField = 456.0
        self.assertEqual(obj.NoSuchField, 456.0)
        with self.assertRaises(AttributeError):
            obj.fs_double = 567.0
        # </AK>

class TestJClassWrapper_Unboxing(unittest.TestCase):
    def setUp(self):
        self.i = J.JClassWrapper('java.lang.Integer')(3)

    def test_01_01_int(self):
        self.assertEqual(int(self.i), 3)

    def test_01_02_float(self):
        self.assertEqual(float(self.i),3.0)

    def test_01_03_str(self):
        self.assertEqual(str(self.i), '3')

class TestJClassWrapper_Collection(unittest.TestCase):
    def setUp(self):
        self.no_seq = J.JClassWrapper('java.lang.Integer')(3)  # <AK> added
        self.a = J.JClassWrapper('java.util.ArrayList')()
        self.assertEqual(len(self.a), 0)
        self.ints = [0,1,2,4,8,16]
        self.assertEqual(len(self.ints), 6)
        for i in self.ints:
            self.a.add(i)

    def test_01_01_get_len(self):
        self.assertEqual(len(self.a), len(self.ints))
        # <AK> added
        with self.assertRaisesRegex(TypeError,
                                    ".+ is not a Collection and does not "
                                    "support __len__"):
            size = len(self.no_seq)
        # </AK>

    def test_01_02_iterate(self):
        for x,y in zip(self.a, self.ints):
            self.assertEqual(x.intValue(), y)
        # <AK> added
        with self.assertRaisesRegex(TypeError,
                                    ".+ is not a Collection and does not "
                                    "support __iter__"):
            for x in self.no_seq: pass
        # </AK>

    def test_01_03_get_index(self):
        for i in range(len(self.a)):
            self.assertEqual(self.a[i].intValue(), self.ints[i])
        # <AK> added
        with self.assertRaisesRegex(TypeError,
                                    ".+ is not a Collection and does not "
                                    "support __getitem__"):
            item = self.no_seq[0]
        # </AK>

    def test_01_04_set_index(self):
        for i in range(len(self.a)):
            self.a[i] = 10
        for i in range(len(self.a)):
            self.assertEqual(self.a[i].intValue(), 10)
        # <AK> added
        with self.assertRaisesRegex(TypeError,
                                    ".+ is not a Collection and does not "
                                    "support __setitem__"):
            self.no_seq[0] = 0
        # </AK>

class TestJClassWrapper(unittest.TestCase):
    def test_01_01_init(self):
        c = J.JClassWrapper("java.lang.Integer")

    def test_01_02_field(self):
        c = J.JClassWrapper("java.lang.Short")
        field = c.MAX_VALUE
        self.assertEqual(field, (1 << 15)-1)
        # <AK> added
        c.MAX_VALUE = 123
        field = c.MAX_VALUE
        self.assertEqual(field, 123)
        with self.assertRaisesRegex(AttributeError,
                                    "Could not find field NoSuchField"):
            field = c.NoSuchField
        c.NoSuchField = 456
        field = c.NoSuchField
        self.assertEqual(field, 456)
        # </AK>

    def test_02_03_static_call(self):
        c = J.JClassWrapper("java.lang.Integer")
        self.assertEqual(c.toString(123), "123")

    def test_02_04_static_call_varargs(self):
        #
        # Test calling a static function with a variable number of
        # arguments.
        #
        c = J.JClassWrapper("java.lang.String")
        self.assertEqual(c.format("Hello, %s.", "world"),
                                  "Hello, world.")
        self.assertEqual(c.format("Goodbye %s %s.", "cruel", "world"),
                         "Goodbye cruel world.")
        # <AK> added
        with self.assertRaisesRegex(TypeError,
                                    "No matching method found for format"):
            c.format()
        with self.assertRaisesRegex(TypeError,
                                    "No matching method found for copyValueOf"):
            c.copyValueOf()
        # </AK>

    def test_02_05_constructor_varargs(self):
        # Regression test of issue #41
        #
        args = ("foo", "bar")
        f = J.JClassWrapper(
            "javax.swing.filechooser.FileNameExtensionFilter")("baz", *args)
        exts = J.get_env().get_object_array_elements(f.getExtensions().o)
        self.assertEqual(args[0], J.to_string(exts[0]))
        self.assertEqual(args[1], J.to_string(exts[1]))
        # <AK> added
        with self.assertRaisesRegex(TypeError,
                                    "No matching constructor found"):
            f = J.JClassWrapper(
                "javax.swing.filechooser.FileNameExtensionFilter")()
        # </AK>

class TestJProxy(unittest.TestCase):
    @unittest.skip("jt.javabridge: crash!!!")
    def test_01_01_init(self):
        def whatever():
            pass
        proxy = J.JProxy('java.lang.Runnable', dict(run=whatever))
        J.JWrapper(proxy.o).run()  # <AK> added

    @unittest.skip("jt.javabridge: crash!!!")
    def test_01_02_runnable(self):
        magic = []
        def whatever(magic=magic):
            magic.append("bus")
        runnable = J.JProxy('java.lang.Runnable',
                            dict(run=whatever))
        J.JWrapper(runnable.o).run()
        self.assertEqual(magic[0], "bus")

    @unittest.skip("jt.javabridge: crash!!!")
    def test_01_03_runnable_class(self):
        class MyProxy(J.JProxy):
            def __init__(self):
                J.JProxy.__init__(self, 'java.lang.Runnable')
                self.esteem = 0

            def run(self):
                self.esteem = "through the roof"

        proxy = MyProxy()
        J.JWrapper(proxy.o).run()
        self.assertEqual(proxy.esteem, "through the roof")

    @unittest.skip("jt.javabridge: crash!!!")
    def test_01_04_args(self):
        my_observable = J.make_instance("java/util/Observable", "()V")
        def update(observable, obj):
            self.assertTrue(J.JWrapper(observable).equals(my_observable))
            self.assertTrue(J.JWrapper(obj).equals("bar"))
        proxy = J.JProxy('java.util.Observer', dict(update=update))
        J.JWrapper(proxy.o).update(my_observable, "bar")

    @unittest.skip("jt.javabridge: crash!!!")
    def test_01_05_return_value(self):
        def call():
            return "foo"
        proxy = J.JProxy('java.util.concurrent.Callable',
                         dict(call = call))
        self.assertEqual(J.JWrapper(proxy.o).call(), "foo")

# <AK> added
class TestImportClass(unittest.TestCase):

    def test_01_01_import_class(self):
        importClass = J.wrappers.importClass
        try:
            del Double
        except:
            pass
        importClass("java.lang.Double")
        del Double
        try:
            del Dummy
        except:
            pass
        importClass("java.lang.Double", "Dummy")
        del Dummy

if __name__=="__main__":
    import javabridge
    javabridge.start_vm()
    try:
        unittest.main()
    finally:
        javabridge.kill_vm()
