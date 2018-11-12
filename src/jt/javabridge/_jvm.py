# Copyright (c) 2014-2018, Adam Karpierz
# Licensed under the BSD license
# http://opensource.org/licenses/BSD-3-Clause

from __future__ import absolute_import

import threading

from ..jvm.lib import annotate
from ..jvm.lib import public
from ..jvm.lib import classproperty
from ..        import jni

from ..jvm import JVM as _JVM

from ._platform._nomac import MacStartVM, StopVM
from ._platform._nomac import (MacRunLoopInit, MacRunLoopReset, MacRunLoopRun,
                               MacRunLoopRunInMode, MacRunLoopStop, MacIsMainThread)


def mac_run_loop_init():

    MacRunLoopInit()

def mac_reset_run_loop():

    # with _nogil():
    MacRunLoopReset()

def mac_enter_run_loop():

    # with _nogil():
    MacRunLoopRun()

def mac_poll_run_loop(timeout):

    MacRunLoopRunInMode(timeout)

def mac_stop_run_loop():

    # with _nogil():
    MacRunLoopStop()

def mac_is_main_thread():

    return MacIsMainThread() != 0


##################################################################
#                                                                #
# Threading                                                      #
#                                                                #
# Java environments are thread-specific and the Java             #
# VM is global. This section helps maintain each thread's        #
# Java environment as a thread-local variable shared with        #
# the Cython code and maintains the VM singleton.                #
#                                                                #
# In addition, there's a wakeup event that's used to             #
# communicate with the thread that's in charge of garbage-       #
# collection objects deleted on a thread without an environment. #
#                                                                #
##################################################################

__vm            = None
__thread_locals = threading.local()
__wake_event    = threading.Event()
__dead_objects  = []

def get_jvm():

    global __vm
    if __vm is None:
        __vm = JB_VM()
    return __vm

def get_jenv():

    return get_thread_local("env")

def get_thread_local(key, default=None):

    global __thread_locals
    if not hasattr(__thread_locals, key):
        setattr(__thread_locals, key, default)
    return getattr(__thread_locals, key)

def set_thread_local(key, value):

    global  __thread_locals
    setattr(__thread_locals, key, value)

def wait_for_wake_event():

    global __wake_event
    __wake_event.wait()
    __wake_event.clear()

def set_wake_event():

    global __wake_event
    __wake_event.set()

def jb_attach():

    global __vm
    assert __vm is not None
    assert get_thread_local("env") is None
    assert __vm.is_active()
    set_thread_local("env", __vm.attach_as_daemon())
    return get_thread_local("env")

def jb_detach():

    global __vm
    assert __vm is not None
    assert get_thread_local("env") is not None
    set_thread_local("env", None)
    __vm.detach()

def jni_enter(env):

    from ._jenv import JB_Env

    env_stack = get_thread_local("envstack", None)
    if env_stack is None:
        env_stack = []
        set_thread_local("envstack", env_stack)
    old_env = get_thread_local("env")
    if old_env is not None:
        env_stack.append(old_env)
    new_env = JB_Env()
    new_env.set_env(env)
    set_thread_local("env", new_env)

def jni_exit():

    env_stack = get_thread_local("envstack")
    set_thread_local("env", env_stack.pop() if env_stack else None)

def jvm_enter(vm):

    get_jvm().set_vm(vm)

def dead(jobject):

    global __dead_objects
    __dead_objects.append(jobject)
    set_wake_event()

def reap():

    global __dead_objects
    if __dead_objects:
        jenv = get_jenv()
        assert jenv is not None
        while __dead_objects:
            to_die = __dead_objects.pop()
            jenv.env.DeleteGlobalRef(to_die.handle)
            to_die._borrowed = True


