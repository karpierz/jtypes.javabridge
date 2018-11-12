# Copyright (c) 2014-2018, Adam Karpierz
# Licensed under the BSD license
# http://opensource.org/licenses/BSD-3-Clause

from __future__ import absolute_import

import gc
import inspect
import logging
import os
import threading
import traceback
import re
import subprocess
import uuid
import weakref
import sys
try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

from ..jvm.lib.compat import PY2, PY3
from ..jvm.lib import annotate
from ..jvm.lib import public
from ..jvm.lib import platform
from ..        import jni

if PY3: long = int
unicode = type(u"")

from ._jvm    import get_jvm, get_jenv
from ._jclass import JB_Class, JB_Object

from .__config__ import config

logger = logging.getLogger(__name__)


class JavaError(ValueError):

    """An error caused by using the Javabridge incorrectly"""

    def __init__(self, message=None):
        super(JavaError,self).__init__(message)


class JVMNotFoundError(JavaError):

    """Failed to find The Java Runtime Environment"""

    def __init__(self):
        message = "Can't find the Java Virtual Machine"
        super(JVMNotFoundError, self).__init__(message)


class JavaException(Exception):

    """Represents a Java exception thrown inside the JVM"""

    def __init__(self, throwable):

        jvm  = get_jvm()
        jenv = get_jenv()

        jenv.exception_describe()
        if isinstance(throwable, jni.Throwable):
            cause = throwable.getCause()
            cause = jvm.JObject(jenv.env, cause) if cause else None
            self.throwable = jenv._make_jb_object(cause) if cause else None
        else:
            self.throwable = throwable

        try:
            if self.throwable is None:
                raise ValueError("Tried to create a JavaException "
                                 "but there was no current exception")

            # The following has to be done by hand because the exception can't be
            # cleared at this point

            jbclass   = jenv.get_object_class(self.throwable)
            method_id = jenv.get_method_id(jbclass, 'getMessage', '()Ljava/lang/String;')
            del jbclass
            if method_id is not None:
                message = jenv.call_method(self.throwable, method_id)
                if message is not None:
                    message = jenv.get_string_utf(message)
                    super(JavaException, self).__init__(message)
        finally:
            jenv.exception_clear()

    @classmethod
    def __exception__(cls, jexc):

        # jexc: jt.jvm.JException
        return cls(jni.Throwable(jexc.handle))


def _find_jvm():

    jvm_dir = None
    if platform.is_windows or platform.is_osx:
        from ._platform import JVMFinder
        jvm_dir = JVMFinder().find_jvm()
        if jvm_dir is None:
            raise JVMNotFoundError()
    return jvm_dir

if platform.is_windows:
    # Need to fix up executable path to pick up jvm.dll
    # Also need path to JAVA_HOME\bin in order to find msvcr...
    from ._platform import JVMFinder
    os.environ["PATH"] += os.pathsep + _find_jvm() + os.pathsep + \
                          os.path.join(JVMFinder().find_javahome(), "bin")
    del JVMFinder
elif platform.is_osx:
    # Has side-effect of preloading dylibs
    from ._platform import JVMFinder
    JVMFinder().find_jvm()
    del JVMFinder


__dead_event           = threading.Event()
__kill                 = [False]
__main_thread_closures = []
__run_headless         = False
__start_thread         = None


class AtExit(object):

    '''\
    AtExit runs a function as the main thread exits from the __main__ function

    We bind a reference to self to the main frame's locals. When
    the frame exits, "__del__" is called and the function runs. This is an
    alternative to "atexit" which only runs when all threads die.
    '''
    def __init__(self, fn):
        self.fn = fn
        stack = inspect.stack()
        for f, filename, lineno, module_name, code, index in stack:
            if (module_name == '<module>' and
                f.f_locals.get("__name__") == "__main__"):
                f.f_locals["X" + uuid.uuid4().hex] = self
                break

    def __del__(self):
        self.fn()

class vm(object):

    def __init__(self, *args, **kwds):

        self.args = args
        self.kwds = kwds

    def __enter__(self):

        start_vm(*self.args, **self.kwds)

    def __exit__(self, *exc_info):

        del exc_info
        kill_vm()

def start_vm(args=None, class_path=None, max_heap_size=None, run_headless=False):

    '''
    Start the Java Virtual Machine.

    :param args: a list of strings, encoding arbitrary startup options
      for the VM. In particular, strings on the form
      ``"-D<name>=<value>"`` are used to set Java system
      properties. For other startup options, see `"The Invocation API"
      <http://docs.oracle.com/javase/6/docs/technotes/guides/jni/spec/invocation.html>`_.
      Options that set the class path (``-cp``, ``-classpath``, and ``-Djava.class.path``)
      are not allowed here; instead, use the `class_path` keyword argument.

    :param class_path: a list of strings constituting a class search
      path. Each string can be a directory, JAR archive, or ZIP
      archive. The default value, `None`, causes the class path in
      ``jt.javabridge.JARS`` to be used.

    :param max_heap_size: string that specifies the maximum size, in
      bytes, of the memory allocation pool. This value must be a multiple
      of 1024 greater than 2MB. Append the letter k or K to indicate
      kilobytes, or m or M to indicate megabytes.

    :param run_headless: if true, set the ``java.awt.headless`` Java
      property. See `"Using Headless Mode in the Java SE Platform"
      <http://www.oracle.com/technetwork/articles/javase/headless-136834.html>`_.

    :throws: :py:exc:`jt.javabridge.JVMNotFoundError`

    '''

    if args is None: args = []

    # Put this before the _vm check so the unit test can test it even
    # though the JVM is already started.
    if '-cp' in args or '-classpath' in args or any(arg.startswith('-Djava.class.path=') for arg in args):
        raise ValueError("Cannot set Java class path in the \"args\" argument to start_vm. "
                         "Use the class_path keyword argument to javabridge.start_vm instead.")

    _find_jvm()
    if get_jvm().is_active(): return

    start_event = threading.Event()

    if class_path is None:
        from . import JARS as class_path
    if len(class_path) > 0:
        args.append("-Djava.class.path=" + os.pathsep.join(class_path))
    if max_heap_size:
        args.append("-Xmx" + max_heap_size)

    def start_thread(args=args, run_headless=run_headless):

        from ._jvm import set_thread_local, wait_for_wake_event, reap

        global __i_am_the_main_thread
        global __dead_event
        global __kill
        global __main_thread_closures
        global __run_headless

        args = list(args)
        if run_headless:
            __run_headless = True
            args += [r"-Djava.awt.headless=true"]

        logger.debug("Creating JVM object")
        set_thread_local("is_main_thread", True)

        jvm = get_jvm()

        # We get local copies here and bind them in a closure to guarantee
        # that they exist past atexit.

        try:
            if platform.is_osx:
                jenv = jvm.create_mac(args)
            else:
                jenv = jvm.create(args)
            init_context_class_loader()
        except:
            traceback.print_exc()
            logger.error("Failed to create Java VM")
            return
        finally:
            logger.debug("Signalling caller")
            start_event.set()

        while True:
            wait_for_wake_event()
            reap()
            while __main_thread_closures:
                __main_thread_closures.pop()()
            if __kill[0]:
                break

        if platform.is_osx:
            # Torpedo the main thread RunnableQueue
            from ._jvm import jb_detach
            rqclass = jenv.find_class("org/cellprofiler/runnablequeue/RunnableQueue")
            stop_id = jenv.get_static_method_id(rqclass, "stop", "()V")
            jenv.call_static_method(rqclass, stop_id)
            jb_detach()
        else:
            jvm.destroy()
        __dead_event.set()

    global __start_thread

    __start_thread = threading.Thread(target=start_thread)
    __start_thread.setName("JVMMonitor")
    __start_thread.start()
    start_event.wait()

    if not get_jvm().is_active():
        raise RuntimeError("Failed to start Java VM")

    attach()

