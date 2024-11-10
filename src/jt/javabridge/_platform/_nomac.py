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
    return -1

def StopVM(vm: jni.JavaVM):
    vm.DestroyJavaVM()

def MacRunLoopInit():
    pass

def MacRunLoopReset():
    pass

def MacRunLoopRun():
    pass

def MacRunLoopRunInMode(timeout: ct.c_double):
    pass

def MacRunLoopStop():
    pass

def MacIsMainThread() -> ct.c_int:
    return 0
