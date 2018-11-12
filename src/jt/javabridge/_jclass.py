# Copyright (c) 2014-2018, Adam Karpierz
# Licensed under the BSD license
# http://opensource.org/licenses/BSD-3-Clause

from ..jvm.lib import annotate
from ..jvm.lib import public
from ..        import jni

from ._jvm import get_jenv
from ._jvm import dead


@public
class JB_Class(object):

    """A Java class"""

    def __new__(cls):

        self = super(JB_Class, cls).__new__(cls)
        self._jclass = None
        return self

    c = property(lambda self: jni.cast(self._jclass.handle, jni.jclass)
                              if self._jclass else jni.obj(jni.jclass, 0))

    def __del__(self):

        jclass = self._jclass
        if jclass is None or jclass._borrowed: return
        jenv = get_jenv()
        if jenv:
            jenv.env.DeleteGlobalRef(jclass.handle)
            jclass._borrowed = True
        else:
            dead(jclass)

    def __repr__(self):

        return "<Java class at {:#x}>".format(self.c.value)

    def as_class_object(self):

        jclass = self._jclass
        jbobject = JB_Object()
        jbobject._jobject = jclass.asObject() if jclass else None
        return jbobject


@public
class JB_Object(object):

    """Represents a Java object."""

    def __new__(cls):

        self = super(JB_Object, cls).__new__(cls)
        self._jobject = None
        return self

    o = property(lambda self: jni.cast(self._jobject.handle, jni.jobject)
                              if self._jobject else jni.obj(jni.jobject, 0))

    def __del__(self):

        jobject = self._jobject
        if jobject is None or jobject._borrowed: return
        jenv = get_jenv()
        if jenv:
            jenv.env.DeleteGlobalRef(jobject.handle)
            jobject._borrowed = True
        else:
            dead(jobject)

    def __repr__(self):

        return "<Java object at {:#x}>".format(self.o.value)

    def addr(self):

        return str(self.o.value)


class _JB_MethodID(object):

    def __new__(cls, id=0, sig="", is_static=False):

        self = super(_JB_MethodID, cls).__new__(cls)
        self.id        = id # jni.obj(jni.jmethodID, id)
        self.sig       = sig
        self.is_static = is_static
        return self

    def __repr__(self):

        return "<Java method with sig={} at {:#x}>".format(self.sig, int(self.id))


class _JB_FieldID(object):

    def __new__(cls, id=0, sig="", is_static=False):

        self = super(_JB_FieldID, cls).__new__(cls)
        self.id        = id # jni.obj(jni.jfieldID, id)
        self.sig       = sig
        self.is_static = is_static
        return self

    def __repr__(self):

        return "<Java field with sig={} at {:#x}>".format(self.sig, int(self.id))