def unwrap_javascript(o):

    '''Unwrap an object such as NativeJavaObject

    :param o: an object, possibly implementing org.mozilla.javascript.Wrapper

    :returns: result of calling the wrapper's unwrap method if a wrapper,
              otherwise the unboxed value for boxed types such as
              java.lang.Integer, and if not boxed, return the Java object.
    '''
    if is_instance_of(o, "org/mozilla/javascript/Wrapper"):
        o = call(o, "unwrap", "()Ljava/lang/Object;")
    if not isinstance(o, JB_Object):
        return o
    for class_name, method, sig in (
        ("java/lang/Boolean", "booleanValue", "()Z"),
        ("java/lang/Byte",    "byteValue",    "()B"),
        ("java/lang/Integer", "intValue",     "()I"),
        ("java/lang/Long",    "longValue",    "()L"),
        ("java/lang/Float",   "floatValue",   "()F"),
        ("java/lang/Double",  "doubleValue",  "()D")):
        if is_instance_of(o, class_name):
            return call(o, method, sig)
    return o

def run_script(script, bindings_in={}, bindings_out={}, class_loader=None):

    '''Run a piece of JavaScript code.

    :param script: script to run
    :type script: string

    :param bindings_in: global variable names and values to assign to them.
    :type bindings_in: dict

    :param bindings_out: a dictionary for returning variables. The
                         keys should be global variable names. After
                         the script has run, the values of these
                         variables will be assigned to the appropriate
                         value slots in the dictionary. For instance,
                         ``bindings_out = dict(foo=None)`` to get the
                         value for the "foo" variable on output.

    :param class_loader: class loader for scripting context

    :returns: the object that is the result of the evaluation.
    '''

    context = static_call("org/mozilla/javascript/Context", "enter",
                          "()Lorg/mozilla/javascript/Context;")
    try :
        if class_loader is not None:
            call(context, "setApplicationClassLoader",
                 "(Ljava/lang/ClassLoader;)V", class_loader)
        scope = make_instance("org/mozilla/javascript/ImporterTopLevel",
                              "(Lorg/mozilla/javascript/Context;)V",
                              context)
        for k, v in bindings_in.items():
            call(scope, "put",
                 "(Ljava/lang/String;Lorg/mozilla/javascript/Scriptable;Ljava/lang/Object;)V",
                 k, scope, v)
        result = call(context, "evaluateString",
                      "(Lorg/mozilla/javascript/Scriptable;"
                      "Ljava/lang/String;"
                      "Ljava/lang/String;"
                      "I"
                      "Ljava/lang/Object;)"
                      "Ljava/lang/Object;",
                      scope, script, "<java-python-bridge>", 0, None)
        result = unwrap_javascript(result)
        for k in list(bindings_out):
            bindings_out[k] = unwrap_javascript(call(scope, "get",
                                                     "(Ljava/lang/String;"
                                                     "Lorg/mozilla/javascript/Scriptable;)"
                                                     "Ljava/lang/Object;",
                                                     k, scope))
    except JavaException as e:
        if is_instance_of(e.throwable, "org/mozilla/javascript/WrappedException"):
            raise JavaException(call(e.throwable, "unwrap", "()Ljava/lang/Object;"))
        else:
            raise e
    finally:
        static_call("org/mozilla/javascript/Context", "exit", "()V")
    return result


def get_future_wrapper(o, fn_post_process=None):

    '''
    Wrap a ``java.util.concurrent.Future`` as a class.

    :param o: the object implementing the Future interface

    :param fn_post_process: a post-processing function to run on the object returned
                      from ``o.get()``. If you have ``Future<T>``, this can apply
                      the appropriate wrapper for ``T`` so you get back a
                      wrapped class of the appropriate type.
    '''
    class Future(object):

        def __init__(self):
            self.o = o

        run     = make_method("run",    "()V")
        cancel  = make_method("cancel", "(Z)Z")
        raw_get = make_method("get",    "()Ljava/lang/Object;",
                                        "Waits if necessary for the computation to complete, "
                                        "and then retrieves its result.",
                                        fn_post_process=fn_post_process)
        if platform.is_osx:
            get = lambda self: mac_get_future_value(self)
        else:
            get = raw_get
        isCancelled = make_method("isCancelled", "()Z")
        isDone      = make_method("isDone",      "()Z")

    return Future()

def make_future_task(runnable_or_callable, result=None, fn_post_process=None):

    '''Make an instance of ``java.util.concurrent.FutureTask``.

    :param runnable_or_callable: either a
                           ``java.util.concurrent.Callable`` or a
                           ``java.lang.Runnable`` which is wrapped inside
                           the ``Future``

    :param result: if a ``Runnable``, this is the result that is returned
                   by ``Future.get``.

    :param fn_post_process: a postprocessing function run on the
                            result of ``Future.get``.


    Example: Making a future task from a Runnable:

    >>> future = javabridge.make_future_task(
            javabridge.run_script("new java.lang.Runnable() { run: function() {}};"),
            11)
    >>> future.run()
    >>> javabridge.call(future.get(), "intValue", "()I")
    11

    Example: Making a future task from a Callable:

    >>> callable = javabridge.run_script("""
            new java.util.concurrent.Callable() {
                call: function() { return 2+2; }};""")
    >>> future = javabridge.make_future_task(callable,
            fn_post_process=jutil.unwrap_javascript)
    >>> future.run()
    >>> future.get()
    4

    '''
    if is_instance_of(runnable_or_callable, 'java/util/concurrent/Callable'):
        o = make_instance('java/util/concurrent/FutureTask',
                          '(Ljava/util/concurrent/Callable;)V',
                          runnable_or_callable)
    else:
        o = make_instance('java/util/concurrent/FutureTask',
                          '(Ljava/lang/Runnable;Ljava/lang/Object;)V',
                          runnable_or_callable, result)
    return get_future_wrapper(o, fn_post_process)

def execute_runnable_in_main_thread(runnable, synchronous=False):

    """
    Execute a runnable on the main thread

    :param runnable: a Java object implementing ``java.lang.Runnable``.

    :param synchronous: ``True`` if we should wait for the runnable to finish.

    Hint: to make a runnable using JavaScript::

        return new java.lang.Runnable() {
            run: function() {
                <do something here>
            }
        };

    """
    if platform.is_osx:
        # Assumes that RunnableQueue has been deployed on the main thread
        if synchronous:
            future = make_future_task(runnable)
            execute_future_in_main_thread(future)
        else:
            static_call("org/cellprofiler/runnablequeue/RunnableQueue", "enqueue",
                        "(Ljava/lang/Runnable;)V",
                        runnable)
    else:
        run_in_main_thread(lambda: call(runnable, "run", "()V"), synchronous)

def execute_future_in_main_thread(future):

    """
    Execute a Future in the main thread

    :param future: a future, wrapped by :py:func:`jt.javabridge.get_future_wrapper`

    Synchronize with the return, running the event loop.

    """
    if platform.is_osx:
        logger.debug("Enqueueing future on runnable queue")
        static_call("org/cellprofiler/runnablequeue/RunnableQueue", "enqueue",
                    "(Ljava/lang/Runnable;)V", future.o)
        return mac_get_future_value(future)
    else:
        run_in_main_thread(future.run, True)
        return future.get()

def mac_get_future_value(future):

    '''Do special event loop processing to wait for future done on OS/X

    We need to run the event loop in OS/X while waiting for the
    future to come done to keep the UI event loop alive for message
    processing.
    '''
    from ._jvm import mac_is_main_thread

    global __run_headless

    if __run_headless:
        return future.raw_get()

    if not platform.is_32bit:
        if mac_is_main_thread():
            # Haven't figured out how to run a modal event loop on OS/X
            # - tried CFRunLoopInMode with 1/4 sec timeout and it never returned.
            raise NotImplementedError("No support for synchronizing futures in Python's "
                                      "startup thread on the OS/X in 64-bit mode.")
        return future.raw_get()

    import wx
    import time
    app = wx.GetApp()
    synchronize_without_event_loop = ((app is None and not __run_headless) or
                                      not mac_is_main_thread())
    if synchronize_without_event_loop:
        logger.debug("Synchronizing without event loop")
        # There could be a deadlock between the GIL being taken
        # by the execution of Future.get() and AWT needing WX to
        # run the event loop. Therefore, we poll before getting.
        while not future.isDone():
            logger.debug("Future is not done")
            time.sleep(.1)
        return future.raw_get()
    elif app is None:
        # So sad - start some GUI if we need it.
        app = wx.PySimpleApp(True)
    if app.IsMainLoopRunning():
        evtloop = wx.EventLoop()
        logger.debug("Polling for future done within main loop")
        while not future.isDone():
            logger.debug("Future is not done")
            if evtloop.Pending():
                while evtloop.Pending():
                    logger.debug("Processing pending event")
                    evtloop.Dispatch()
            else:
                logger.debug("No pending wx event, run Dispatch anyway")
                evtloop.Dispatch()
            logger.debug("Sleeping")
            time.sleep(.1)
    else:
        logger.debug("Polling for future while running main loop")
        class EventLoopTimer(wx.Timer):

            def __init__(self, func):
                self.func = func
                wx.Timer.__init__(self)

            def Notify(self):
                self.func()

        class EventLoopRunner(object):

            def __init__(self, fn):
                self.fn = fn

            def Run(self, time):
                self.evtloop = wx.EventLoop()
                self.timer = EventLoopTimer(self.check_fn)
                self.timer.Start(time)
                self.evtloop.Run()

            def check_fn(self):
                if self.fn():
                    self.timer.Stop()
                    self.evtloop.Exit()
        event_loop_runner = EventLoopRunner(lambda: future.isDone())
        event_loop_runner.Run(time=10)
    logger.debug("Fetching future value")
    return future.raw_get()

