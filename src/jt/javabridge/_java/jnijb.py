# Copyright (c) 2014-2018, Adam Karpierz
# Licensed under the BSD license
# http://opensource.org/licenses/BSD-3-Clause

from ...jvm.lib.compat import *
from ...jvm.lib import annotate
from ...        import jni

from ...jvm.java.jnij import jnij
from ...jvm.java      import registerClass
from ...jvm.java      import registerNatives
from ...jvm.java      import unregisterNatives


class javabridge_CPython(jnij):

    @annotate(jenv=jni.JNIEnv)
    def initialize(self, jenv):

        from .org.cellprofiler.javabridge import (CPython,
                                                  CPython_StackFrame,
                                                  CPython_WrappedException)
        registerClass(jenv, "org.cellprofiler.javabridge.CPython$StackFrame",
                      CPython_StackFrame)
        registerClass(jenv, "org.cellprofiler.javabridge.CPython$WrappedException",
                      CPython_WrappedException)
        registerClass(jenv, "org.cellprofiler.javabridge.CPython",
                      CPython)

class javabridge_RunnableQueue(jnij):

    @annotate(jenv=jni.JNIEnv)
    def initialize(self, jenv):

        from .org.cellprofiler.runnablequeue import RunnableQueue, RunnableQueue_1
        registerClass(jenv, "org.cellprofiler.runnablequeue.RunnableQueue$1",
                      RunnableQueue_1)
        registerClass(jenv, "org.cellprofiler.runnablequeue.RunnableQueue",
                      RunnableQueue)

class javabridge_reflect_ProxyHandler(jnij):

    @annotate(jenv=jni.JNIEnv)
    def initialize(self, jenv):

        from .org.cellprofiler.javabridge.reflect import ProxyHandler
        unregisterNatives(jenv, "com.jt.reflect.ProxyHandler")
        registerNatives(jenv,   "com.jt.reflect.ProxyHandler", ProxyHandler)
