# Copyright (c) 2014 Adam Karpierz
# SPDX-License-Identifier: BSD-3-Clause

import ctypes as ct

import jni
from jvm.lib import public
from jvm.lib import cached


def MacStartVM(pvm: jni.POINTER(jni.POINTER(jni.JavaVM)),
               penv: jni.POINTER(jni.POINTER(jni.JNIEnv)),
               pVMArgs: jni.POINTER(jni.JavaVMInitArgs),
               class_name: ct.c_char_p,
               path_to_libjvm: ct.c_char_p,
               path_to_libjli: ct.c_char_p) -> ct.c_int:
    pass # from "mac_javabridge_utils.c": # nogil

def StopVM(vm: jni.JavaVM):
    # MacStopVM # from "mac_javabridge_utils.c": # nogil
    MacStopVM()

def MacRunLoopInit():
    pass # from "mac_javabridge_utils.c": # nogil

def MacRunLoopReset():
    pass # from "mac_javabridge_utils.c": # nogil

def MacRunLoopRun():
    pass # from "mac_javabridge_utils.c": # nogil

def MacRunLoopRunInMode(timeout: ct.c_double):
    pass # from "mac_javabridge_utils.c": # nogil

def MacRunLoopStop():
    pass # from "mac_javabridge_utils.c": # nogil

def MacIsMainThread() -> ct.c_int:
    pass # from "mac_javabridge_utils.c": # nogil