@public
class JB_VM(_JVM):

    """Represents the Java virtual machine"""

    def __init__(self):

        self._dll_path = None
        self._jvm      = None

    vm = property(lambda self: self._jvm.jnijvm if self._jvm is not None else None)
    
    def set_vm(self, capsule):

        '''Set the pointer to the JavaVM
        
        This is here to handle the case where Java is the boss and Python
        is being started from Java, e.g. from 
        org.cellprofiler.javabridge.CPython.
        
        :param capsule: an encapsulated pointer to the JavaVM
        '''

        if not PyCapsule_CheckExact(capsule):
            raise ValueError("set_vm called with something other than a wrapped environment")

        #self.vm =
        self._jvm.jnijvm = ct.cast(PyCapsule_GetPointer(capsule, NULL), "<JavaVM *>")

        if not self.vm:
            raise ValueError("set_vm called with non-environment capsule")

    def is_active(self):

        return self.vm is not None

    def create(self, jvmoptions):

        try:
            #with self:
            self._load()
            self.start(*jvmoptions)

            from ._java import jnijb

            CPython       = jnijb.javabridge_CPython()
            RunnableQueue = jnijb.javabridge_RunnableQueue()
            ProxyHandler  = jnijb.javabridge_reflect_ProxyHandler()

            with self as (jvm, jenv):
                CPython.initialize(jenv)
                RunnableQueue.initialize(jenv)
                ProxyHandler.initialize(jenv)

        except jni.JNIException as exc:
            raise RuntimeError("Failed to create Java VM. "
                               "Return code = {}".format(exc.getError()))
        env = self.attach()
        set_thread_local("env", env)
        return env

    def create_mac(self, jvmoptions, class_name=None):

        if class_name is None:
            class_name = "org/cellprofiler/runnablequeue/RunnableQueue"

        from ._platform._osx import JVMFinder
        finder = JVMFinder()
        libjvm_path = finder._find_mac_lib("libjvm")
        libjli_path = finder._find_mac_lib("libjli")
        if (libjvm_path is None or
            libjli_path is None): # <AK> added
            raise Exception("Javabridge failed to find JVM library")

        class_name  = str(class_name).encode("utf-8")
        libjvm_path = str(libjvm_path).encode("utf-8")
        libjli_path = str(libjli_path).encode("utf-8")

        try:
            # < result = CreateJavaVM(&self.vm, <void **>&env, &args)
            # -
            # > # with _nogil():
            # > result = MacStartVM(&self.vm, <void **>&env, &args,
            # >                     pclass_name, ppath_to_libjvm, ppath_to_libjli)

            #with self:
            self.start(*jvmoptions)

            from ._java import jnijb

            CPython       = jnijb.javabridge_CPython()
            RunnableQueue = jnijb.javabridge_RunnableQueue()
            ProxyHandler  = jnijb.javabridge_reflect_ProxyHandler()

            with self as (jvm, jenv):
                CPython.initialize(jenv)
                RunnableQueue.initialize(jenv)
                ProxyHandler.initialize(jenv)

        except jni.JNIException as exc:
            raise RuntimeError("Failed to create Java VM. "
                               "Return code = {}".format(exc.getError()))
        assert get_thread_local("env") is None
        env = self.attach_as_daemon()
        set_thread_local("env", env)
        return env

    def _load(self, dll_path=None):

        from ..jvm.platform import JVMFinder
        from ..jvm          import EStatusCode
        from .jutil         import JavaException

        if dll_path is not None:
            self._dll_path = dll_path

        if self._dll_path is None:
            finder = JVMFinder()
            self._dll_path = finder.get_jvm_path()

        super(JB_VM, self).__init__(self._dll_path)
        self.JavaException = JavaException

    def attach(self):

        from ._jenv import JB_Env

        try:
            _, jenv = self.attachThread()
        except jni.JNIException as exc:
            raise RuntimeError("Failed to attach to current thread. "
                               "Return code = {}".format(exc.getError()))
        env = JB_Env()
        env.env = jenv
        return env

    def attach_as_daemon(self):

        from ._jenv import JB_Env

        try:
            _, jenv = self.attachThread(daemon=True)
        except jni.JNIException as exc:
            raise RuntimeError("Failed to attach to current thread. "
                               "Return code = {}".format(exc.getError()))
        env = JB_Env()
        env.env = jenv
        return env

    def detach(self):

        try:
            self.detachThread()
        except jni.JNIException as exc:
            pass

    def destroy(self):

        if self.vm:
            StopVM(self.vm)
        self._jvm = None
