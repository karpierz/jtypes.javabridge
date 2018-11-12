# Copyright (c) 2014-2018, Adam Karpierz
# Licensed under the BSD license
# http://opensource.org/licenses/BSD-3-Clause

from __future__ import absolute_import

import sys
import ctypes as ct
import numbers
try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

from ..jvm.lib.compat import PY3, py2compatible
from ..jvm.lib import public
from ..jvm.jhost      import JHost

if PY3: long = int
unicode = type(u"")

from ._jvm    import get_jvm, get_jenv
from ._jclass import JB_Object
from .jutil   import get_class_wrapper
from .jutil   import is_instance_of
from .jutil   import call, static_call
from .jutil   import get_field, get_static_field, set_field, set_static_field
from .jutil   import get_constructor_wrapper, get_method_wrapper
from .jutil   import class_for_name, make_instance
from .jutil   import get_nice_arg
from .jutil   import to_string
from .jutil   import create_jref

from .__config__ import config


@public
@py2compatible
class JWrapper(object):

    '''
    A class that wraps a Java object

    JWrapper uses Java reflection to find a Java object's methods and fields.
    You can then use dot notation to call the methods and get references
    to the fields. If methods return Java objects, these will also be
    wrapped, so you can use the wrapper to do almost anything.

    When a class has overloaded methods with the same name, JWrapper will
    try to pick the one that matches the types of the arguments.

    To access static methods and fields, use JClassWrapper.

    `self.o` is the JB_Object wrapped by the wrapper. You
    can use `self.o` as an argument for the collection wrappers or anywhere
    else you might use a JB_Object.

    Usage:

        >>> a = JWrapper(javabridge.make_instance("java/util/ArrayList", "()V"))
        >>> a.add("Hello")
        >>> a.add("World")
        >>> a.size()
        2
        >>> a.get(0).toLowerCase()
        hello

    '''

    def __init__(self, o):

        '''
        Initialize the JWrapper with a Java object

        :param o: a Java object (class = JB_Object)

        '''
        jenv = get_jenv()

        self.o = o
        self.class_wrapper = get_class_wrapper(o)
        STATIC   = get_static_field("java/lang/reflect/Modifier", "STATIC", "I")
        jmethods = jenv.get_object_array_elements(self.class_wrapper.getMethods())
        methods = {}
        for jmethod in jmethods:
            if (call(jmethod, "getModifiers", "()I") & STATIC) == STATIC:
                continue
            method = get_method_wrapper(jmethod)
            method_name = method.getName()
            if method_name not in methods:
                methods[method_name] = []
                fn = lambda name=method_name: lambda *args: self.__call(name, *args)
                fn = fn()
                fn.__doc__ = to_string(jmethod)
                setattr(self, method_name, fn)
            else:
                fn = getattr(self, method_name)
                fn.__doc__ += "\n"
                fn.__doc__ += to_string(jmethod)
            methods[method_name].append(method)
        jfields = jenv.get_object_array_elements(self.class_wrapper.getFields(self))
        field_class = jenv.find_class("java/lang/reflect/Field")
        method_id = jenv.get_method_id(field_class, "getName", "()Ljava/lang/String;")
        self.field_names = [jenv.get_string_utf(jenv.call_method(o, method_id)) for o in jfields]
        self.methods = methods

    def __getattr__(self, name):

        if (name in ("o", "class_wrapper", "methods", "field_names") or
            not hasattr(self, "methods") or not hasattr(self, "field_names")):
            raise AttributeError()
        if name not in self.field_names:
            raise AttributeError()
        try:
            jfield = self.class_wrapper.getField(name)
        except:
            raise AttributeError()
        else:
            STATIC = get_static_field("java/lang/reflect/Modifier", "STATIC", "I")
            if (call(jfield, "getModifiers", "()I") & STATIC) == STATIC:
                raise AttributeError()

            jvm = get_jvm()

            klass = call(jfield, "getType", "()Ljava/lang/Class;")
            jcls = jvm.JClass(None, klass.o, borrowed=True)
            result = get_field(self.o, name, str(jcls.getSignature()))
            return JWrapper(result) if isinstance(result, JB_Object) else result

    def __setattr__(self, name, value):

        if (name in ("o","class_wrapper","methods","field_names") or
            not hasattr(self, "methods")):
            super(JWrapper, self).__setattr__(name, value)
            return
        try:
            jfield = self.class_wrapper.getField(name)
        except:
            super(JWrapper, self).__setattr__(name, value)
        else:
            STATIC = get_static_field("java/lang/reflect/Modifier", "STATIC", "I")
            if (call(jfield, "getModifiers", "()I") & STATIC) == STATIC:
                raise AttributeError()

            jvm = get_jvm()

            klass = call(jfield, "getType", "()Ljava/lang/Class;")
            jcls = jvm.JClass(None, klass.o, borrowed=True)
            set_field(self.o, name, str(jcls.getSignature()), value)

    def __call(self, method_name, *args):

        '''
        Call the appropriate overloaded method with the given name

        :param method_name: the name of the method to call
        :param *args: the arguments to the method, which are used to
                      disambiguate between similarly named methods
        '''
        arg_count = len(args)

        jenv = get_jenv()

        last_e = None
        for method in self.methods[method_name]:
            params = jenv.get_object_array_elements(method.getParameterTypes())

            par_count  = len(params)
            is_varargs = call(method.o, "isVarArgs", "()Z")

            if is_varargs:
                perm_count = par_count - 1
                if arg_count < perm_count:
                    continue
                args1 = args[:perm_count] + (args[perm_count:],)
            else:
                if arg_count != par_count:
                    continue
                args1 = args

            try:
                cargs = tuple(cast(o, klass) for o, klass in zip(args1, params))
            except:
                last_e = sys.exc_info()[1]
            else:
                rtype = call(method.o, "getReturnType", "()Ljava/lang/Class;")
                break
        else:
            raise TypeError("No matching method found for {}".format(method_name))

        args_sig = "".join(sig(param) for param in params)
        ret_sig  = sig(rtype)
        method_sig = "({}){}".format(args_sig, ret_sig)
        result = call(self.o, method_name, method_sig, *cargs)
        return JWrapper(result) if isinstance(result, JB_Object) else result

    def __str__(self):

        return to_string(self.o)

    def __repr__(self):

        jcls = self.o._jobject.getClass()
        return "Instance of {}: {}".format(jcls.getName(), to_string(self.o))

    def __int__(self):

        return self.intValue()

    def __float__(self):

        return self.floatValue()

    def __len__(self):

        if not is_instance_of(self.o, "java/util/Collection"):
            raise TypeError("{} is not a Collection and does not support __len__".format(self))

        return self.size()

    def __getitem__(self, idx):

        if not is_instance_of(self.o, "java/util/Collection"):
            raise TypeError("{} is not a Collection and does not support __getitem__".format(self))

        return self.get(idx)

    def __setitem__(self, idx, value):

        if not is_instance_of(self.o, "java/util/Collection"):
            raise TypeError("{} is not a Collection and does not support __setitem__".format(self))

        return self.set(idx, value)

    @py2compatible
    class Iterator(object):

        def __init__(self, obj):

            self.obj = obj
            self.idx = 0

        def __next__(self):

            if self.idx == len(self.obj):
                raise StopIteration
            self.idx += 1
            return self.obj[self.idx - 1]

    def __iter__(self):

        if not is_instance_of(self.o, "java/util/Collection"):
            raise TypeError("{} is not a Collection and does not support __iter__".format(self))

        return self.Iterator(self)


