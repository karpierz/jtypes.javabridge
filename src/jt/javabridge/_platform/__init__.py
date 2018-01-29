# Copyright (c) 2014-2018, Adam Karpierz
# Licensed under the BSD license
# http://opensource.org/licenses/BSD-3-Clause

from ...jvm.lib import platform

if platform.is_windows:
    from ._windows import JVMFinder
elif platform.is_linux:
    from ._linux   import JVMFinder
elif platform.is_osx:
    from ._osx     import JVMFinder
elif platform.is_android:
    from ._android import JVMFinder
elif platform.is_posix:
    from ._linux   import JVMFinder
else:
    raise ImportError("unsupported platform")

del platform