def execute_callable_in_main_thread(jcallable):

    """
    Execute a callable on the main thread, returning its value

    :param jcallable: a Java object implementing ``java.util.concurrent.Callable``

    :returns: the result of evaluating the callable's "call" method in the
              main thread.

    Hint: to make a callable using JavaScript::

        var my_import_scope = new JavaImporter(java.util.concurrent.Callable);
        with (my_import_scope) {
            return new Callable() {
                call: function {
                    <do something that produces result>
                    return result;
                }
            };

    """
    if platform.is_osx:
        # Assumes that RunnableQueue has been deployed on the main thread
        future = make_instance("java/util/concurrent/FutureTask",
                               "(Ljava/util/concurrent/Callable;)V",
                               jcallable)
        return execute_future_in_main_thread(future)
    else:
        return run_in_main_thread(lambda: call(jcallable, "call", "()Ljava/lang/Object;"), True)

def run_in_main_thread(closure, synchronous):

    '''Run a closure in the main Java thread

    :param closure: a callable object (eg lambda : print("hello, world"))
    :param synchronous: True to wait for completion of execution

    '''
    from ._jvm import get_thread_local, set_wake_event

    if get_thread_local("is_main_thread", False):
        return closure()

    global __main_thread_closures

    if synchronous:
        done_event = threading.Event()
        done_event.clear()
        result    = [None]
        exception = [None]
        def synchronous_closure():
            try:
                result[0] = closure()
            except Exception as exc:
                logger.exception("Caught exception when executing closure")
                exception[0] = exc
            done_event.set()
        __main_thread_closures.append(synchronous_closure)
        set_wake_event()
        done_event.wait()
        if exception[0] is not None:
            raise exception[0]
        return result[0]
    else:
        __main_thread_closures.append(closure)
        set_wake_event()
        return None

def print_all_stack_traces():

    thread_map   = static_call("java/lang/Thread", "getAllStackTraces", "()Ljava/util/Map;")
    stack_traces = call(thread_map,   "values",  "()Ljava/util/Collection;")
    sta          = call(stack_traces, "toArray", "()[Ljava/lang/Object;")

    jenv = get_jenv()

    stal = jenv.get_object_array_elements(sta)
    for stak in stal:
        stakes = jenv.get_object_array_elements(stak)
        for stake in stakes:
            print(to_string(stake))

__awt_is_active = False

def activate_awt():

    """Make a trivial AWT call in order to force AWT to initialize."""

    global __awt_is_active
    if     __awt_is_active: return
    execute_runnable_in_main_thread(run_script("""
       new java.lang.Runnable() {
           run: function() {
               java.awt.Color.BLACK.toString();
           }
       };"""), True)
    __awt_is_active = True

def deactivate_awt():

    """Close all AWT windows."""

    global __awt_is_active
    if not __awt_is_active: return
    execute_runnable_in_main_thread(run_script("""
       new java.lang.Runnable() {
           run: function() {
               var all_frames = java.awt.Frame.getFrames();
               if ( all_frames ) {
                   for ( idx in all_frames ) {
                       try {
                           all_frames[idx].dispose();
                       }
                       catch ( err ) {
                       }
                   }
               }
           }
       };"""), True)
    __awt_is_active = False

def kill_vm():

    """Kill the JVM. Once it is killed, it cannot be restarted."""

    from ._jvm import get_thread_local, set_wake_event

    if not get_jvm().is_active(): return

    global __dead_event
    global __kill
    global __start_thread

    deactivate_awt()
    gc.collect()
    while get_thread_local("attach_count", 0) > 0:
        detach()
    __kill[0] = True
    set_wake_event()
    __dead_event.wait()
    __start_thread.join()

def get_env():

    """Return the thread's environment"""

    return get_jenv()

def attach():

    """Attach to the VM, receiving the thread's environment"""

    from ._jvm import get_thread_local, set_thread_local, jb_attach

    attach_count = get_thread_local("attach_count", 0)
    set_thread_local("attach_count", attach_count + 1)
    if attach_count == 0:
        jb_attach()
        init_context_class_loader()
    return get_jenv()

def detach():

    """Detach from the VM, releasing the thread's environment"""

    from ._jvm import get_thread_local, set_thread_local, jb_detach

    attach_count = get_thread_local("attach_count", 0)
    assert attach_count > 0
    set_thread_local("attach_count", attach_count - 1)
    attach_count -= 1
    if attach_count == 0:
        jb_detach()

def init_context_class_loader():

    """
    Set the thread's context class loader to the system class loader

    When Java starts, as opposed to the JVM, the thread context class loader
    is set to the system class loader. When you start the JVM, the context
    class loader is null. This initializes the context class loader
    for a thread, if null.

    """
    jvm = get_jvm()

    current_thread = jvm.JThread.currentThread()
    class_loader   = current_thread.getContextClassLoader()
    if class_loader is None:
        class_loader = jvm.JClassLoader.getSystemClassLoader()
        current_thread.setContextClassLoader(class_loader)


def is_instance_of(jbobject, class_name):

    '''Return True if object is instance of class'''

    if not isinstance(jbobject, JB_Object):
        return False

    jenv = get_jenv()

    jbclass = jenv.find_class(class_name)
    return jenv.is_instance_of(jbobject, jbclass)


def make_call(obj, method_name, sig):

    '''Create a function that calls a method'''

    assert obj is not None

    jenv = get_jenv()

    bind = not isinstance(obj, (str, unicode))
    jbclass   = jenv.get_object_class(obj) if bind else jenv.find_class(obj)
    method_id = jenv.get_method_id(jbclass, method_name, sig)
    del jbclass
    if method_id is None:
        raise JavaError('Could not find method name = "{}" with signature = "{}"'.format(
                        method_name, sig))
    if bind:
        def fn(*args):
            return jenv.call_method(obj, method_id, *args)
    else:
        def fn(obj, *args):
            return jenv.call_method(obj, method_id, *args)

    return fn


def make_static_call(class_name, method_name, sig):

    '''Create a function that performs a call of a static method'''

    jenv = get_jenv()

    jbclass   = jenv.find_class(class_name)
    method_id = jenv.get_static_method_id(jbclass, method_name, sig)
    if method_id is None:
        raise JavaError('Could not find method name = "{}" with signature = "{}"'.format(
                        method_name, sig))
    def fn(*args):
        return jenv.call_static_method(jbclass, method_id, *args)

    return fn


def call(obj, method_name, sig, *args):

    """Call a method on an object"""

    fn = make_call(obj, method_name, sig)
    args_sigs, ret_sig = _split_method_sig(sig)
    nice_args = _get_nice_args(args, args_sigs)
    result = fn(*nice_args)
    return get_nice_result(result, ret_sig)


def static_call(class_name, method_name, sig, *args):

    """Call a static method on a class"""

    fn = make_static_call(class_name, method_name, sig)
    args_sigs, ret_sig = _split_method_sig(sig)
    nice_args = _get_nice_args(args, args_sigs)
    result = fn(*nice_args)
    return get_nice_result(result, ret_sig)


