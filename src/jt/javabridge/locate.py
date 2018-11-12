# Copyright (c) 2014-2018, Adam Karpierz
# Licensed under the BSD license
# http://opensource.org/licenses/BSD-3-Clause

from __future__ import absolute_import

import os, sys

from ..jvm.lib import platform

def is_mingw():

    # Note: if a matching gcc is available from the shell on Windows, its
    #       probably safe to assume the user is in an MINGW or MSYS or Cygwin
    #       environment, in which case he/she wants to compile with gcc for
    #       Windows, in which case the correct compiler flags will be triggered
    #       by is_mingw. This method is not great, improve it if you know a
    #       better way to discriminate between compilers on Windows.

    # currently this check detects mingw only on Windows. Extend for other
    # platforms if required:
    if os.name != "nt":  # pragma: no cover
        return False

    # if the user defines DISTUTILS_USE_SDK or MSSdk, we expect they want
    # to use Microsoft's compiler (as described here:
    # https://github.com/cython/cython/wiki/CythonExtensionsOnWindows):
    if (os.getenv("DISTUTILS_USE_SDK") is not None or
        os.getenv("MSSdk") is not None):  # pragma: no cover
        return False

    mingw32 = os.getenv("MINGW32_PREFIX") or ""
    mingw64 = os.getenv("MINGW64_PREFIX") or ""

    # if any invocation of gcc works, then we assume the user wants mingw:
    test = "gcc --version > NUL 2>&1"
    return (os.system(test) == 0 or
            os.system(mingw32 + test) == 0 or os.system(mingw64 + test) == 0)

is_linux = platform.is_linux
is_mac   = platform.is_osx
is_win   = platform.is_windows
is_win64 = (is_win and os.environ["PROCESSOR_ARCHITECTURE"] == "AMD64")
is_msvc  = (is_win and sys.version_info >= (2,6,0))
is_mingw = is_mingw()

from ._platform import JVMFinder
find_javahome       = lambda JVMFinder=JVMFinder: JVMFinder().find_javahome()
find_jdk            = lambda JVMFinder=JVMFinder: JVMFinder().find_jdk()
find_javac_cmd      = lambda JVMFinder=JVMFinder: JVMFinder().find_javac_cmd()
find_jar_cmd        = lambda JVMFinder=JVMFinder: JVMFinder().find_jar_cmd()
find_jre_bin_jdk_so = lambda JVMFinder=JVMFinder: JVMFinder().find_jre_bin_jdk_so()
del JVMFinder

del os, sys
del platform
del absolute_import
