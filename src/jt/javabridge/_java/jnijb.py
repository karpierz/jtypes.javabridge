# Copyright (c) 2014 Adam Karpierz
# SPDX-License-Identifier: BSD-3-Clause

import jni

from jvm.java.jnij import jnij
from jvm.java import registerClass
from jvm.java import registerNatives
from jvm.java import unregisterNatives


class javabridge_CPython(jnij):

    def initialize(self, jenv: jni.JNIEnv):
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

    def initialize(self, jenv: jni.JNIEnv):
        from .org.cellprofiler.runnablequeue import RunnableQueue, RunnableQueue_1
        registerClass(jenv, "org.cellprofiler.runnablequeue.RunnableQueue$1",
                      RunnableQueue_1)
        registerClass(jenv, "org.cellprofiler.runnablequeue.RunnableQueue",
                      RunnableQueue)

class javabridge_reflect_ProxyHandler(jnij):

    def initialize(self, jenv: jni.JNIEnv):
        from .org.cellprofiler.javabridge.reflect import ProxyHandler
        unregisterNatives(jenv, "org.jt.reflect.ProxyHandler")
        registerNatives(jenv,   "org.jt.reflect.ProxyHandler", ProxyHandler)