def make_method(name, sig, doc='No documentation', fn_post_process=None):

    '''
    Return a class method for the given Java class. When called,
    the method expects to find its Java instance object in ``self.o``,
    which is where ``make_new`` puts it.

    :param name: method name
    :param sig: calling signature
    :param doc: doc string to be attached to the Python method
    :param fn_post_process: a function, such as a wrapper, that transforms
                            the method output into something more useable.
    '''
    def method(self, *args):

        assert isinstance(self.o, JB_Object)
        result = call(self.o, name, sig, *args)
        if fn_post_process is not None:
            result = fn_post_process(result)
        return result

    method.__doc__ = doc
    return method


def get_static_field(klass, name, sig):

    '''
    Get the value for a static field on a class

    :param klass: the class or string name of class
    :param name:  the name of the field
    :param sig:   the signature, typically, 'I' or 'Ljava/lang/String;'

    >>> javabridge.get_static_field("java/lang/Short", "MAX_VALUE", "S")
    32767

    '''
    jenv = get_jenv()

    if isinstance(klass, JB_Object):
        klass = jenv.get_object_class(klass)
    elif not isinstance(klass, JB_Class):
        class_name = str(klass)
        klass = jenv.find_class(class_name)
    field_id = jenv.get_static_field_id(klass, name, sig)

    if   sig == 'Z': return jenv.get_static_boolean_field(klass, field_id)
    elif sig == 'B': return jenv.get_static_byte_field   (klass, field_id)
    elif sig == 'C': return jenv.get_static_char_field   (klass, field_id)
    elif sig == 'S': return jenv.get_static_short_field  (klass, field_id)
    elif sig == 'I': return jenv.get_static_int_field    (klass, field_id)
    elif sig == 'J': return jenv.get_static_long_field   (klass, field_id)
    elif sig == 'F': return jenv.get_static_float_field  (klass, field_id)
    elif sig == 'D': return jenv.get_static_double_field (klass, field_id)
    else:
        jresult = jenv.get_static_object_field(klass, field_id)
        return get_nice_result(jresult, sig)


def set_static_field(klass, name, sig, value):

    '''
    Set the value for a static field on a class

    :param klass: the class or string name of class
    :param name:  the name of the field
    :param sig:   the signature, typically, 'I' or 'Ljava/lang/String;'
    :param value: the value to set

    '''
    jenv = get_jenv()

    if isinstance(klass, JB_Object):
        klass = jenv.get_object_class(klass)
    elif not isinstance(klass, JB_Class):
        class_name = str(klass)
        klass = jenv.find_class(class_name)
    field_id = jenv.get_static_field_id(klass, name, sig)

    if   sig == 'Z': jenv.set_static_boolean_field(klass, field_id, value)
    elif sig == 'B': jenv.set_static_byte_field   (klass, field_id, value)
    elif sig == 'C': jenv.set_static_char_field   (klass, field_id, value)
    elif sig == 'S': jenv.set_static_short_field  (klass, field_id, value)
    elif sig == 'I': jenv.set_static_int_field    (klass, field_id, value)
    elif sig == 'J': jenv.set_static_long_field   (klass, field_id, value)
    elif sig == 'F': jenv.set_static_float_field  (klass, field_id, value)
    elif sig == 'D': jenv.set_static_double_field (klass, field_id, value)
    else:
        jobject = get_nice_arg(value, sig)
        jenv.set_static_object_field(klass, field_id, jobject)


def get_field(obj, field_name, sig):

    """Get the value for a field on an object"""

    assert isinstance(obj, JB_Object)

    jenv = get_jenv()

    jbclass  = jenv.get_object_class(obj)
    field_id = jenv.get_field_id(jbclass, field_name, sig)
    del jbclass

    if   sig == 'Z': return jenv.get_boolean_field(obj, field_id)
    elif sig == 'B': return jenv.get_byte_field   (obj, field_id)
    elif sig == 'C': return jenv.get_char_field   (obj, field_id)
    elif sig == 'S': return jenv.get_short_field  (obj, field_id)
    elif sig == 'I': return jenv.get_int_field    (obj, field_id)
    elif sig == 'J': return jenv.get_long_field   (obj, field_id)
    elif sig == 'F': return jenv.get_float_field  (obj, field_id)
    elif sig == 'D': return jenv.get_double_field (obj, field_id)
    else:
        jresult = jenv.get_object_field(obj, field_id)
        return get_nice_result(jresult, sig)


def set_field(obj, field_name, sig, value):

    """Set the value for a field on an object"""

    assert isinstance(obj, JB_Object)

    jenv = get_jenv()

    jbclass  = jenv.get_object_class(obj)
    field_id = jenv.get_field_id(jbclass, field_name, sig)
    del jbclass

    if   sig == 'Z': jenv.set_boolean_field(obj, field_id, value)
    elif sig == 'B': jenv.set_byte_field   (obj, field_id, value)
    elif sig == 'C': jenv.set_char_field   (obj, field_id, value)
    elif sig == 'S': jenv.set_short_field  (obj, field_id, value)
    elif sig == 'I': jenv.set_int_field    (obj, field_id, value)
    elif sig == 'J': jenv.set_long_field   (obj, field_id, value)
    elif sig == 'F': jenv.set_float_field  (obj, field_id, value)
    elif sig == 'D': jenv.set_double_field (obj, field_id, value)
    else:
        jobject = get_nice_arg(value, sig)
        jenv.set_object_field(obj, field_id, jobject)


def _split_method_sig(sig):

    arg_end  = sig.find(')')
    args_sig = sig[1:arg_end]
    args_sigs = []
    while args_sig:
        match = re.match(r"\[*(?:[ZBCSIJFD]|L[^;]+;)", args_sig)
        if match is None:
            raise ValueError("Invalid signature: {}".format(sig))
        args_sigs.append(match.group())
        args_sig = args_sig[match.end():]
    ret_sig   = sig[arg_end+1:]
    return args_sigs, ret_sig

def _get_nice_args(args, sigs):

    """Convert arguments to Java types where appropriate"""

    return [get_nice_arg(arg, sig) for arg, sig in zip(args, sigs)]

def get_nice_arg(arg, sig):

    '''Convert an argument into a Java type when appropriate.'''

    jenv = get_jenv()

    is_java = isinstance(arg, (JB_Object, JB_Class))
    if sig[0] == 'L' and not is_java:
        # Check for the standard packing of java objects into class instances
        if hasattr(arg, "o"):
            return arg.o

    # If asking for an object, try converting basic types into Java-wraps
    # of Java basic types

    if sig == 'Ljava/lang/Integer;'   and type(arg) in (int, long, bool):
        return make_instance('java/lang/Integer', '(I)V', int(arg))
    elif sig == 'Ljava/lang/Long'     and type(arg) in (int, long, bool):
        return make_instance('java/lang/Long',    '(J)V', long(arg))
    elif sig == 'Ljava/lang/Boolean;' and type(arg) in (int, long, bool):
        return make_instance('java/lang/Boolean', '(Z)V', bool(arg))
    elif sig == 'Ljava/lang/Object;'  and isinstance(arg, bool):
        return make_instance('java/lang/Boolean', '(Z)V', arg)
    elif sig == 'Ljava/lang/Object;'  and isinstance(arg, int):
        return make_instance('java/lang/Integer', '(I)V', arg)
    elif sig == 'Ljava/lang/Object;'  and isinstance(arg, long):
        return make_instance('java/lang/Long',    '(J)V', arg)
    elif sig == 'Ljava/lang/Object;'  and isinstance(arg, float):
        return make_instance('java/lang/Double',  '(D)V', arg)
    elif sig in ('Ljava/lang/String;','Ljava/lang/Object;') and not isinstance(arg, JB_Object):
        if arg is None:
            return None
        else:
            if PY2 and isinstance(arg, str):
                arg = arg.decode("utf-8")
            return jenv.new_string_utf(arg)
    elif config.getboolean("NUMPY_ENABLED", True) and np and isinstance(arg, np.ndarray):
        if sig == '[Z':
            return jenv.make_boolean_array(np.ascontiguousarray(arg.flatten(), np.bool8))
        elif sig == '[B':
            return jenv.make_byte_array(np.ascontiguousarray(arg.flatten(), np.ubyte))
        elif sig == '[S':
            return jenv.make_short_array(np.ascontiguousarray(arg.flatten(), np.int16))
        elif sig == '[I':
            return jenv.make_int_array(np.ascontiguousarray(arg.flatten(), np.int32))
        elif sig == '[J':
            return jenv.make_long_array(np.ascontiguousarray(arg.flatten(), np.int64))
        elif sig == '[F':
            return jenv.make_float_array(np.ascontiguousarray(arg.flatten(), np.float32))
        elif sig == '[D':
            return jenv.make_double_array(np.ascontiguousarray(arg.flatten(), np.float64))
    elif sig.startswith('L') and sig.endswith(';') and not is_java:
        # Desperately try to make an instance of it with an integer constructor
        if isinstance(arg, (int, long, bool)):
            return make_instance(sig[1:-1], '(I)V', int(arg))
        elif isinstance(arg, (str, unicode)):
            return make_instance(sig[1:-1], '(Ljava/lang/String;)V', arg)
    elif sig.startswith('[L') and (not is_java) and hasattr(arg, '__iter__'):
        objs = [get_nice_arg(subarg, sig[1:]) for subarg in arg]
        k = jenv.find_class(sig[2:-1])
        a = jenv.make_object_array(len(objs), k)
        for i, obj in enumerate(objs):
            jenv.set_object_array_element(a, i, obj)
        return a
    return arg

