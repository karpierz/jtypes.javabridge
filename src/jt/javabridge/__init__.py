# Copyright (c) 2014-2018, Adam Karpierz
# Licensed under the BSD license
# http://opensource.org/licenses/BSD-3-Clause

from . import __config__ ; del __config__
from .__about__ import * ; del __about__

from os import path

# We must dynamically find libjvm.so since its unlikely to be in the same place
# as it was on the distribution on which javabridge was built.
import sys
if sys.platform.startswith("linux"):  # pragma: no cover
    from .locate import find_jre_bin_jdk_so
    _, jdk_so = find_jre_bin_jdk_so()
    if jdk_so:
        import ctypes
        # ctypes.cdll.LoadLibrary(jdk_so)
        del ctypes

# List of absolute paths to JAR files that are required for the Javabridge to work.
jars_dir = path.join(path.dirname(__file__), "_java", "lib")
JARS = [path.realpath(path.join(jars_dir, _)) for _ in ["rhino-1.7.8.jar"]]
del jars_dir

from .jutil import start_vm, kill_vm, vm, activate_awt, deactivate_awt
from .jutil import attach, detach, get_env

# JavaScript
from .jutil import run_script, unwrap_javascript

# Operations on Java objects
from .jutil import (get_field, get_static_field, set_field, set_static_field,
                    call, static_call, is_instance_of, make_instance, make_static_call,
                    to_string)

# Make Python object that wraps a Java object
from .jutil    import make_method, make_new, make_call, box
from .wrappers import JWrapper, JClassWrapper, JProxy

from .jutil import get_nice_arg

# Useful collection wrappers
from .jutil import (get_dictionary_wrapper, jdictionary_to_string_dictionary,
                    jenumeration_to_string_list, get_enumeration_wrapper, iterate_collection,
                    iterate_java, make_list, get_collection_wrapper, make_future_task,
                    make_map, get_map_wrapper)

# Reflection. (These use make_method or make_new internally.)
from .jutil import (class_for_name, get_class_wrapper,
                    get_field_wrapper, get_constructor_wrapper, get_method_wrapper)

# Ensure that callables, runnables and futures that use AWT run in the
# AWT main thread, which is not accessible from Python.
from .jutil import (execute_callable_in_main_thread,
                    execute_runnable_in_main_thread,
                    execute_future_in_main_thread,
                    get_future_wrapper)

# Exceptions
from .jutil import JavaError, JavaException, JVMNotFoundError

# References
from .jutil import create_jref, create_and_lock_jref, redeem_jref, lock_jref, unlock_jref

# Don't expose: AtExit, _get_nice_args,
# make_run_dictionary, run_in_main_thread, _split_sig, unwrap_javascript,
# print_all_stack_traces

from ._jvm import mac_run_loop_init, mac_enter_run_loop, mac_stop_run_loop

# Low-level API
from ._jenv   import JB_Env
from ._jclass import JB_Class, JB_Object
# JNI helpers.
from ._jvm    import jni_enter, jni_exit, jvm_enter

del path