@public
class JClassWrapper(object):

    '''Wrapper for a class

    JWrapper uses Java reflection to find a Java object's methods and fields.
    You can then use dot notation to call the static methods and get references
    to the static fields. If methods return Java objects, these will also be
    wrapped, so you can use the wrapper to do almost anything.

    When a class has overloaded methods with the same name, JWrapper will
    try to pick the one that matches the types of the arguments.

    >>> Integer = JClassWrapper("java.lang.Integer")
    >>> Integer.MAX_VALUE
    2147483647
    '''

    def __init__(self, class_name):

        '''
        Initialize to wrap a class name

        :param class_name: name of class in dotted form, e.g. java.lang.Integer

        '''
        jenv = get_jenv()

        self.cname = class_name.replace(".", "/")
        self.klass = get_class_wrapper(class_for_name(class_name), True)
        self.static_methods = {}
        STATIC   = get_static_field("java/lang/reflect/Modifier", "STATIC", "I")
        jmethods = jenv.get_object_array_elements(self.klass.getMethods())
        methods = {}
        for jmethod in jmethods:
            if (call(jmethod, "getModifiers", "()I") & STATIC) != STATIC:
                continue
            method = get_method_wrapper(jmethod)
            name = method.getName()
            if name not in methods:
                methods[name] = []
                fn = lambda name=name: lambda *args: self.__call_static(name, *args)
                fn = fn()
                fn.__doc__ = to_string(jmethod)
                setattr(self, name, fn)
            else:
                fn = getattr(self, name)
                fn.__doc__ += "\n"
                fn.__doc__ += to_string(jmethod)
            methods[name].append(method)
        jfields = jenv.get_object_array_elements(self.klass.getFields(self))
        field_class = jenv.find_class("java/lang/reflect/Field")
        method_id = jenv.get_method_id(field_class, "getName", "()Ljava/lang/String;")
        self.field_names = [jenv.get_string_utf(jenv.call_method(o, method_id)) for o in jfields]
        self.methods = methods

    def __getattr__(self, name):

        if (name in ("klass", "cname", "static_methods", "methods", "field_names") or
            not hasattr(self, "methods") or not hasattr(self, "field_names")):
            raise AttributeError()
        if name not in self.field_names:
            raise AttributeError("Cound not find field {}".format(name))
        try:
            jfield = self.klass.getField(name)
        except:
            raise AttributeError("Could not find field {}".format(name))
        else:
            STATIC = get_static_field("java/lang/reflect/Modifier", "STATIC", "I")
            if (call(jfield, "getModifiers", "()I") & STATIC) != STATIC:
                raise AttributeError("Field {} is not static".format(name))

            jvm = get_jvm()

            klass = call(jfield, "getType", "()Ljava/lang/Class;")
            jcls = jvm.JClass(None, klass.o, borrowed=True)
            result = get_static_field(self.cname, name, str(jcls.getSignature()))
            return JWrapper(result) if isinstance(result, JB_Object) else result

    def __setattr__(self, name, value):

        if (name in ("klass", "cname", "static_methods", "methods", "field_names") or
            not hasattr(self, "methods")):
            super(JClassWrapper, self).__setattr__(name, value)
            return
        try:
            jfield = self.klass.getField(name)
        except:
            super(JClassWrapper, self).__setattr__(name, value)
        else:
            STATIC = get_static_field("java/lang/reflect/Modifier", "STATIC", "I")
            if (call(jfield, "getModifiers", "()I") & STATIC) != STATIC:
                raise AttributeError()

            jvm = get_jvm()

            klass = call(jfield, "getType", "()Ljava/lang/Class;")
            jcls = jvm.JClass(None, klass.o, borrowed=True)
            set_static_field(self.cname, name, str(jcls.getSignature()), value)

    def __call_static(self, method_name, *args):

        '''
        Call the appropriate overloaded method with the given name

        :param method_name: the name of the method to call
        :param *args: the arguments to the method, which are used to
                      disambiguate between similarly named methods
        '''
        arg_count = len(args)

        jenv = get_jenv()

        last_e = None
        for method in self.methods[method_name]:
            params = jenv.get_object_array_elements(method.getParameterTypes())

            par_count  = len(params)
            is_varargs = call(method.o, "isVarArgs", "()Z")

            if is_varargs:
                perm_count = par_count - 1
                if arg_count < perm_count:
                    continue
                args1 = args[:perm_count] + (args[perm_count:],)
            else:
                if arg_count != par_count:
                    continue
                args1 = args

            try:
                cargs = tuple(cast(o, klass) for o, klass in zip(args1, params))
            except:
                last_e = sys.exc_info()[1]
            else:
                rtype = call(method.o, "getReturnType", "()Ljava/lang/Class;")
                break
        else:
            raise TypeError("No matching method found for {}".format(method_name))

        args_sig = "".join(sig(param) for param in params)
        ret_sig  = sig(rtype)
        method_sig = "({}){}".format(args_sig, ret_sig)
        result = static_call(self.cname, method_name, method_sig, *cargs)
        return JWrapper(result) if isinstance(result, JB_Object) else result

    def __call__(self, *args):

        '''Constructors'''

        arg_count = len(args)

        jenv = get_jenv()

        jconstructors = jenv.get_object_array_elements(self.klass.getConstructors())
        for jconstructor in jconstructors:
            constructor = get_constructor_wrapper(jconstructor)
            params = jenv.get_object_array_elements(constructor.getParameterTypes())

            par_count  = len(params)
            is_varargs = call(constructor.o, "isVarArgs", "()Z")

            if is_varargs:
                perm_count = par_count - 1
                if arg_count < perm_count:
                    continue
                args1 = args[:perm_count] + (args[perm_count:],)
            else:
                if arg_count != par_count:
                    continue
                args1 = args

            try:
                cargs = tuple(cast(o, klass) for o, klass in zip(args1, params))
            except:
                last_e = sys.exc_info()[1]
            else:
                break
        else:
            raise TypeError("No matching constructor found")

        args_sig = "".join(sig(param) for param in params)
        ret_sig  = "V"
        method_sig = "({}){}".format(args_sig, ret_sig)
        result = make_instance(self.cname, method_sig, *cargs)
        return JWrapper(result)