def get_nice_result(result, sig):

    '''Convert a result that may be a java object into a string'''

    if result is None:
        return None

    jenv = get_jenv()

    if (sig == 'Ljava/lang/String;' or
        sig == 'Ljava/lang/Object;' and is_instance_of(result, "java/lang/String")):
        return jenv.get_string_utf(result)
    elif sig == 'Ljava/lang/Integer;':
        return call(result, 'intValue', '()I')
    elif sig == 'Ljava/lang/Long':
        return call(result, 'longValue', '()J')
    elif sig == 'Ljava/lang/Boolean;':
        return call(result, 'booleanValue', '()Z')
    elif config.getboolean("NUMPY_ENABLED", True) and np and sig == '[B':
        # Convert a byte array into a numpy array
        return jenv.get_byte_array_elements(result)
    elif isinstance(result, JB_Object):
        # Do longhand to prevent recursion
        rklass = jenv.get_object_class(result)
        m = jenv.get_method_id(rklass, 'getClass', '()Ljava/lang/Class;')
        del rklass
        rclass  = jenv.call_method(result, m)
        rkklass = jenv.get_object_class(rclass)
        m = jenv.get_method_id(rkklass, 'isPrimitive', '()Z')
        del rkklass
        is_primitive = jenv.call_method(rclass, m)
        if is_primitive:
            rc = get_class_wrapper(rclass, True)
            classname = rc.getCanonicalName()
            if classname == 'boolean':
                return to_string(result) == 'true'
            elif classname in ('int', 'byte', 'short', 'long'):
                return int(to_string(result))
            elif classname in ('float', 'double'):
                return float(to_string(result))
            elif classname == 'char':
                return to_string(result)
    return result

def to_string(jobject):

    """
    Call the toString method on any object.

    :returns: the string representation of the object as a Python string

    >>> jstring = javabridge.get_env().new_string_utf("Hello, world")
    >>> jstring
    <Java object at 0x55116e0>
    >>> javabridge.to_string(jstring)
    u'Hello, world'

    """
    if isinstance(jobject, JB_Object):
        return jobject._jobject.toString()
    else:
        return str(jobject)

def box(value, klass):

    """
    Given a Java class and a value, convert the value to an instance of it

    value - value to be converted
    klass - return an object of this class, given the value.

    """
    wclass = get_class_wrapper(klass, True)
    name   = wclass.getCanonicalName()
    if wclass.isPrimitive():
        if   name == "int":     return make_instance("java/lang/Integer",   "(I)V", value)
        elif name == "boolean": return make_instance("java/lang/Boolean",   "(Z)V", value)
        elif name == "byte":    return make_instance("java/lang/Byte",      "(B)V", value)
        elif name == "char":    return make_instance("java/lang/Character", "(C)V", value)
        elif name == "short":   return make_instance("java/lang/Short",     "(S)V", value)
        elif name == "long":    return make_instance("java/lang/Long",      "(J)V", value)
        elif name == "float":   return make_instance("java/lang/Float",     "(F)V", value)
        elif name == "double":  return make_instance("java/lang/Double",    "(D)V", value)
        else:
            raise NotImplementedError("Boxing {} is not implemented".format(name))
    else:
        return get_nice_arg(value, "L{};".format(name.replace(".", "/")))

def get_collection_wrapper(collection, fn_wrapper=None):

    '''Return a wrapper of ``java.util.Collection``

    :param collection: an object that implements
                 ``java.util.Collection``. If the object implements the
                 list interface, that is wrapped as well

    :param fn_wrapper: if defined, a function that wraps a Java object

    The returned value is a Python object, duck-typed as a sequence. Items
    can be retrieved by index or by slicing. You can also iterate through
    the collection::

        for o in get_collection_wrapper(jobject):
            # do something

    If you supply a function wrapper, indexing and iteration operations
    will return the result of calling the function wrapper on the objects
    in the collection::

        for d in get_collection_wrapper(list_of_hashmaps, get_map_wrapper):
            # a map wrapper on the hashmap is returned
            print(d["Foo"])

    '''
    class Collection(object):

        def __init__(self):
            self.o = collection

        add         = make_method("add",         "(Ljava/lang/Object;)Z")
        addAll      = make_method("addAll",      "(Ljava/util/Collection;)Z")
        clear       = make_method("clear",       "()V")
        contains    = make_method("contains",    "(Ljava/lang/Object;)Z")
        containsAll = make_method("containsAll", "(Ljava/util/Collection;)Z")
        isEmpty     = make_method("isEmpty",     "()Z")
        iterator    = make_method("iterator",    "()Ljava/util/Iterator;")
        remove      = make_method("remove",      "(Ljava/lang/Object;)Z")
        removeAll   = make_method("removeAll",   "(Ljava/util/Collection;)Z")
        retainAll   = make_method("retainAll",   "(Ljava/util/Collection;)Z")
        size        = make_method("size",        "()I")
        toArray     = make_method("toArray",     "()[Ljava/lang/Object;",
                                  fn_post_process=get_jenv().get_object_array_elements)
        toArrayC    = make_method("toArray",     "([Ljava/lang/Object;)[Ljava/lang/Object;")

        def __len__(self):
            return self.size()

        def __iter__(self):
            return iterate_collection(self.o, fn_wrapper=fn_wrapper)

        def __contains__(self, item):
            return self.contains(item)

        @staticmethod
        def is_collection(x):
            return hasattr(x, "o") and is_instance_of(x.o, "java/util/Collection")

        def __add__(self, items):
            klass = call(self.o, "getClass", "()Ljava/lang/Class;")
            copy = get_collection_wrapper(call(klass, "newInstance", "()Ljava/lang/Object;"),
                                          fn_wrapper=fn_wrapper)
            copy.addAll(self.o)
            if self.is_collection(items):
                copy.addAll(items.o)
            else:
                for item in items:
                    copy.add(item)
            return copy

        def __iadd__(self, items):
            if self.is_collection(items):
                self.addAll(items)
            else:
                for item in items:
                    self.add(item)
            return self

        if is_instance_of(collection, 'java/util/List'):

            addI        = make_method("add",         "(ILjava/lang/Object;)V")
            addAllI     = make_method("addAll",      "(ILjava/util/Collection;)Z")
            indexOf     = make_method("indexOf",     "(Ljava/lang/Object;)I")
            lastIndexOf = make_method("lastIndexOf", "(Ljava/lang/Object;)I")
            removeI     = make_method("remove",      "(I)Ljava/lang/Object;",
                                      fn_post_process=fn_wrapper)
            get         = make_method("get",         "(I)Ljava/lang/Object;",
                                      fn_post_process=fn_wrapper)
            set         = make_method("set",         "(ILjava/lang/Object;)Ljava/lang/Object;",
                                      fn_post_process=fn_wrapper)
            subList     = make_method("subList",     "(II)Ljava/util/List;",
                                      fn_post_process=lambda x: get_collection_wrapper(x, fn_wrapper))

            def __normalize_idx(self, idx, none_value):
                if idx is None:
                    return none_value
                elif idx < 0:
                    return max(0, self.size()+idx)
                elif idx > self.size():
                    return self.size()
                return idx

            def __getitem__(self, idx):
                if isinstance(idx, slice):
                    start = self.__normalize_idx(idx.start, 0)
                    stop = self.__normalize_idx(idx.stop, self.size())
                    if idx.step is None or idx.step == 1:
                        return self.subList(start, stop)
                    return [self[i] for i in range(start, stop, idx.step)]
                return self.get(self.__normalize_idx(idx, 0))

            def __setitem__(self, idx, value):
                self.set(idx, value)

            def __delitem__(self, idx):
                self.removeI(idx)

    return Collection()

