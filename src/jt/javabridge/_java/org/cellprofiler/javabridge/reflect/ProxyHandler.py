# Copyright (c) 2014 Adam Karpierz
# SPDX-License-Identifier: BSD-3-Clause

import jni

from jvm.jframe import JFrame
from jvm.jhost  import JHost
from jvm.java   import throwJavaException

from ......_jvm    import get_jvm
from ......_jvm    import jni_enter, jni_exit
from ......_jenv   import JB_Env
from ......_jclass import JB_Object


# Class: org.jt.reflect.ProxyHandler

# Method: native Object invoke(long target, Object proxy, java.lang.reflect.Method method, Object[] args);

@jni.method("(JLjava/lang/Object;Ljava/lang/reflect/Method;[Ljava/lang/Object;)Ljava/lang/Object;")
def invoke(env, this,
           target, jproxy, jmethod, jargs):

    proxy = jni.from_oid(target)

    jt_jvm = get_jvm()
    jenv = env[0]
    try:
        with JHost.CallbackState():
            jni_enter(jenv)
            method, args = None, []
            try:
                method = jt_jvm.JMethod(None, jmethod, own=False) if jmethod else None
                env = JB_Env()
                env.env = jenv
                args = env.get_object_array_elements(env._make_jb_object(
                       jt_jvm.JObject(None, jargs, own=False))) if jargs else []

                result = proxy(method, *args)

                if result is None:
                    return None
                else:
                    if not isinstance(result, JB_Object):
                        raise TypeError("Must be JB_Object")
                    return jenv.NewGlobalRef(result.o)
            finally:
                del method, args
                jni_exit()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        throwJavaException(jenv, "java.lang.Error", f"Python exception: {exc}")

    return None

# Method: native void initialize(long target);

@jni.method("(J)V")
def initialize(env, this,
               target):
    pass

# Method: native void release(long target);

@jni.method("(J)V")
def release(env, this,
            target):
    pass


__jnimethods__ = (
    invoke,
    initialize,
    release,
)