@public
class JProxy(object):

    """
    A wrapper around java.lang.reflect.Proxy

    The wrapper takes a dictionary of either method name or a
    `java.lang.reflect.Method` instance to a callable that handles
    the method. You can also subclass JProxy and define methods
    with the same names as the Java methods and they will be called.

    An example:

        >>> import javabridge
        >>> import sys
        >>> runnable = javabridge.JProxy(
                'java.lang.Runnable',
                dict(run=lambda:sys.stderr.write("Hello, world.\\n"))))
        >>> javabridge.JWrapper(runnable.o).run()

    Another example:

        >>> import javabridge
        >>> import sys
        >>> class MyRunnable(javabridge.JProxy):
                def __init__(self):
                    javabridge.JProxy.__init__(self, 'java.lang.Runnable')
                def run(self):
                    sys.stderr.write("Hello, world.\\n")
        >>> proxy = MyRunnable()
        >>> javabridge.JWrapper(runnable.o).run()

    """

    def __init__(self, base_class_name, d=None):

        """
        Initialize the proxy with the interface name and methods

        :param base_class_name: the class name of the interface to implement
                                in dotted form (e.g. java.lang.Runnable)
        :param d: an optional dictionary of method name to implementation

        """
        jvm  = get_jvm()
        jenv = get_jenv()

        self.ref_id, self.ref = create_jref(self)
        self.__d = d or {}
        jinterf = class_for_name(base_class_name)
        jinterf = jvm.JClass(jenv.env, jinterf.o)
        jproxy  = jvm.JProxy((jinterf,))
        #cloader = jinterf.getClassLoader()
        jobj = jproxy.newProxy(self)
        JHost.decRef(self)
        self.o = jenv._make_jb_object(jobj)

    def __call__(self, method, *args):

        method_name  = str(method.getName())
        return_class = method.getReturnType()
        fun  = self.__d.get(method_name) or getattr(self, method_name)
        result = fun(*args)
        return cast(result, return_class)