array_list_add_method_id = None

def make_list(elements=[]):

    '''Make a wrapped ``java.util.ArrayList``.

    The ``ArrayList`` will contain the specified elements, if any.

    :param elements: the elements to put in the ``ArrayList``.

    Examples::
        >>> mylist = make_list(["Hello", "World", 2])
        >>> print("\\n".join([to_string(o) for o in mylist]))
        Hello
        World
        2
        >>> print("{}, {}.".format(mylist[0], mylist[1].lower()))
        Hello, world.
        >>> get_class_wrapper(mylist.o)
        java.util.ArrayList
        public boolean java.util.ArrayList.add(java.lang.Object)
        public void java.util.ArrayList.add(int,java.lang.Object)
        ...
    '''
    global array_list_add_method_id

    a = get_collection_wrapper(make_instance("java/util/ArrayList", "()V"))

    jenv = get_jenv()

    if len(elements) > 0:
        if array_list_add_method_id is None:
            array_list_jbclass       = jenv.find_class("java/util/ArrayList")
            array_list_add_method_id = jenv.get_method_id(array_list_jbclass, "add",
                                                          "(Ljava/lang/Object;)Z")
        for element in elements:
            if not isinstance(element, JB_Object):
                element = get_nice_arg(element, "Ljava/lang/Object;")
            jenv.call_method(a.o, array_list_add_method_id, element)
    return a

def get_dictionary_wrapper(dictionary):

    '''
    Return a wrapper of ``java.util.Dictionary``.

    :param dictionary: Java object that implements the ``java.util.Dictionary`` interface.
    :returns: a Python instance that wraps the Java dictionary.

    >>> jproperties = javabridge.static_call("java/lang/System", "getProperties", "()Ljava/util/Properties;")
    >>> properties  = javabridge.get_dictionary_wrapper(jproperties)
    >>> properties.size()
    56

    '''
    jenv = get_jenv()

    class Dictionary(object):

        def __init__(self):
            self.o = dictionary

        size     = make_method("size",     "()I",
                                           "Returns the number of entries in this dictionary")
        isEmpty  = make_method("isEmpty",  "()Z",
                                           "Tests if this dictionary has no entries")
        keys     = make_method("keys",     "()Ljava/util/Enumeration;",
                                           "Returns an enumeration of keys in this dictionary")
        elements = make_method("elements", "()Ljava/util/Enumeration;",
                                           "Returns an enumeration of elements in this dictionary")
        get      = make_method("get",      "(Ljava/lang/Object;)Ljava/lang/Object;",
                                           "Return the value associated with a key or None if no value")
        put      = make_method("put",      "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;",
                                           "Associate a value with a key in the dictionary")
    return Dictionary()

def get_map_wrapper(o):

    '''Return a wrapper of ``java.util.Map``

    :param o: a Java object that implements the ``java.util.Map`` interface

    Returns a Python object duck typed as a dictionary.
    You can fetch values from the Java object using the Python array syntax::

        > d = get_map_wrapper(jmap)
        > d["Foo"] = "Bar"
        > print(d["Foo"])
        Bar
    '''
    assert is_instance_of(o, 'java/util/Map')

    class Map(object):

        def __init__(self):
            self.o = o

        clear         = make_method("clear",         "()V")
        containsKey   = make_method("containsKey",   "(Ljava/lang/Object;)Z")
        containsValue = make_method("containsValue", "(Ljava/lang/Object;)Z")
        entrySet      = make_method("entrySet",      "()Ljava/util/Set;")
        get           = make_method("get",           "(Ljava/lang/Object;)Ljava/lang/Object;")
        isEmpty       = make_method("isEmpty",       "()Z")
        keySet        = make_method("keySet",        "()Ljava/util/Set;")
        put           = make_method("put",           "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;")
        putAll        = make_method("putAll",        "(Ljava/util/Map;)V")
        remove        = make_method("remove",        "(Ljava/lang/Object;)Ljava/lang/Object;")
        size          = make_method("size",          "()I")
        values        = make_method("values",        "()Ljava/util/Collection;")

        def __len__(self):
            return self.size()

        def __getitem__(self, key):
            return self.get(key)

        def __setitem__(self, key, value):
            self.put(key, value)

        def __iter__(self):
            return iterate_collection(self.keySet())

        def keys(self):
            return tuple(iterate_collection(self.keySet(self)))

    return Map()

def make_map(**kwargs):

    """
    Create a wrapped ``java.util.HashMap`` from arbitrary keyword arguments.

    Example::

        > d = make_map(foo="Bar")
        > print(d["foo"])
        Bar
        > get_class_wrapper(d.o)
        java.util.HashMap
        public java.lang.Object java.util.HashMap.get(java.lang.Object)
        public java.lang.Object java.util.HashMap.put(java.lang.Object,java.lang.Object)

    """
    hashmap = get_map_wrapper(make_instance("java/util/HashMap", "()V"))
    for key, value in kwargs.items():
        hashmap[key] = value
    return hashmap

def jdictionary_to_string_dictionary(hashtable):

    '''Convert a Java dictionary to a Python dictionary.

    Convert each key and value in the Java dictionary to a string and
    construct a Python dictionary from the result.

    :param hashtable: Java object that implements the ``java.util.Hashtable`` interface.
    :returns: a Python ``dict`` with strings as keys and values

    >>> jproperties = javabridge.static_call("java/lang/System", "getProperties", "()Ljava/util/Properties;")
    >>> properties = javabridge.jdictionary_to_string_dictionary(jproperties)
    >>> properties['java.specification.vendor']
    'Sun Microsystems Inc.'

    '''
    jhashtable = get_dictionary_wrapper(hashtable)
    jkeys = jhashtable.keys()
    keys  = jenumeration_to_string_list(jkeys)
    result = {}
    for key in keys:
        result[key] = to_string(jhashtable.get(key))
    return result

def get_enumeration_wrapper(enumeration):

    '''Return a wrapper of java.util.Enumeration

    Given a JB_Object that implements java.util.Enumeration,
    return an object that wraps the class methods.

    >>> jproperties = javabridge.static_call("java/lang/System", "getProperties", "()Ljava/util/Properties;")
    >>> keys = javabridge.call(jproperties, "keys", "()Ljava/util/Enumeration;")
    >>> enum = javabridge.get_enumeration_wrapper(keys)
    >>> while enum.hasMoreElements():
    ...     if javabridge.to_string(enum.nextElement()) == 'java.vm.name':
    ...         print("Has java.vm.name")
    ...
    Has java.vm.name

    '''
    jenv = get_jenv()

    class Enumeration(object):

        def __init__(self):
            '''Call the init method with the JB_Object'''
            self.o = enumeration

        hasMoreElements = make_method('hasMoreElements', '()Z',
                                      'Return true if the enumeration has more elements to retrieve')
        nextElement     = make_method('nextElement', '()Ljava/lang/Object;')

    return Enumeration()

iterator_has_next_id = None
iterator_next_id     = None

