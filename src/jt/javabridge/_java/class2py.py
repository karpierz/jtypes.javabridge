# Copyright (c) 2014 Adam Karpierz
# SPDX-License-Identifier: BSD-3-Clause

from jvm.java.class2py import *

header = \
"""\
# Copyright (c) 2014 Adam Karpierz
# SPDX-License-Identifier: BSD-3-Clause

"""

if __name__ == "__main__":
    import sys
    class2py(sys.argv[1], header=header)