def importClass(class_name, import_name=None):

    """
    Import a wrapped class into the global context

    :param class_name: a dotted class name such as java.lang.String
    :param import_name: if defined, use this name instead of the class's name

    """
    if import_name is None:
        import_name = class_name.rsplit(".", 1)[-1]

    frame = sys._getframe(1)
    frame.f_locals[import_name] = JClassWrapper(class_name)
    ct.pythonapi.PyFrame_LocalsToFast(ct.py_object(frame), ct.c_int(0))


def sig(klass):

    """Return the JNI signature for a class"""

    jvm = get_jvm()

    jcls = jvm.JClass(None, klass.o, borrowed=True)
    return str(jcls.getSignature())


def cast(o, klass):

    """
    Cast the given object to the given class

    :param o: either a Python object or Java object to be cast
    :param klass: a java.lang.Class indicating the target class

    raises a TypeError if the object can't be cast.

    """
    jvm = get_jvm()

    jclass = klass if isinstance(klass, jvm.JClass) else jvm.JClass(None, klass.o, borrowed=True)
    if jclass.getName() == "void":
        return None
    elif o is None:
        if jclass.isPrimitive():
            raise TypeError("Can't cast None to a primitive type")
        return None
    elif isinstance(o, JB_Object):
        jobject = o._jobject
        if not jclass.isInstance(jobject):
            raise TypeError("Object of class {} cannot be cast to {}".format(
                            jobject.getClass().getCanonicalName(), jclass.getCanonicalName()))
        return o
    elif hasattr(o, "o"):
        return cast(o.o, klass)
    elif not (np.isscalar(o) if config.getboolean("NUMPY_ENABLED", True) and np
              else (type(o) in (bool, int, long, float, complex,
                                bytes, unicode, memoryview if PY3 else buffer)
                    or isinstance(o, numbers.Number))):
        component_type = jclass.getComponentType()
        if component_type is None:
            raise TypeError("Argument must not be a sequence")
        if len(o) > 0:
            # Test if an element can be cast to the array type
            cast(o[0], component_type)
        csig = str(jclass.getSignature())
        return get_nice_arg(o, csig)
    csig = str(jclass.getSignature())
    if jclass.isPrimitive() or csig in ("Ljava/lang/String;",
                                        "Ljava/lang/CharSequence;",
                                        "Ljava/lang/Object;"):
        if csig == "Ljava/lang/CharSequence;":
            csig = "Ljava/lang/String;"
        elif csig == "C" and isinstance(o, (str, unicode)) and len(o) != 1:
            raise TypeError("Failed to convert string of length {} to char".format(len(o)))
        return get_nice_arg(o, csig)
    else:
        raise TypeError("Failed to convert argument to {}".format(csig))


all = [JWrapper, JClassWrapper]
