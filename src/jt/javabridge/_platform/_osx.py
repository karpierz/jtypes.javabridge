# Copyright (c) 2014-2018, Adam Karpierz
# Licensed under the BSD license
# http://opensource.org/licenses/BSD-3-Clause

from __future__ import absolute_import

import sys
import os
from os import path
import re
import ctypes
import logging

from ...jvm.lib import platform
from ...jvm.lib import cli
from ...jvm.platform import _jvmfinder

logger = logging.getLogger(__name__)


class JVMFinder(_jvmfinder.JVMFinder):

    def __init__(self, java_version=None):

        super(JVMFinder, self).__init__(java_version)

        self._methods = (
        )

    def find_jvm(self):

        # Load libjvm.dylib and lib/jli/libjli.dylib if it exists

        return self.find_javahome()

    def find_javahome(self):

        """Find JAVA_HOME if it doesn't exist"""

        java_home = os.environ.get("JAVA_HOME")
        if java_home is not None:
            return java_home

        # Use the "java_home" executable to find the location. See "man java_home"
        libc = ctypes.CDLL("/usr/lib/libc.dylib")
        arch = "i386" if platform.is_32bit else "x86_64"
        try:
            java_home, _ = cli.cmd("/usr/libexec/java_home", "--arch", arch)
            java_home = java_home.strip().decode("utf-8")
            for place_to_look in (path.join(path.dirname(java_home),"Libraries"),
                                  path.join(java_home,"jre","lib","server")):
                # In "Java for OS X 2015-001" libjvm.dylib is a symlink to libclient.dylib
                # which is i686 only, whereas libserver.dylib contains both architectures.
                for file_to_look in ("libjvm.dylib",
                                     "libclient.dylib",
                                     "libserver.dylib"):
                    lib = path.join(place_to_look, file_to_look)
                    #
                    # dlopen_preflight checks to make sure the dylib
                    # can be loaded in the current architecture
                    #
                    if path.exists(lib) and libc.dlopen_preflight(lib.encode("utf-8")) != 0:
                        return java_home
            else:
                logger.error("Could not find Java JRE compatible with {} architecture".format(arch))
                if platform.is_32bit:
                    logger.error("Please visit https://support.apple.com/kb/DL1572 for help\n"
                                 "installing Apple legacy Java 1.6 for 32 bit support.")
                return None
        except:
            logger.error("Failed to run /usr/libexec/java_home, "
                         "defaulting to best guess for Java", exc_info=1)
            return "/System/Library/Frameworks/JavaVM.framework/Home"

    def find_jdk(self):

        """Find the JDK under OS X"""

        jdk_home = os.environ.get("JDK_HOME")
        if jdk_home is not None:
            return jdk_home

        return self.find_javahome()

    def find_javac_cmd(self):

        """Find the javac executable"""

        # will be along path for other platforms
        return "javac"

    def find_jar_cmd(self):

        """Find the jar executable"""

        # will be along path for other platforms
        return "jar"

    def _find_mac_lib(self, library):

        jvm_dir = self.find_javahome()
        for extension in (".dylib", ".jnilib"):
            try:
                cmd = ["find", path.dirname(jvm_dir), "-name", library + extension]
                result, _ = cli.cmd(*cmd)
                if type(result) == bytes:
                    lines = result.decode("utf-8").split("\n")
                else:
                    lines = result.split("\n")
                if len(lines) > 0 and len(lines[0]) > 0:
                    library_path = lines[0].strip()
                    return library_path
            except Exception as exc:
                logger.error("Failed to execute '{}' when searching for {}".format(cmd, library),
                             exc_info=1)
        else:
            logger.error("Failed to find {} (jvmdir: {})".format(library, jvm_dir))
            return None

    def find_jre_bin_jdk_so(self):

        """Finds the jre bin dir and the jdk shared library file"""

        java_home = self.find_javahome()
        if java_home is None:
            return (None, None)
        jre_bin = None
        for jre_home in (java_home,
                         path.join(java_home, "jre"),
                         path.join(java_home, "default-java")):
            jre_bin     = path.join(jre_home, "bin")
            jre_libexec = path.join(jre_home, "lib")
            arches = ("",)
            lib_prefix = "lib"
            lib_suffix = ".dylib"
            for arch in arches:
                for place_to_look in ("client", "server"):
                    jvm_dir = path.join(jre_libexec, arch, place_to_look)
                    jvm_so  = path.join(jvm_dir, lib_prefix + "jvm" + lib_suffix)
                    if path.isfile(jvm_so):
                        return (jre_bin, jvm_so)
        else:
            return (jre_bin, None)
