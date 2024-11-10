# Copyright (c) 2014 Adam Karpierz
# SPDX-License-Identifier: BSD-3-Clause

from jvm.lib import platform

if platform.is_windows:
    from ._windows import *  # noqa
elif platform.is_linux:
    from ._linux   import *  # noqa
elif platform.is_macos:
    from ._macos   import *  # noqa
elif platform.is_android:
    from ._android import *  # noqa
elif platform.is_posix:
    from ._linux   import *  # noqa
else:
    raise ImportError("unsupported platform")

del platform
