# Copyright (c) 2014 Adam Karpierz
# SPDX-License-Identifier: BSD-3-Clause

from typing import Union, Optional, Tuple, List
import ctypes as ct

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

import jni
from jvm.lib import public

from jvm.jframe  import JFrame
from jvm.jstring import JString
from jvm._util   import str2jchars

from ._jvm    import get_jvm
from ._jclass import JB_Class, JB_Object, _JB_MethodID, _JB_FieldID

# cdef extern from "numpy/arrayobject.h":
#     ctypedef class numpy.ndarray [object PyArrayObject]:
#         cdef char *data
#         cdef Py_intptr_t *dimensions
#         cdef Py_intptr_t *strides


@public
class JB_Env:

    """Represents the Java VM and the Java execution environment."""

    def __new__(cls):
        self = super().__new__(cls)
        self.env = None  # jni.JNIEnv
        return self

    def __repr__(self):
        return "<JB_Env at {:#x}>".format(id(self.env))

    def set_env(self, jenv: jni.JNIEnv):
        self.env = jenv
        if not self.env:
            raise ValueError("set_env called with non-environment capsule")

    def dealloc_jobject(self, jbobject: JB_Object):
        jobject = jbobject._jobject
        if jbobject.o:
            self.env.DeleteGlobalRef(jobject.handle)
        if jbobject:
            jobject._own = False

    def get_version(self) -> Tuple[int, int]:
        version = self.env.GetVersion()
        return (int(version // 65536), version % 65536)

    def find_class(self, name: str) -> JB_Class:
        jvm  = get_jvm()
        jenv = self.env

        name = name.encode("utf-8").translate(jvm.JClass.name_trans).decode("utf-8")
        jclass = jvm.JClass.forName(name)

        jbclass = JB_Class()
        jbclass._jclass = jvm.JClass(jenv, jclass.handle)
        return jbclass

    def get_object_class(self, jbobject: JB_Object) -> JB_Class:
        jvm  = get_jvm()
        jenv = self.env

        jobject = jbobject._jobject
        jclass  = jobject.getClass()

        jbclass = JB_Class()
        jbclass._jclass = jvm.JClass(jenv, jclass.handle)
        return jbclass

    def is_instance_of(self, jbobject: JB_Object, jbclass: JB_Class) -> bool:
        jobject = jbobject._jobject
        jclass  = jbclass._jclass
        return jclass.isInstance(jobject)

    def exception_occurred(self) -> Optional[JB_Object]:
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

    def get_method_id(self, jbclass: JB_Class, name: str, sig: str) ->_JB_MethodID:
        if jbclass is None:
            raise ValueError("Class = None on call to get_method_id")
        jcls = jbclass.c
        try:
            id = self.env.GetMethodID(jcls, name.encode("utf-8"), sig.encode("utf-8"))
        except jni.Throwable as exc:
            return None
        return _JB_MethodID(id, sig, False)

    def get_static_method_id(self, jbclass: JB_Class, name: str, sig: str) -> _JB_MethodID:
        jcls = jbclass.c
        try:
            id = self.env.GetStaticMethodID(jcls, name.encode("utf-8"), sig.encode("utf-8"))
        except jni.Throwable as exc:
            return None
        return _JB_MethodID(id, sig, True)

    def from_reflected_method(self, method: JB_Object, sig: bytes, is_static: bool) -> _JB_MethodID:
        try:
            id = self.env.FromReflectedMethod(method.o)
        except jni.Throwable as exc:
            return None
        if not id:
            return None
        return _JB_MethodID(id, sig, is_static)

    def call_method(self, jobject: JB_Object, meth: _JB_MethodID, *args) -> object:

        if meth is None:
            raise ValueError("Method ID is None - check your method ID call")

        if meth.is_static:
            raise ValueError("call_method called with a static method. "
                             "Use call_static_method instead")

        if meth.sig[0] != '(' or ')' not in meth.sig:
            raise ValueError(f"Bad function signature: {meth.sig}")

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
            raise ValueError(f"Unhandled return type. Signature = {meth.sig}")

    def call_static_method(self, jbclass: JB_Class, meth: _JB_MethodID, *args) -> object:

        if meth is None:
            raise ValueError("Method ID is None - check your method ID call")

        if not meth.is_static:
            raise ValueError("call_static_method called with an object method. "
                             "Use call_method instead")

        if meth.sig[0] != '(' or ')' not in meth.sig:
            raise ValueError(f"Bad function signature: {meth.sig}")

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
            raise ValueError(f"Unhandled return type. Signature = {meth.sig}")

    def get_field_id(self, jbclass: JB_Class, name: str, sig: str) -> _JB_FieldID:
        jcls = jbclass.c
        try:
            id = self.env.GetFieldID(jcls, name.encode("utf-8"), sig.encode("utf-8"))
        except jni.Throwable as exc:
            raise get_jvm().JavaException(exc)
        return _JB_FieldID(id, sig, False)

    def get_static_field_id(self, jbclass: JB_Class, name: str, sig: str) -> _JB_FieldID:
        jcls = jbclass.c
        try:
            id = self.env.GetStaticFieldID(jcls, name.encode("utf-8"), sig.encode("utf-8"))
        except jni.Throwable as exc:
            raise get_jvm().JavaException(exc)
        return _JB_FieldID(id, sig, True)  # !!! bylo False, chyba blad !!!

    def get_boolean_field(self, jbobject: JB_Object, field: _JB_FieldID):
        jenv = self.env
        this = jbobject._jobject
        return jenv.GetBooleanField(this.handle, field.id)

    def get_byte_field(self, jbobject: JB_Object, field: _JB_FieldID):
        jenv = self.env
        this = jbobject._jobject
        return jenv.GetByteField(this.handle, field.id)

    def get_char_field(self, jbobject: JB_Object, field: _JB_FieldID):
        jenv = self.env
        this = jbobject._jobject
        return jenv.GetCharField(this.handle, field.id)

    def get_short_field(self, jbobject: JB_Object, field: _JB_FieldID):
        jenv = self.env
        this = jbobject._jobject
        return jenv.GetShortField(this.handle, field.id)

    def get_int_field(self, jbobject: JB_Object, field: _JB_FieldID):
        jenv = self.env
        this = jbobject._jobject
        return jenv.GetIntField(this.handle, field.id)

    def get_long_field(self, jbobject: JB_Object, field: _JB_FieldID):
        jenv = self.env
        this = jbobject._jobject
        return jenv.GetLongField(this.handle, field.id)

    def get_float_field(self, jbobject: JB_Object, field: _JB_FieldID):
        jenv = self.env
        this = jbobject._jobject
        return jenv.GetFloatField(this.handle, field.id)

    def get_double_field(self, jbobject: JB_Object, field: _JB_FieldID):
        jenv = self.env
        this = jbobject._jobject
        return jenv.GetDoubleField(this.handle, field.id)

    def get_object_field(self, jbobject: JB_Object, field: _JB_FieldID) -> Optional[JB_Object]:
        jvm  = get_jvm()
        jenv = self.env
        this = jbobject._jobject
        with JFrame(jenv, 1):
            jobj = jenv.GetObjectField(this.handle, field.id)
            jobj = jvm.JObject(jenv, jobj) if jobj else None
        return self._make_jb_object(jobj) if jobj else None

    def set_boolean_field(self, jbobject: JB_Object, field: _JB_FieldID, value):
        jenv = self.env
        this = jbobject._jobject
        jenv.SetBooleanField(this.handle, field.id, value)

    def set_byte_field(self, jbobject: JB_Object, field: _JB_FieldID, value):
        jenv = self.env
        this = jbobject._jobject
        jenv.SetByteField(this.handle, field.id, value)

    def set_char_field(self, jbobject: JB_Object, field: _JB_FieldID, value):
        assert len(str(value)) > 0
        jenv = self.env
        this = jbobject._jobject
        jenv.SetCharField(this.handle, field.id, value)

    def set_short_field(self, jbobject: JB_Object, field: _JB_FieldID, value):
        jenv = self.env
        this = jbobject._jobject
        jenv.SetShortField(this.handle, field.id, value)

    def set_int_field(self, jbobject: JB_Object, field: _JB_FieldID, value):
        jenv = self.env
        this = jbobject._jobject
        jenv.SetIntField(this.handle, field.id, value)

    def set_long_field(self, jbobject: JB_Object, field: _JB_FieldID, value):
        jenv = self.env
        this = jbobject._jobject
        jenv.SetLongField(this.handle, field.id, value)

    def set_float_field(self, jbobject: JB_Object, field: _JB_FieldID, value):
        jenv = self.env
        this = jbobject._jobject
        jenv.SetFloatField(this.handle, field.id, value)

    def set_double_field(self, jbobject: JB_Object, field: _JB_FieldID, value):
        jenv = self.env
        this = jbobject._jobject
        jenv.SetDoubleField(this.handle, field.id, value)

    def set_object_field(self, jbobject: JB_Object, field: _JB_FieldID, value: Optional[JB_Object]):
        jenv = self.env
        this = jbobject._jobject
        jenv.SetObjectField(this.handle, field.id, value.o if value is not None else None)

    def get_static_boolean_field(self, jbclass: JB_Class, field: _JB_FieldID):
        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticBooleanField(jcls, field.id)

    def get_static_byte_field(self, jbclass: JB_Class, field: _JB_FieldID):
        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticByteField(jcls, field.id)

    def get_static_char_field(self, jbclass: JB_Class, field: _JB_FieldID):
        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticCharField(jcls, field.id)

    def get_static_short_field(self, jbclass: JB_Class, field: _JB_FieldID):
        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticShortField(jcls, field.id)

    def get_static_int_field(self, jbclass: JB_Class, field: _JB_FieldID):
        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticIntField(jcls, field.id)

    def get_static_long_field(self, jbclass: JB_Class, field: _JB_FieldID):
        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticLongField(jcls, field.id)

    def get_static_float_field(self, jbclass: JB_Class, field: _JB_FieldID):
        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticFloatField(jcls, field.id)

    def get_static_double_field(self, jbclass: JB_Class, field: _JB_FieldID):
        jenv = self.env
        jcls = jbclass.c
        return jenv.GetStaticDoubleField(jcls, field.id)

    def get_static_object_field(self, jbclass: JB_Class, field: _JB_FieldID) -> Optional[JB_Object]:
        jvm  = get_jvm()
        jenv = self.env
        jcls = jbclass.c
        with JFrame(jenv, 1):
            jobj = jenv.GetStaticObjectField(jcls, field.id)
            jobj = jvm.JObject(jenv, jobj) if jobj else None
        return self._make_jb_object(jobj) if jobj else None

    def set_static_boolean_field(self, jbclass: JB_Class, field: _JB_FieldID, value):
        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticBooleanField(jcls, field.id, value)

    def set_static_byte_field(self, jbclass: JB_Class, field: _JB_FieldID, value):
        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticByteField(jcls, field.id, value)

    def set_static_char_field(self, jbclass: JB_Class, field: _JB_FieldID, value):
        assert len(str(value)) > 0
        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticCharField(jcls, field.id, value)

    def set_static_short_field(self, jbclass: JB_Class, field: _JB_FieldID, value):
        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticShortField(jcls, field.id, value)

    def set_static_int_field(self, jbclass: JB_Class, field: _JB_FieldID, value):
        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticIntField(jcls, field.id, value)

    def set_static_long_field(self, jbclass: JB_Class, field: _JB_FieldID, value):
        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticLongField(jcls, field.id, value)

    def set_static_float_field(self, jbclass: JB_Class, field: _JB_FieldID, value):
        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticFloatField(jcls, field.id, value)

    def set_static_double_field(self, jbclass: JB_Class, field: _JB_FieldID, value):
        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticDoubleField(jcls, field.id, value)

    def set_static_object_field(self, jbclass: JB_Class, field: _JB_FieldID, value: Optional[JB_Object]):
        jenv = self.env
        jcls = jbclass.c
        jenv.SetStaticObjectField(jcls, field.id, value.o if value is not None else None)

    def new_object(self, jclass: JB_Class, meth: _JB_MethodID, *args) -> Optional[JB_Object]:
        if meth.sig[0] != '(' or ')' not in meth.sig:
            raise ValueError(f"Bad function signature: {meth.sig}")

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

    def new_string(self, u: str) -> JB_Object:
        jvm  = get_jvm()
        jenv = self.env
        with JFrame(jenv, 1):
            try:
                jchars, size, jbuf = str2jchars(u)
                jstr = jenv.NewString(jchars, size)
            except jni.Throwable:
                raise MemoryError("Failed to allocate string")
            if not jstr:
                raise MemoryError("Failed to allocate string")
            jstr = jvm.JObject(jenv, jstr)
        return self._make_jb_object(jstr)

    def new_string_utf(self, s: str) -> JB_Object:
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

    def get_string(self, s: JB_Object) -> Optional[str]:
        jenv = self.env
        jstr = s.o
        return JString(jenv, jstr, own=False).str if jstr else None

    def get_string_utf(self, s: JB_Object) -> Optional[str]:
        jenv = self.env
        jstr = s.o
        return JString(jenv, jstr, own=False).str if jstr else None

    def get_array_length(self, array: JB_Object) -> int:
        jenv = self.env
        jarr = array.o
        return jenv.GetArrayLength(jarr)

    def get_boolean_array_elements(self, array: JB_Object):
        # np.ndarray[dtype=np.uint8, ndim=1, negative_indices=False, mode='c']
        jenv = self.env
        size = self.get_array_length(array)
        result = np.zeros(shape=(size,), dtype=np.uint8)
        addr = result.ctypes.data_as(ct.c_void_p)
        jarr = array.o
        jenv.GetBooleanArrayRegion(jarr, 0, size,
                                   jni.cast(addr.value, jni.POINTER(jni.jboolean)))
        return result.astype(np.bool_)

    def get_byte_array_elements(self, array: JB_Object):
        # np.ndarray[dtype=np.ubyte, ndim=1, negative_indices=False, mode='c']
        jenv = self.env
        size = self.get_array_length(array)
        result = np.zeros(shape=(size,), dtype=np.ubyte)
        addr = result.ctypes.data_as(ct.c_void_p)
        jarr = array.o
        jenv.GetByteArrayRegion(jarr, 0, size,
                                jni.cast(addr.value, jni.POINTER(jni.jbyte)))
        return result

    def get_short_array_elements(self, array: JB_Object):
        # np.ndarray[dtype=np.int16, ndim=1, negative_indices=False, mode='c']
        jenv = self.env
        size = self.get_array_length(array)
        result = np.zeros(shape=(size,), dtype=np.int16)
        addr = result.ctypes.data_as(ct.c_void_p)
        jarr = array.o
        jenv.GetShortArrayRegion(jarr, 0, size,
                                 jni.cast(addr.value, jni.POINTER(jni.jshort)))
        return result

    def get_int_array_elements(self, array: JB_Object):
        # np.ndarray[dtype=np.int32, ndim=1, negative_indices=False, mode='c']
        jenv = self.env
        size = self.get_array_length(array)
        result = np.zeros(shape=(size,), dtype=np.int32)
        addr = result.ctypes.data_as(ct.c_void_p)
        jarr = array.o
        jenv.GetIntArrayRegion(jarr, 0, size,
                               jni.cast(addr.value, jni.POINTER(jni.jint)))
        return result

    def get_long_array_elements(self, array: JB_Object):
        # np.ndarray[dtype=np.int64, ndim=1, negative_indices=False, mode='c']
        jenv = self.env
        size = self.get_array_length(array)
        result = np.zeros(shape=(size,), dtype=np.int64)
        addr = result.ctypes.data_as(ct.c_void_p)
        jarr = array.o
        jenv.GetLongArrayRegion(jarr, 0, size,
                                jni.cast(addr.value, jni.POINTER(jni.jlong)))
        return result

    def get_float_array_elements(self, array: JB_Object):
        # np.ndarray[dtype=np.float32, ndim=1, negative_indices=False, mode='c']
        jenv = self.env
        size = self.get_array_length(array)
        result = np.zeros(shape=(size,), dtype=np.float32)
        addr = result.ctypes.data_as(ct.c_void_p)
        jarr = array.o
        jenv.GetFloatArrayRegion(jarr, 0, size,
                                 jni.cast(addr.value, jni.POINTER(jni.jfloat)))
        return result

    def get_double_array_elements(self, array: JB_Object):
        # np.ndarray[dtype=np.float64, ndim=1, negative_indices=False, mode='c']
        jenv = self.env
        size = self.get_array_length(array)
        result = np.zeros(shape=(size,), dtype=np.float64)
        addr = result.ctypes.data_as(ct.c_void_p)
        jarr = array.o
        jenv.GetDoubleArrayRegion(jarr, 0, size,
                                  jni.cast(addr.value, jni.POINTER(jni.jdouble)))
        return result

    def get_object_array_elements(self, array: JB_Object) -> List[Optional[JB_Object]]:
        jvm  = get_jvm()
        jenv = self.env
        result = []
        with JFrame(jenv) as jfrm:
            size = self.get_array_length(array)
            jarr = array.o
            for ix in range(size):
                if not (ix % 256): jfrm.reset(256)
                jobj = jenv.GetObjectArrayElement(jarr, ix)
                jobj = jvm.JObject(jenv, jobj) if jobj else None
                result.append(self._make_jb_object(jobj) if jobj else None)
        return result

    def make_boolean_array(self,
            array: "np.ndarray[dtype=np.uint8, ndim=1, negative_indices=False, mode='c']") -> JB_Object:
        # np.ndarray[dtype=np.uint8, ndim=1, negative_indices=False, mode='c'] array = array.astype(np.bool_).astype(np.uint8)
        jvm  = get_jvm()
        jenv = self.env
        with JFrame(jenv, 1):
            size = array.shape[0]
            try:
                jarr = jenv.NewBooleanArray(size)
            except jni.Throwable:
                raise MemoryError(f"Failed to allocate boolean array of size {size}")
            addr = array.ctypes.data_as(ct.c_void_p)
            jenv.SetBooleanArrayRegion(jarr, 0, size,
                                       jni.cast(addr.value, jni.POINTER(jni.jboolean)))
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    def make_byte_array(self,
            array: "np.ndarray[dtype=np.ubyte, ndim=1, negative_indices=False, mode='c']") -> JB_Object:
        jvm  = get_jvm()
        jenv = self.env
        with JFrame(jenv, 1):
            size = array.shape[0]
            try:
                jarr = jenv.NewByteArray(size)
            except jni.Throwable:
                raise MemoryError(f"Failed to allocate byte array of size {size}")
            addr = array.ctypes.data_as(ct.c_void_p)
            jenv.SetByteArrayRegion(jarr, 0, size,
                                    jni.cast(addr.value, jni.POINTER(jni.jbyte)))
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    def make_short_array(self,
            array: "np.ndarray[dtype=np.int16, ndim=1, negative_indices=False, mode='c']") -> JB_Object:
        jvm  = get_jvm()
        jenv = self.env
        with JFrame(jenv, 1):
            size = array.shape[0]
            try:
                jarr = jenv.NewShortArray(size)
            except jni.Throwable:
                raise MemoryError(f"Failed to allocate short array of size {size}")
            addr = array.ctypes.data_as(ct.c_void_p)
            jenv.SetShortArrayRegion(jarr, 0, size,
                                     jni.cast(addr.value, jni.POINTER(jni.jshort)))
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    def make_int_array(self,
            array: "np.ndarray[dtype=np.int32, ndim=1, negative_indices=False, mode='c']") -> JB_Object:
        jvm  = get_jvm()
        jenv = self.env
        with JFrame(jenv, 1):
            size = array.shape[0]
            try:
                jarr = jenv.NewIntArray(size)
            except jni.Throwable:
                raise MemoryError(f"Failed to allocate int array of size {size}")
            addr = array.ctypes.data_as(ct.c_void_p)
            jenv.SetIntArrayRegion(jarr, 0, size,
                                   jni.cast(addr.value, jni.POINTER(jni.jint)))
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    def make_long_array(self,
            array: "np.ndarray[dtype=np.int64, ndim=1, negative_indices=False, mode='c']") -> JB_Object:
        jvm  = get_jvm()
        jenv = self.env
        with JFrame(jenv, 1):
            size = array.shape[0]
            try:
                jarr = jenv.NewLongArray(size)
            except jni.Throwable:
                raise MemoryError(f"Failed to allocate long array of size {size}")
            addr = array.ctypes.data_as(ct.c_void_p)
            jenv.SetLongArrayRegion(jarr, 0, size,
                                    jni.cast(addr.value, jni.POINTER(jni.jlong)))
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    def make_float_array(self,
            array: "np.ndarray[dtype=np.float32, ndim=1, negative_indices=False, mode='c']") -> JB_Object:
        jvm  = get_jvm()
        jenv = self.env
        with JFrame(jenv, 1):
            size = array.shape[0]
            try:
                jarr = jenv.NewFloatArray(size)
            except jni.Throwable:
                raise MemoryError(f"Failed to allocate float array of size {size}")
            addr = array.ctypes.data_as(ct.c_void_p)
            jenv.SetFloatArrayRegion(jarr, 0, size,
                                     jni.cast(addr.value, jni.POINTER(jni.jfloat)))
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    def make_double_array(self,
            array: "np.ndarray[dtype=np.float64, ndim=1, negative_indices=False, mode='c']") -> JB_Object:
        jvm  = get_jvm()
        jenv = self.env
        with JFrame(jenv, 1):
            size = array.shape[0]
            try:
                jarr = jenv.NewDoubleArray(size)
            except jni.Throwable:
                raise MemoryError(f"Failed to allocate double array of size {size}")
            addr = array.ctypes.data_as(ct.c_void_p)
            jenv.SetDoubleArrayRegion(jarr, 0, size,
                                      jni.cast(addr.value, jni.POINTER(jni.jdouble)))
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    def make_object_array(self, size: int, jclass: JB_Class) -> JB_Object:
        jvm  = get_jvm()
        jenv = self.env
        with JFrame(jenv, 1):
            jcls = jclass.c
            try:
                jarr = jenv.NewObjectArray(size, jcls)
            except jni.Throwable:
                raise MemoryError(f"Failed to allocate object array of size {size}")
            jarr = jvm.JObject(jenv, jarr)
        return self._make_jb_object(jarr)

    def set_object_array_element(self, jobject: JB_Object, index: int, value: Optional[JB_Object]):
        jenv = self.env
        jenv.SetObjectArrayElement(jobject.o, index, value.o if value is not None else None)

    def _make_jb_object(self, jobject: 'JObject') -> JB_Object:
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
                raise ValueError(f"# of arguments ({len(args)}) in call "
                                 f"did not match signature ({arg_sig})")

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
                    raise ValueError(f"{str(arg)} is not a Java object")

                if sig[0] == '[':

                    if len(sig) == 1:
                        raise ValueError(f"Bad signature: {arg_sig}")

                    non_bracket_ind = 1
                    try:
                        while sig[non_bracket_ind] == '[':
                            non_bracket_ind += 1
                    except IndexError:
                        raise ValueError(f"Bad signature: {arg_sig}")
                    if sig[non_bracket_ind] != 'L':
                        # An array of primitive type:
                        sig = sig[(non_bracket_ind + 1):]
                        continue

                sig = sig[sig.find(';') + 1:]

            else:
                raise ValueError(f"Unhandled signature: {arg_sig}")

        if len(sig) > 0:
            raise ValueError(f"Too few arguments ({len(args)}) for signature ({arg_sig})")

        return jargs
