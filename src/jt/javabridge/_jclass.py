# Copyright (c) 2014 Adam Karpierz
# SPDX-License-Identifier: BSD-3-Clause

import jni
from jvm.lib import public

from ._jvm import get_jenv
from ._jvm import dead


@public
class JB_Class:
    """A Java class"""

    def __new__(cls):
        self = super().__new__(cls)
        self._jclass = None
        return self

    c = property(lambda self: jni.cast(self._jclass.handle, jni.jclass)
                              if self._jclass else jni.obj(jni.jclass, 0))

    def __del__(self):
        jclass = self._jclass
        if jclass is None or not jclass._own: return
        jenv = get_jenv()
        if jenv:
            jenv.env.DeleteGlobalRef(jclass.handle)
            jclass._own = False
        else:
            dead(jclass)

    def __repr__(self):
        return "<Java class at {:#x}>".format(getattr(self.c, "value", id(self.c)))

    def as_class_object(self):
        jclass = self._jclass
        jbobject = JB_Object()
        jbobject._jobject = jclass.asObject() if jclass else None
        return jbobject


@public
class JB_Object:
    """Represents a Java object."""

    def __new__(cls):
        self = super().__new__(cls)
        self._jobject = None
        return self

    o = property(lambda self: jni.cast(self._jobject.handle, jni.jobject)
                              if self._jobject else jni.obj(jni.jobject, 0))

    def __del__(self):
        jobject = self._jobject
        if jobject is None or not jobject._own: return
        jenv = get_jenv()
        if jenv:
            jenv.env.DeleteGlobalRef(jobject.handle)
            jobject._own = False
        else:
            dead(jobject)

    def __repr__(self):
        return "<Java object at {:#x}>".format(getattr(self.o, "value", id(self.o)))

    def addr(self):
        return str(getattr(self.o, "value", id(self.o)))


class _JB_MethodID:

    def __new__(cls, id=0, sig: str = "", is_static: bool = False):
        self = super().__new__(cls)
        self.id        = id # jni.obj(jni.jmethodID, id)
        self.sig       = sig
        self.is_static = is_static
        return self

    def __repr__(self):
        return "<Java method with sig={} at {:#x}>".format(self.sig, int(self.id))


class _JB_FieldID:

    def __new__(cls, id=0, sig: str = "", is_static: bool = False):
        self = super().__new__(cls)
        self.id        = id # jni.obj(jni.jfieldID, id)
        self.sig       = sig
        self.is_static = is_static
        return self

    def __repr__(self):
        return "<Java field with sig={} at {:#x}>".format(self.sig, int(self.id))
