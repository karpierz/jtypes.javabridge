# Copyright (c) 2014-2018, Adam Karpierz
# Licensed under the BSD license
# http://opensource.org/licenses/BSD-3-Clause

from __future__ import absolute_import

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None
unicode = type(u"")

from ..jvm.lib import annotate, Union, Optional
from ..jvm.lib import public
from ..        import jni

from ..jvm.jframe  import JFrame
from ..jvm.jstring import JString

from ._jvm    import get_jvm
from ._jclass import JB_Class, JB_Object, _JB_MethodID, _JB_FieldID

# cdef extern from "numpy/arrayobject.h":
#     ctypedef class numpy.ndarray [object PyArrayObject]:
#         cdef char *data
#         cdef Py_intptr_t *dimensions
#         cdef Py_intptr_t *strides


@public
class JB_Env(object):

    """
    Represents the Java VM and the Java execution environment.

    """

    def __new__(cls):

        self = super(JB_Env, cls).__new__(cls)
        self.env = None  # jni.JNIEnv
        return self

    def __repr__(self):

        return "<JB_Env at {:#x}>".format(id(self.env))

    @annotate(jenv=jni.JNIEnv)
    def set_env(self, jenv):

        self.env = jenv
        if not self.env:
            raise ValueError("set_env called with non-environment capsule")

    @annotate(jbobject=JB_Object)
    def dealloc_jobject(self, jbobject):

        jobject = jbobject._jobject
        if jbobject.o:
            self.env.DeleteGlobalRef(jobject.handle)
        if jbobject:
            jobject._borrowed = True

    def get_version(self):

        version = self.env.GetVersion()
        return (int(version // 65536), version % 65536)

    @annotate(JB_Class, name=Union[str, unicode])
    def find_class(self, name):

        jvm  = get_jvm()
        jenv = self.env

        name = name.encode("utf-8").translate(jvm.JClass.name_trans).decode("utf-8")
        jclass = jvm.JClass.forName(name)

        jbclass = JB_Class()
        jbclass._jclass = jvm.JClass(jenv, jclass.handle)
        return jbclass

    @annotate(JB_Class, jbobject=JB_Object)
    def get_object_class(self, jbobject):

        jvm  = get_jvm()
        jenv = self.env

        jobject = jbobject._jobject
        jclass  = jobject.getClass()

        jbclass = JB_Class()
        jbclass._jclass = jvm.JClass(jenv, jclass.handle)
        return jbclass

    @annotate(bool, jbobject=JB_Object, jbclass=JB_Class)
    def is_instance_of(self, jbobject, jbclass):

        jobject = jbobject._jobject
        jclass  = jbclass._jclass
        return jclass.isInstance(jobject)

    def exception_occurred(self):

        jvm  = get_jvm()
        jenv = self.env

        with JFrame(jenv, 1):
            jth = jni.Throwable.last.getCause() if jni.Throwable.last else jni.obj(jni.jthrowable)
            jth = jvm.JObject(jenv, jth) if jth else None
        return self._make_jb_object(jth) if jth else None

    def exception_describe(self):

        self.env.ExceptionDescribe()

    def exception_clear(self):

        self.env.ExceptionClear()

    @annotate(_JB_MethodID, jbclass=JB_Class, name=Union[str, unicode], sig=Union[str, unicode])
    def get_method_id(self, jbclass, name, sig):

        if jbclass is None:
            raise ValueError("Class = None on call to get_method_id")

        jcls = jbclass.c

        try:
            id = self.env.GetMethodID(jcls, name.encode("utf-8"), sig.encode("utf-8"))
        except jni.Throwable as exc:
            return None
        return _JB_MethodID(id, sig, False)

    @annotate(_JB_MethodID, jbclass=JB_Class, name=Union[str, unicode], sig=Union[str, unicode])
    def get_static_method_id(self, jbclass, name, sig):

        jcls = jbclass.c

        try:
            id = self.env.GetStaticMethodID(jcls, name.encode("utf-8"), sig.encode("utf-8"))
        except jni.Throwable as exc:
            return None
        return _JB_MethodID(id, sig, True)

    @annotate(_JB_MethodID, method=JB_Object, sig=bytes, is_static=bool)
    def from_reflected_method(self, method, sig, is_static):

        try:
            id = self.env.FromReflectedMethod(method.o)
        except jni.Throwable as exc:
            return None
        if not id:
            return None
        return _JB_MethodID(id, sig, is_static)

    @annotate(jobject=JB_Object, meth=_JB_MethodID)
    def call_method(self, jobject, meth, *args):

        if meth is None:
            raise ValueError("Method ID is None - check your method ID call")

        if meth.is_static:
            raise ValueError("call_method called with a static method. "
                             "Use call_static_method instead")

        if meth.sig[0] != '(' or ')' not in meth.sig:
            raise ValueError("Bad function signature: {}".format(meth.sig))

        arg_end = meth.sig.find(')')
        arg_sig = meth.sig[1:arg_end]
        ret_sig = meth.sig[arg_end+1:]
        jargs = JB_Env._make_arguments(arg_sig, args)

        jenv = self.env
        this = jobject._jobject

        #
        # Dispatch based on return code at end of sig
        #

        if ret_sig == 'V':

            try:
                jenv.CallVoidMethod(this.handle, meth.id, jargs.arguments)
                return None
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'Z':

            try:
                return jenv.CallBooleanMethod(this.handle, meth.id, jargs.arguments)
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'B':

            try:
                return jenv.CallByteMethod(this.handle, meth.id, jargs.arguments)
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'C':

            try:
                return jenv.CallCharMethod(this.handle, meth.id, jargs.arguments)
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'S':

            try:
                return jenv.CallShortMethod(this.handle, meth.id, jargs.arguments)
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'I':

            try:
                return jenv.CallIntMethod(this.handle, meth.id, jargs.arguments)
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'J':

            try:
                return jenv.CallLongMethod(this.handle, meth.id, jargs.arguments)
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'F':

            try:
                return jenv.CallFloatMethod(this.handle, meth.id, jargs.arguments)
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'D':

            try:
                return jenv.CallDoubleMethod(this.handle, meth.id, jargs.arguments)
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif (ret_sig[0] == 'L' or
              ret_sig[0] == '['):

            jvm = get_jvm()

            try:
                with JFrame(jenv, 1):
                    jobj = jenv.CallObjectMethod(this.handle, meth.id, jargs.arguments)
                    jobj = jvm.JObject(jenv, jobj) if jobj else None
                return self._make_jb_object(jobj) if jobj else None
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        else:
            raise ValueError("Unhandled return type. Signature = {}".format(meth.sig))

    @annotate(jbclass=JB_Class, meth=_JB_MethodID)
    def call_static_method(self, jbclass, meth, *args):

        if meth is None:
            raise ValueError("Method ID is None - check your method ID call")

        if not meth.is_static:
            raise ValueError("call_static_method called with an object method. "
                             "Use call_method instead")

        if meth.sig[0] != '(' or ')' not in meth.sig:
            raise ValueError("Bad function signature: {}".format(meth.sig))

        arg_end = meth.sig.find(')')
        arg_sig = meth.sig[1:arg_end]
        ret_sig = meth.sig[arg_end+1:]
        jargs = JB_Env._make_arguments(arg_sig, args)

        jenv = self.env
        jcls = jbclass.c

        #
        # Dispatch based on return code at end of sig
        #

        if ret_sig == 'V':

            try:
                jenv.CallStaticVoidMethod(jcls, meth.id, jargs.arguments)  # !!! bylo bez Static, nie bylo nogil !!!
                return None
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'Z':

            try:
                return jenv.CallStaticBooleanMethod(jcls, meth.id, jargs.arguments)
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'B':

            try:
                return jenv.CallStaticByteMethod(jcls, meth.id, jargs.arguments)
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'C':

            try:
                return jenv.CallStaticCharMethod(jcls, meth.id, jargs.arguments)
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'S':

            try:
                return jenv.CallStaticShortMethod(jcls, meth.id, jargs.arguments)  # !!! bylo bez Static !!!
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'I':

            try:
                return jenv.CallStaticIntMethod(jcls, meth.id, jargs.arguments)  # !!! bylo bez Static !!!
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'J':

            try:
                return jenv.CallStaticLongMethod(jcls, meth.id, jargs.arguments)  # !!! bylo bez Static !!!
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'F':

            try:
                return jenv.CallStaticFloatMethod(jcls, meth.id, jargs.arguments)  # !!! bylo bez Static !!!
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif ret_sig == 'D':

            try:
                return jenv.CallStaticDoubleMethod(jcls, meth.id, jargs.arguments)  # !!! bylo bez Static !!!
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        elif (ret_sig[0] == 'L' or
              ret_sig[0] == '['):

            jvm = get_jvm()

            try:
                with JFrame(jenv, 1):
                    jobj = jenv.CallStaticObjectMethod(jcls, meth.id, jargs.arguments)  # !!! bylo bez Static !!!
                    jobj = jvm.JObject(jenv, jobj) if jobj else None
                return self._make_jb_object(jobj) if jobj else None
            except jni.Throwable as exc:
                raise get_jvm().JavaException(exc)

        else:
            raise ValueError("Unhandled return type. Signature = {}".format(meth.sig))

    @annotate(_JB_FieldID, jbclass=JB_Class, name=Union[str, unicode], sig=Union[str, unicode])
    def get_field_id(self, jbclass, name, sig):

        jcls = jbclass.c

        try:
            id = self.env.GetFieldID(jcls, name.encode("utf-8"), sig.encode("utf-8"))
        except jni.Throwable as exc:
            raise get_jvm().JavaException(exc)
        return _JB_FieldID(id, sig, False)

    @annotate(_JB_FieldID, jbclass=JB_Class, name=Union[str, unicode], sig=Union[str, unicode])
    def get_static_field_id(self, jbclass, name, sig):

        jcls = jbclass.c

        try:
            id = self.env.GetStaticFieldID(jcls, name.encode("utf-8"), sig.encode("utf-8"))
        except jni.Throwable as exc:
            raise get_jvm().JavaException(exc)
        return _JB_FieldID(id, sig, True)  # !!! bylo False, chyba blad !!!

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def get_boolean_field(self, jbobject, field):

        jenv = self.env
        this = jbobject._jobject
        return jenv.GetBooleanField(this.handle, field.id)

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def get_byte_field(self, jbobject, field):

        jenv = self.env
        this = jbobject._jobject
        return jenv.GetByteField(this.handle, field.id)

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def get_char_field(self, jbobject, field):

        jenv = self.env
        this = jbobject._jobject
        return jenv.GetCharField(this.handle, field.id)

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def get_short_field(self, jbobject, field):

        jenv = self.env
        this = jbobject._jobject
        return jenv.GetShortField(this.handle, field.id)

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def get_int_field(self, jbobject, field):

        jenv = self.env
        this = jbobject._jobject
        return jenv.GetIntField(this.handle, field.id)

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def get_long_field(self, jbobject, field):

        jenv = self.env
        this = jbobject._jobject
        return jenv.GetLongField(this.handle, field.id)

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def get_float_field(self, jbobject, field):

        jenv = self.env
        this = jbobject._jobject
        return jenv.GetFloatField(this.handle, field.id)

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def get_double_field(self, jbobject, field):

        jenv = self.env
        this = jbobject._jobject
        return jenv.GetDoubleField(this.handle, field.id)

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def get_object_field(self, jbobject, field):

        jvm  = get_jvm()
        jenv = self.env

        this = jbobject._jobject
        with JFrame(jenv, 1):
            jobj = jenv.GetObjectField(this.handle, field.id)
            jobj = jvm.JObject(jenv, jobj) if jobj else None
        return self._make_jb_object(jobj) if jobj else None

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def set_boolean_field(self, jbobject, field, value):

        jenv = self.env
        this = jbobject._jobject
        jenv.SetBooleanField(this.handle, field.id, value)

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def set_byte_field(self, jbobject, field, value):

        jenv = self.env
        this = jbobject._jobject
        jenv.SetByteField(this.handle, field.id, value)

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def set_char_field(self, jbobject, field, value):

        assert len(str(value)) > 0
        jenv = self.env
        this = jbobject._jobject
        jenv.SetCharField(this.handle, field.id, value)

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def set_short_field(self, jbobject, field, value):

        jenv = self.env
        this = jbobject._jobject
        jenv.SetShortField(this.handle, field.id, value)

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def set_int_field(self, jbobject, field, value):

        jenv = self.env
        this = jbobject._jobject
        jenv.SetIntField(this.handle, field.id, value)

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def set_long_field(self, jbobject, field, value):

        jenv = self.env
        this = jbobject._jobject
        jenv.SetLongField(this.handle, field.id, value)

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def set_float_field(self, jbobject, field, value):

        jenv = self.env
        this = jbobject._jobject
        jenv.SetFloatField(this.handle, field.id, value)

    @annotate(jbobject=JB_Object, field=_JB_FieldID)
    def set_double_field(self, jbobject, field, value):

        jenv = self.env
        this = jbobject._jobject
        jenv.SetDoubleField(this.handle, field.id, value)

    @annotate(jbobject=JB_Object, field=_JB_FieldID, value=Optional[JB_Object])
    def set_object_field(self, jbobject, field, value):

        jenv = self.env
        this = jbobject._jobject
        jenv.SetObjectField(this.handle, field.id, value.o if value is not None else None)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def get_static_boolean_field(self, jbclass, field):

        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticBooleanField(jcls, field.id)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def get_static_byte_field(self, jbclass, field):

        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticByteField(jcls, field.id)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def get_static_char_field(self, jbclass, field):

        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticCharField(jcls, field.id)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def get_static_short_field(self, jbclass, field):

        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticShortField(jcls, field.id)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def get_static_int_field(self, jbclass, field):

        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticIntField(jcls, field.id)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def get_static_long_field(self, jbclass, field):

        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticLongField(jcls, field.id)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def get_static_float_field(self, jbclass, field):

        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticFloatField(jcls, field.id)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def get_static_double_field(self, jbclass, field):

        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticDoubleField(jcls, field.id)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def get_static_object_field(self, jbclass, field):

        jvm  = get_jvm()
        jenv = self.env

        jcls = jbclass.c
        with JFrame(jenv, 1):
            jobj = jenv.GetStaticObjectField(jcls, field.id)
            jobj = jvm.JObject(jenv, jobj) if jobj else None
        return self._make_jb_object(jobj) if jobj else None

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def set_static_boolean_field(self, jbclass, field, value):

        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticBooleanField(jcls, field.id, value)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def set_static_byte_field(self, jbclass, field, value):

        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticByteField(jcls, field.id, value)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def set_static_char_field(self, jbclass, field, value):

        assert len(str(value)) > 0
        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticCharField(jcls, field.id, value)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def set_static_short_field(self, jbclass, field, value):

        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticShortField(jcls, field.id, value)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def set_static_int_field(self, jbclass, field, value):

        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticIntField(jcls, field.id, value)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def set_static_long_field(self, jbclass, field, value):

        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticLongField(jcls, field.id, value)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def set_static_float_field(self, jbclass, field, value):

        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticFloatField(jcls, field.id, value)

    @annotate(jbclass=JB_Class, field=_JB_FieldID)
    def set_static_double_field(self, jbclass, field, value):

        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticDoubleField(jcls, field.id, value)

    @annotate(jbclass=JB_Class, field=_JB_FieldID, value=Optional[JB_Object])
    def set_static_object_field(self, jbclass, field, value):

        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticObjectField(jcls, field.id, value.o if value is not None else None)

    @annotate(jclass=JB_Class, meth=_JB_MethodID)
    def new_object(self, jclass, meth, *args):

        if meth.sig[0] != '(' or ')' not in meth.sig:
            raise ValueError("Bad function signature: {}".format(meth.sig))

        arg_end = meth.sig.find(')')
        arg_sig = meth.sig[1:arg_end]
        jargs = JB_Env._make_arguments(arg_sig, args)

        jvm  = get_jvm()
        jenv = self.env

        try:
            jcls = jclass.c
            with JFrame(jenv, 1):
                jobj = jenv.NewObject(jcls, meth.id, jargs.arguments)
                jobj = jvm.JObject(jenv, jobj) if jobj else None
            return self._make_jb_object(jobj) if jobj else None
        except jni.Throwable as exc:
            raise get_jvm().JavaException(exc)

    @annotate(u=unicode)
    def new_string(self, u):

        jvm  = get_jvm()
        jenv = self.env

        with JFrame(jenv, 1):
            try:
                import ctypes as ct

                jchars = u.encode("utf-16")[jni.sizeof(jni.jchar):]  # skip byte-order mark
                size = len(jchars) // jni.sizeof(jni.jchar) # - 1
                jbuf = jni.cast(ct.c_char_p(jchars), jni.POINTER(jni.jchar))
                jstr = jenv.NewString(jbuf, size)
            except jni.Throwable:
                raise MemoryError("Failed to allocate string")
            if not jstr:
                raise MemoryError("Failed to allocate string")
            jstr = jvm.JObject(jenv, jstr)
        return self._make_jb_object(jstr)

    @annotate(s=Union[str, unicode])
    def new_string_utf(self, s):

        jvm  = get_jvm()
        jenv = self.env

        with JFrame(jenv, 1):
            try:
                jstr = jenv.NewStringUTF(s.encode("utf-8"))
            except jni.Throwable:
                raise MemoryError("Failed to allocate string")
            if not jstr:
                raise MemoryError("Failed to allocate string")
            jstr = jvm.JObject(jenv, jstr)
        return self._make_jb_object(jstr)

    @annotate(Optional[unicode], s=JB_Object)
    def get_string(self, s):

        jenv = self.env
        jstr = s.o
        return JString(jenv, jstr, borrowed=True).str if jstr else None

    @annotate(Optional[unicode], s=JB_Object)
    def get_string_utf(self, s):

        jenv = self.env
        jstr = s.o
        return JString(jenv, jstr, borrowed=True).str if jstr else None

    @annotate(int, array=JB_Object)
    def get_array_length(self, array):

        jenv = self.env
        jarr = array.o
        return jenv.GetArrayLength(jarr)

    @annotate(array=JB_Object)
    def get_boolean_array_elements(self, array):

        # np.ndarray[dtype=np.uint8, ndim=1, negative_indices=False, mode='c']

        jenv = self.env
        size = self.get_array_length(array)
        result = np.zeros(shape=(size,), dtype=np.uint8)
        jarr = array.o
        jenv.GetBooleanArrayRegion(jarr, 0, size, result.ctypes.data_as(jni.POINTER(jni.jboolean)))
        return result.astype(np.bool8)

    @annotate(array=JB_Object)
    def get_byte_array_elements(self, array):

        # np.ndarray[dtype=np.ubyte, ndim=1, negative_indices=False, mode='c']

        jenv = self.env
        size = self.get_array_length(array)
        result = np.zeros(shape=(size,), dtype=np.ubyte)
        jarr = array.o
        jenv.GetByteArrayRegion(jarr, 0, size, result.ctypes.data_as(jni.POINTER(jni.jbyte)))
        return result

    @annotate(array=JB_Object)
    def get_short_array_elements(self, array):

        # np.ndarray[dtype=np.int16, ndim=1, negative_indices=False, mode='c']

        jenv = self.env
        size = self.get_array_length(array)
        result = np.zeros(shape=(size,), dtype=np.int16)
        jarr = array.o
        jenv.GetShortArrayRegion(jarr, 0, size, result.ctypes.data_as(jni.POINTER(jni.jshort)))
        return result

    @annotate(array=JB_Object)
    def get_int_array_elements(self, array):

        # np.ndarray[dtype=np.int32, ndim=1, negative_indices=False, mode='c']

        jenv = self.env
        size = self.get_array_length(array)
        result = np.zeros(shape=(size,), dtype=np.int32)
        jarr = array.o
        jenv.GetIntArrayRegion(jarr, 0, size, result.ctypes.data_as(jni.POINTER(jni.jint)))
        return result

    @annotate(array=JB_Object)
    def get_long_array_elements(self, array):

        # np.ndarray[dtype=np.int64, ndim=1, negative_indices=False, mode='c']

        jenv = self.env
        size = self.get_array_length(array)
        result = np.zeros(shape=(size,), dtype=np.int64)
        jarr = array.o
        jenv.GetLongArrayRegion(jarr, 0, size, result.ctypes.data_as(jni.POINTER(jni.jlong)))
        return result

    @annotate(array=JB_Object)
    def get_float_array_elements(self, array):

        # np.ndarray[dtype=np.float32, ndim=1, negative_indices=False, mode='c']

        jenv = self.env
        size = self.get_array_length(array)
        result = np.zeros(shape=(size,), dtype=np.float32)
        jarr = array.o
        jenv.GetFloatArrayRegion(jarr, 0, size, result.ctypes.data_as(jni.POINTER(jni.jfloat)))
        return result

    @annotate(array=JB_Object)
    def get_double_array_elements(self, array):

        # np.ndarray[dtype=np.float64, ndim=1, negative_indices=False, mode='c']

        jenv = self.env
        size = self.get_array_length(array)
        result = np.zeros(shape=(size,), dtype=np.float64)
        jarr = array.o
        jenv.GetDoubleArrayRegion(jarr, 0, size, result.ctypes.data_as(jni.POINTER(jni.jdouble)))
        return result

    @annotate(array=JB_Object)
    def get_object_array_elements(self, array):

        jvm  = get_jvm()
        jenv = self.env

        size = self.get_array_length(array)
        result = []
        jarr = array.o
        with JFrame(jenv) as jfrm:
            for ix in range(size):
                if not (ix % 256): jfrm.reset(256)
                jobj = jenv.GetObjectArrayElement(jarr, ix)
                jobj = jvm.JObject(jenv, jobj) if jobj else None
                result.append(self._make_jb_object(jobj) if jobj else None)
        return result

    @annotate(array="")
    def make_boolean_array(self, array):

        # np.ndarray[dtype=np.uint8, ndim=1, negative_indices=False, mode='c'] array = array.astype(np.bool8).astype(np.uint8)

        jvm  = get_jvm()
        jenv = self.env

        size = array.shape[0]
        with JFrame(jenv, 1):
            try:
                jarr = jenv.NewBooleanArray(size)
            except jni.Throwable:
                raise MemoryError("Failed to allocate boolean array of size {}".format(size))
            jenv.SetBooleanArrayRegion(jarr, 0, size, array.ctypes.data_as(jni.POINTER(jni.jboolean)))
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    @annotate(array="np.ndarray[dtype=np.ubyte, ndim=1, negative_indices=False, mode='c']")
    def make_byte_array(self, array):

        jvm  = get_jvm()
        jenv = self.env

        size = array.shape[0]
        with JFrame(jenv, 1):
            try:
                jarr = jenv.NewByteArray(size)
            except jni.Throwable:
                raise MemoryError("Failed to allocate byte array of size {}".format(size))
            jenv.SetByteArrayRegion(jarr, 0, size, array.ctypes.data_as(jni.POINTER(jni.jbyte)))
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    @annotate(array="np.ndarray[dtype=np.int16, ndim=1, negative_indices=False, mode='c']")
    def make_short_array(self, array):

        jvm  = get_jvm()
        jenv = self.env

        size = array.shape[0]
        with JFrame(jenv, 1):
            try:
                jarr = jenv.NewShortArray(size)
            except jni.Throwable:
                raise MemoryError("Failed to allocate short array of size {}".format(size))
            jenv.SetShortArrayRegion(jarr, 0, size, array.ctypes.data_as(jni.POINTER(jni.jshort)))
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    @annotate(array="np.ndarray[dtype=np.int32, ndim=1, negative_indices=False, mode='c']")
    def make_int_array(self, array):

        jvm  = get_jvm()
        jenv = self.env

        size = array.shape[0]
        with JFrame(jenv, 1):
            try:
                jarr = jenv.NewIntArray(size)
            except jni.Throwable:
                raise MemoryError("Failed to allocate int array of size {}".format(size))
            jenv.SetIntArrayRegion(jarr, 0, size, array.ctypes.data_as(jni.POINTER(jni.jint)))
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    @annotate(array="np.ndarray[dtype=np.int64, ndim=1, negative_indices=False, mode='c']")
    def make_long_array(self, array):

        jvm  = get_jvm()
        jenv = self.env

        size = array.shape[0]
        with JFrame(jenv, 1):
            try:
                jarr = jenv.NewLongArray(size)
            except jni.Throwable:
                raise MemoryError("Failed to allocate long array of size {}".format(size))
            jenv.SetLongArrayRegion(jarr, 0, size, array.ctypes.data_as(jni.POINTER(jni.jlong)))
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    @annotate(array="np.ndarray[dtype=np.float32, ndim=1, negative_indices=False, mode='c']")
    def make_float_array(self, array):

        jvm  = get_jvm()
        jenv = self.env

        size = array.shape[0]
        with JFrame(jenv, 1):
            try:
                jarr = jenv.NewFloatArray(size)
            except jni.Throwable:
                raise MemoryError("Failed to allocate float array of size {}".format(size))
            jenv.SetFloatArrayRegion(jarr, 0, size, array.ctypes.data_as(jni.POINTER(jni.jfloat)))
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    @annotate(array="np.ndarray[dtype=np.float64, ndim=1, negative_indices=False, mode='c']")
    def make_double_array(self, array):

        jvm  = get_jvm()
        jenv = self.env

        size = array.shape[0]
        with JFrame(jenv, 1):
            try:
                jarr = jenv.NewDoubleArray(size)
            except jni.Throwable:
                raise MemoryError("Failed to allocate double array of size {}".format(size))
            jenv.SetDoubleArrayRegion(jarr, 0, size, array.ctypes.data_as(jni.POINTER(jni.jdouble)))
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    @annotate(size=int, jclass=JB_Class)
    def make_object_array(self, size, jclass):

        jvm  = get_jvm()
        jenv = self.env

        jcls = jclass.c
        with JFrame(jenv, 1):
            try:
                jarr = jenv.NewObjectArray(size, jcls)
            except jni.Throwable:
                raise MemoryError("Failed to allocate object array of size {}".format(size))
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    @annotate(jobject=JB_Object, index=int, value=Optional[JB_Object])
    def set_object_array_element(self, jobject, index, value):

        jenv = self.env
        jenv.SetObjectArrayElement(jobject.o, index, value.o if value is not None else None)

    @annotate(JB_Object, jobject='JObject')
    def _make_jb_object(self, jobject):

        jbobject = JB_Object()
        jbobject._jobject = jobject
        return jbobject

    @staticmethod
    def _make_arguments(arg_sig, args):

        jvm = get_jvm()

        jargs = jvm.JArguments(len(args))
        sig = arg_sig
        for pos, arg in enumerate(args):

            if len(sig) == 0:
                raise ValueError("# of arguments ({}) in call did not match "
                                 "signature ({})".format(len(args), arg_sig))

            if sig[0] == 'Z':

                jargs.setBoolean(pos, bool(arg))
                sig = sig[1:]

            elif sig[0] == 'B':

                jargs.setByte(pos, int(arg))
                sig = sig[1:]

            elif sig[0] == 'C':

                jargs.setChar(pos, arg[0])
                sig = sig[1:]

            elif sig[0] == 'S':

                jargs.setShort(pos, int(arg))
                sig = sig[1:]

            elif sig[0] == 'I':

                jargs.setInt(pos, int(arg))
                sig = sig[1:]

            elif sig[0] == 'J':

                jargs.setLong(pos, int(arg))
                sig = sig[1:]

            elif sig[0] == 'F':

                jargs.setFloat(pos, float(arg))
                sig = sig[1:]

            elif sig[0] == 'D':

                jargs.setDouble(pos, float(arg))
                sig = sig[1:]

            elif sig[0] == 'L' or sig[0] == '[':

                if isinstance(arg, JB_Object):

                    jargs.arguments[pos].l = arg.o

                elif isinstance(arg, JB_Class):

                    jargs.arguments[pos].l = arg.c

                elif arg is None:

                    jargs.setObject(pos, None)

                else:
                    raise ValueError("{} is not a Java object".format(str(arg)))

                if sig[0] == '[':

                    if len(sig) == 1:
                        raise ValueError("Bad signature: {}".format(arg_sig))

                    non_bracket_ind = 1
                    try:
                        while sig[non_bracket_ind] == '[':
                            non_bracket_ind += 1
                    except IndexError:
                        raise ValueError("Bad signature: {}".format(arg_sig))
                    if sig[non_bracket_ind] != 'L':
                        # An array of primitive type:
                        sig = sig[(non_bracket_ind + 1):]
                        continue

                sig = sig[sig.find(';') + 1:]

            else:
                raise ValueError("Unhandled signature: {}".format(arg_sig))

        if len(sig) > 0:
            raise ValueError("Too few arguments ({}) for signature ({})".format(
                             len(args), arg_sig))
        return jargs