def iterate_java(iterator, fn_wrapper=None):

    '''Make a Python iterator for a Java iterator

    >>> jiterator = javabridge.run_script("""var al = new java.util.ArrayList(); al.add("Foo"); al.add("Bar"); al.iterator()""")
    >>> [x for x in javabridge.iterate_java(jiterator)]
    [u'Foo', u'Bar']

    '''
    global iterator_has_next_id, iterator_next_id

    jenv = get_jenv()

    if not isinstance(iterator, JB_Object):
        raise JavaError("{} is not a Javabridge JB_Object".format(repr(iterator)))

    iterator_jbclass = jenv.find_class("java/util/Iterator")

    if not jenv.is_instance_of(iterator, iterator_jbclass):
        raise JavaError("{} does not implement the java.util.Iterator interface".format(
                        get_class_wrapper(iterator).getCanonicalName()))

    if iterator_has_next_id is None:
        iterator_has_next_id = jenv.get_method_id(iterator_jbclass, "hasNext", "()Z")
        iterator_next_id     = jenv.get_method_id(iterator_jbclass, "next",    "()Ljava/lang/Object;")
    while True:
        result = jenv.call_method(iterator, iterator_has_next_id)
        if not result: break
        item = jenv.call_method(iterator, iterator_next_id)
        yield item if fn_wrapper is None else fn_wrapper(item)

def iterate_collection(c, fn_wrapper=None):

    '''
    Make a Python iterator over the elements of a Java collection

    >>> al = javabridge.run_script("""var al = new java.util.ArrayList(); al.add("Foo"); al.add("Bar"); al;""")
    >>> [x for x in javabridge.iterate_java(al)]
    [u'Foo', u'Bar']

    '''
    return iterate_java(call(c, "iterator", "()Ljava/util/Iterator;"), fn_wrapper=fn_wrapper)

def jenumeration_to_string_list(enumeration):

    '''
    Convert a Java enumeration to a Python list of strings

    Convert each element in an enumeration to a string and return them
    as a Python list.

    >>> jproperties = javabridge.static_call("java/lang/System", "getProperties", "()Ljava/util/Properties;")
    >>> keys = javabridge.call(jproperties, "keys", "()Ljava/util/Enumeration;")
    >>> 'java.vm.name' in javabridge.jenumeration_to_string_list(keys)
    True

    '''
    jenumeration = get_enumeration_wrapper(enumeration)
    result = []
    while jenumeration.hasMoreElements():
        result.append(to_string(jenumeration.nextElement()))
    return result

def make_new(class_name, sig):

    '''
    Make a function that creates a new instance of the class. When
    called, the function does not return the new instance, but stores
    it at ``self.o``.

    A typical init function looks like this::

        new_fn = make_new("java/lang/Integer", '(I)V')
        def __init__(self, i):
            new_fn(i)
    '''
    def constructor(self, *args):
        self.o = make_instance(class_name, sig, *args)

    return constructor

def make_instance(class_name, sig, *args):

    '''
    Create an instance of a class

    :param class_name: name of class in foo/bar/Baz form (not foo.bar.Baz)
    :param sig: signature of constructor
    :param args: arguments to constructor

    >>> javabridge.make_instance("java/lang/Integer", "(I)V", 42)
    <Java object at 0x55116dc>

    '''
    jenv = get_jenv()

    jbclass   = jenv.find_class(class_name)
    method_id = jenv.get_method_id(jbclass, "<init>", sig)
    if method_id is None:
        raise JavaError('Could not find constructor with signature = "{}"'.format(sig))
    args_sigs = _split_method_sig(sig)[0]
    nice_args = _get_nice_args(args, args_sigs)
    return jenv.new_object(jbclass, method_id, *nice_args)

def class_for_name(classname, ldr="system"):

    '''
    Return a ``java.lang.Class`` for the given name.

    :param classname: the class name in dotted form, e.g. "java.lang.String"

    '''
    if ldr == "system":
        from ._jenv import JB_Env
        jvm  = get_jvm()
        env = JB_Env()
        jldr = jvm.JClassLoader.getSystemClassLoader()
        ldr  = env._make_jb_object(jvm.JObject(None, jldr.handle, borrowed=True))
    return static_call("java/lang/Class", "forName",
                       "(Ljava/lang/String;ZLjava/lang/ClassLoader;)Ljava/lang/Class;",
                       classname, True, ldr)

def get_class_wrapper(obj, is_class=False):

    '''Return a wrapper for an object's class (e.g., for
    reflection). The returned wrapper class will have the following
    methods:

    ``getAnnotation()``
       ``java.lang.annotation.Annotation``
    ``getAnnotations()``
       array of ``java.lang.annotation.Annotation``
    ``getCanonicalName()``
       ``java.lang.String``
    ``getClasses()``
       array of ``java.lang.Class``
    ``getContructor(signature)``
       ``java.lang.reflect.Constructor``
    ``getFields()``
       array of ``java.lang.reflect.Field``
    ``getField(field_name)``
       ``java.lang.reflect.Field``
    ``getMethods()``
       array of ``java.lang.reflect.Method``
    ``getMethod(method_name)``
       ``java.lang.reflect.Method``
    ``cast(class)``
       object
    ``isPrimitive()``
       boolean
    ``newInstance()``
       object

    '''

    if is_class:
        class_object = obj
    elif isinstance(obj, (str, unicode)):
        class_object = class_for_name(obj)
    else:
        class_object = call(obj, 'getClass', '()Ljava/lang/Class;')

    class Klass(object):

        def __init__(self):
            self.o = class_object

        getCanonicalName = make_method('getCanonicalName', '()Ljava/lang/String;',
                                                           'Returns the canonical name of the class')
        getAnnotation    = make_method('getAnnotation',    '(Ljava/lang/Class;)Ljava/lang/annotation/Annotation;',
                                                           "Returns this element's annotation if present")
        getAnnotations   = make_method('getAnnotations',   '()[Ljava/lang/annotation/Annotation;')
        getClasses       = make_method('getClasses',       '()[Ljava/lang/Class;',
                                                           'Returns an array containing Class objects representing all the public classes and interfaces that are members of the class represented by this Class object.')
        getConstructor   = make_method('getConstructor',   '([Ljava/lang/Class;)Ljava/lang/reflect/Constructor;',
                                                           'Return a constructor with the given signature')
        getConstructors  = make_method('getConstructors',  '()[Ljava/lang/reflect/Constructor;')
        getField         = make_method('getField',         '(Ljava/lang/String;)Ljava/lang/reflect/Field;')
        getFields        = make_method('getFields',        '()[Ljava/lang/reflect/Field;')
        getMethod        = make_method('getMethod',        '(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;')
        getMethods       = make_method('getMethods',       '()[Ljava/lang/reflect/Method;')
        cast             = make_method('cast',             '(Ljava/lang/Object;)Ljava/lang/Object;',
                                                           'Throw an exception if object is not castable to this class')
        isPrimitive      = make_method('isPrimitive',      '()Z',
                                                           'Return True if the class is a primitive such as boolean or int')
        newInstance      = make_method('newInstance',      '()Ljava/lang/Object;',
                                                           'Make a new instance of the object with the default constructor')
        def __repr__(self):
            jenv = get_jenv()
            methods = jenv.get_object_array_elements(self.getMethods())
            return "{}\n{}".format(self.getCanonicalName(), "\n".join([to_string(x) for x in methods]))

    return Klass()

MOD_ABSTRACT    = 'ABSTRACT'
MOD_FINAL       = 'FINAL'
MOD_INTERFACE   = 'INTERFACE'
MOD_NATIVE      = 'NATIVE'
MOD_PRIVATE     = 'PRIVATE'
MOD_PROTECTED   = 'PROTECTED'
MOD_PUBLIC      = 'PUBLIC'
MOD_STATIC      = 'STATIC'
MOD_STRICT      = 'STRICT'
MOD_SYCHRONIZED = 'SYNCHRONIZED'
MOD_TRANSIENT   = 'TRANSIENT'
MOD_VOLATILE    = 'VOLATILE'
MOD_ALL = [MOD_ABSTRACT, MOD_FINAL, MOD_INTERFACE, MOD_NATIVE,
           MOD_PRIVATE, MOD_PROTECTED, MOD_PUBLIC, MOD_STATIC,
           MOD_STRICT, MOD_SYCHRONIZED, MOD_TRANSIENT, MOD_VOLATILE]

def get_modifier_flags(modifier_flags):

    '''Parse out the modifiers from the modifier flags from getModifiers'''

    result = []
    for mod in MOD_ALL:
        if get_static_field('java/lang/reflect/Modifier', mod, 'I') & modifier_flags:
            result.append(mod)
    return result

