# Copyright (c) 2014 Adam Karpierz
# SPDX-License-Identifier: BSD-3-Clause

from typing import Optional, Tuple
from pathlib import Path
import sys
import os
import re
import ctypes
import logging

from jvm.lib import public
from jvm.lib import platform
from jvm.lib import run

from jvm.platform import _jvmfinder

logger = logging.getLogger(__name__)


@public
class JVMFinder(_jvmfinder.JVMFinder):

    def __init__(self, java_version=None):
        super().__init__(java_version)

        self._methods = (
        )

    def find_jvm(self) -> Optional[Path]:
        # Load libjvm.dylib and lib/jli/libjli.dylib if it exists
        return self.find_javahome()

    def find_javahome(self) -> Optional[Path]:
        """Find JAVA_HOME if it doesn't exist"""

        if "CP_JAVA_HOME" in os.environ:
            # Prefer CellProfiler's JAVA_HOME if it's set.
            return Path(os.environ["CP_JAVA_HOME"])

        java_home = self.get_java_home()
        if java_home is not None:
            return java_home

        # Use the "java_home" executable to find the location. See "man java_home"
        libc = ctypes.CDLL("/usr/lib/libc.dylib")
        arch = "i386" if platform.is_32bit else "x86_64"
        try:
            java_home = Path(run("/usr/libexec/java_home", "--arch", arch,
                                 text=True, capture_output=True).stdout.strip())
            for place_to_look in (java_home.parent/"Libraries",
                                  java_home/"jre/lib/server"):
                # In "Java for OS X 2015-001" libjvm.dylib is a symlink to libclient.dylib
                # which is i686 only, whereas libserver.dylib contains both architectures.
                for file_to_look in ("libjvm.dylib",
                                     "libclient.dylib",
                                     "libserver.dylib"):
                    lib = place_to_look/file_to_look
                    #
                    # dlopen_preflight checks to make sure the dylib
                    # can be loaded in the current architecture
                    #
                    if lib.exists() and libc.dlopen_preflight(str(lib).encode("utf-8")) != 0:
                        return java_home
            else:
                logger.error(f"Could not find Java JRE compatible with {arch} architecture")
                if platform.is_32bit:
                    logger.error("Please visit https://support.apple.com/kb/DL1572 for help\n"
                                 "installing Apple legacy Java 1.6 for 32 bit support.")
                return None
        except:
            logger.error("Failed to run /usr/libexec/java_home, "
                         "defaulting to best guess for Java", exc_info=1)
            return Path("/System/Library/Frameworks/JavaVM.framework/Home")

    def find_jdk(self) -> Optional[Path]:
        """Find the JDK under OS X"""
        jdk_home = self.get_jdk_home()
        if jdk_home is not None:
            return jdk_home
        return self.find_javahome()

    def find_javac_cmd(self) -> Path:
        """Find the javac executable"""
        # will be along path for other platforms
        return Path("javac")

    def find_jar_cmd(self) -> Path:
        """Find the jar executable"""
        # will be along path for other platforms
        return Path("jar")

    def find_jre_bin_jdk_so(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Finds the jre bin dir and the jdk shared library file"""
        java_home = self.find_javahome()
        if java_home is None:
            return (None, None)
        jre_bin = None
        for jre_home in (java_home,
                         java_home/"jre",
                         java_home/"default-java",
                         java_home/"default-runtime"):
            jre_bin     = jre_home/"bin"
            jre_libexec = jre_home/"lib"
            arches = ("",)
            lib_prefix = "lib"
            lib_suffix = ".dylib"
            for arch in arches:
                for place_to_look in ("client", "server"):
                    jvm_dir = jre_libexec/arch/place_to_look
                    jvm_so  = jvm_dir/(lib_prefix + "jvm" + lib_suffix)
                    if jvm_so.is_file():
                        return (jre_bin, jvm_so)
        else:
            return (jre_bin, None)

    def _find_mac_lib(self, library: str) -> Optional[Path]:
        jvm_dir = self.find_javahome()
        for extension in (".dylib", ".jnilib"):
            try:
                cmd = ("find", jvm_dir.parent, "-name", library + extension)
                result = run(*cmd, text=True, capture_output=True).stdout
                lines = result.split("\n")
                if lines and lines[0]:
                    library_path = lines[0].strip()
                    return Path(library_path)
            except Exception as exc:
                logger.error(f"Failed to execute '{cmd}' when searching for {library}",
                             exc_info=1)
        else:
            logger.error(f"Failed to find {library} (jvmdir: {jvm_dir})")
            return None