def get_field_wrapper(field):

    '''
    Return a wrapper for the java.lang.reflect.Field class. The
    returned wrapper class will have the following methods:

    ``getAnnotation()``
       java.lang.annotation.Annotation
    ``getBoolean()``
       bool
    ``getByte``
       byte
    ``getChar``
       char
    ``getDouble``
       double
    ``getFloat``
       float
    ``getInt``
       int
    ``getShort``
       short
    ``getLong``
       long
    ``getDeclaredAnnotations()``
       array of java.lang.annotation.Annotation
    ``getGenericType``
       java.lang.reflect.Type
    ``getModifiers()``
       Python list of strings indicating the modifier flags
    ``getName()``
       java.lang.String()
    ``getType()``
       java.lang.Class()
    ``set(object, object)``
       void
    ``setBoolean(bool)``
       void
    ``setByte(byte)``
       void
    ``setChar(char)``
       void
    ``setDouble(double)``
       void
    ``setFloat(float)``
       void
    ``setInt(int)``
       void
    ``setShort(short)``
       void
    ``setLong(long)``
       void
    '''

    class Field(object):

        def __init__(self):
            self.o = field

        def getModifiers(self):
            return get_modifier_flags(call(self.o, 'getModifiers','()I'))

        getName = make_method('getName', '()Ljava/lang/String;')
        getType = make_method('getType', '()Ljava/lang/Class;')

        def getAnnotation(self, annotation_class):

            """Returns this element's annotation for the specified type

            annotation_class - find annotations of this class

            returns the annotation or None if not annotated"""

            if isinstance(annotation_class, (str, unicode)):
                annotation_class = class_for_name(annotation_class)
            return call(self.o, 'getAnnotation',
                        '(Ljava/lang/Class;)Ljava/lang/annotation/Annotation;',
                        annotation_class)

        getDeclaredAnnotations = make_method('getDeclaredAnnotations',
                                             '()[Ljava/lang/annotation/Annotation;')
        getGenericType         = make_method('getGenericType', '()Ljava/lang/reflect/Type;')

        get        = make_method('get',        '(Ljava/lang/Object;)Ljava/lang/Object;',
                                               'Returns the value of the field represented by this '
                                               'Field, on the specified object.')
        getBoolean = make_method('getBoolean', '(Ljava/lang/Object;)Z',
                                               'Read a boolean field from an object')
        getByte    = make_method('getByte',    '(Ljava/lang/Object;)B',
                                               'Read a byte field from an object')
        getChar    = make_method('getChar',    '(Ljava/lang/Object;)C')
        getShort   = make_method('getShort',   '(Ljava/lang/Object;)S')
        getInt     = make_method('getInt',     '(Ljava/lang/Object;)I')
        getLong    = make_method('getLong',    '(Ljava/lang/Object;)J')
        getFloat   = make_method('getFloat',   '(Ljava/lang/Object;)F')
        getDouble  = make_method('getDouble',  '(Ljava/lang/Object;)D')

        set        = make_method('set',        '(Ljava/lang/Object;Ljava/lang/Object;)V')
        setBoolean = make_method('setBoolean', '(Ljava/lang/Object;Z)V',
                                               'Set a boolean field in an object')
        setByte    = make_method('setByte',    '(Ljava/lang/Object;B)V',
                                               'Set a byte field in an object')
        setChar    = make_method('setChar',    '(Ljava/lang/Object;C)V')
        setShort   = make_method('setShort',   '(Ljava/lang/Object;S)V')
        setInt     = make_method('setInt',     '(Ljava/lang/Object;I)V')
        setLong    = make_method('setLong',    '(Ljava/lang/Object;J)V')
        setFloat   = make_method('setFloat',   '(Ljava/lang/Object;F)V')
        setDouble  = make_method('setDouble',  '(Ljava/lang/Object;D)V')

    return Field()

def get_constructor_wrapper(obj):

    class Constructor(object):

        def __init__(self):
            self.o = obj

        getName           = make_method("getName",           "()Ljava/lang/String;")
        getModifiers      = make_method("getModifiers",      "()I")
        getAnnotation     = make_method("getAnnotation",     "()Ljava/lang/annotation/Annotation;")
        getParameterTypes = make_method("getParameterTypes", "()[Ljava/lang/Class;",
                                                             "Get the types of the constructor parameters")
        newInstance       = make_method("newInstance",       "([Ljava/lang/Object;)Ljava/lang/Object;")

    return Constructor()

def get_method_wrapper(obj):

    class Method(object):

        def __init__(self):
            self.o = obj

        getName           = make_method("getName",           "()Ljava/lang/String;")
        getModifiers      = make_method("getModifiers",      "()I")
        getAnnotation     = make_method("getAnnotation",     "()Ljava/lang/annotation/Annotation;")
        getParameterTypes = make_method("getParameterTypes", "()[Ljava/lang/Class;",
                                                             "Get the types of the constructor parameters")
        invoke            = make_method("invoke",            "(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;")

    return Method()


def make_run_dictionary(jobject):

    '''Support function for Py_RunString - jobject -> globals / locals

    jobject - address of a Java Map of string to object
    '''
    from .wrappers import JWrapper
    result = {}
    jmap = JWrapper(jobject)
    jentry_set          = jmap.entrySet()
    jentry_set_iterator = jentry_set.iterator()
    while jentry_set_iterator.hasNext():
        entry = jentry_set_iterator.next()
        key   = entry.getKey()
        value = entry.getValue()
        if isinstance(key,   JWrapper): key   = key.o
        if isinstance(value, JWrapper): value = value.o
        result[to_string(key)] = value
    return result


class _JRef(object):

    """
    A reference to some Python value for Java scripting

    A Java script executed using org.cellprofiler.javabridge.CPython.exec
    might want to maintain and refer to objects and values. This class
    wraps the value so that it can be referred to later.

    """
    def __init__(self, value):
        self.__value = value

    def __call__(self):
        return self.__value

__weakref_dict   = weakref.WeakValueDictionary()
__strongref_dict = {}

def create_jref(value):

    """
    Create a weak reference to a Python value

    This routine lets the Java method, CPython.exec(), create weak references
    which can be redeemed by passing a token to redeem_weak_reference. The
    routine returns a reference to the value as well and this reference must
    be stored somewhere (e.g. a global value in a module) for the token to
    be valid upon redemption.

    :param value: The value to be redeemed

    :returns: a tuple of a string token and a reference that must be maintained
              in order to retrieve it later
    """
    global __weakref_dict
    ref = _JRef(value)
    ref_id = uuid.uuid4().hex
    __weakref_dict[ref_id] = ref
    return ref_id, ref

def create_and_lock_jref(value):

    """
    Create and lock a value in one step

    :param value: the value to be redeemed
    :returns: a ref_id that can be used to redeem the value and to unlock it.

    """
    ref_id, ref = create_jref(value)
    lock_jref(ref_id)
    return ref_id

def redeem_jref(ref_id):

    """
    Redeem a reference created using create_jref

    Raises KeyError if the reference could not be found, possibly because
    someone didn't hold onto it

    :param ref_id: the token returned by create_jref for the reference

    :returns: the value

    """
    global __weakref_dict
    return __weakref_dict[ref_id]()

def lock_jref(ref_id):

    """
    Lock a reference to maintain it across CPython.exec() invocations

    Lock a reference into memory until unlock_jref is called. lock_jref()
    can be called repeatedly on the same reference and the reference will
    be held until an equal number of unlock_jref() calls have been made.

    :param ref_id: the ID returned from create_ref

    """
    global __weakref_dict
    global __strongref_dict
    if ref_id not in __strongref_dict:
        __strongref_dict[ref_id] = [__weakref_dict[ref_id]]
    else:
        __strongref_dict[ref_id].append(__weakref_dict[ref_id])

def unlock_jref(ref_id):

    """
    Unlock a reference locked by lock_jref

    Unlock and potentially dereference a reference locked by lock_jref()

    :param ref_id: the ID used to lock the reference

    """
    global __strongref_dict
    refs = __strongref_dict[ref_id]
    if len(refs) == 1:
        del __strongref_dict[ref_id]
    else:
        refs.pop()
