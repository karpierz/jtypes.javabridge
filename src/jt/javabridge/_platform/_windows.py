# Copyright (c) 2014 Adam Karpierz
# SPDX-License-Identifier: BSD-3-Clause

from typing import Optional, Tuple
from pathlib import Path
import sys
import os
import re
import winreg
import logging

from jvm.lib import public
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
        # Look for JAVA_HOME and in the registry
        java_home = self.find_javahome()
        if java_home is None:
            return None
        for jre_home in (java_home, java_home/"jre"):
            jre_bin = jre_home/"bin"
            for place_to_look in ("client", "server"):
                jvm_dir = jre_bin/place_to_look
                if (jvm_dir/"jvm.dll").is_file():
                    os.environ["PATH"] += (os.pathsep + str(jvm_dir) +
                                           os.pathsep + str(jre_bin))
                    return jvm_dir
        else:
            return None

    def find_javahome(self) -> Optional[Path]:
        """Find JAVA_HOME if it doesn't exist"""

        if hasattr(sys, "frozen"):
            # If we're frozen we probably have a packaged java environment.
            app_path  = Path(sys.executable).parent
            java_path = app_path/"java"
            if java_path.path.exists():
                return java_path
            else:
                # Can use env from CP_JAVA_HOME or JAVA_HOME by removing the CellProfiler/java folder.
                print("Packaged java environment not found, searching for java elsewhere.")

        if "CP_JAVA_HOME" in os.environ:
            # Prefer CellProfiler's JAVA_HOME if it's set.
            return Path(os.environ["CP_JAVA_HOME"])

        java_home = self.get_java_home()
        if java_home is not None:
            return java_home

        node = r"SOFTWARE"
        # Registry keys changed in Java 9
        # https://docs.oracle.com/javase/9/migrate/toc.htm#GUID-EEED398E-AE37-4D12-AB10-49F82F720027
        jre_key_paths = (node + r"\JavaSoft\JRE",
                         node + r"\JavaSoft\Java Runtime Environment",
                         node + r"\JavaSoft\JDK")
        hkey = winreg.HKEY_LOCAL_MACHINE

        for key_path in jre_key_paths:
            try:
                java_key = winreg.OpenKey(hkey, key_path)
                java_key_values = dict([winreg.EnumValue(java_key, i)[:2]
                                        for i in range(winreg.QueryInfoKey(java_key)[1])])
                version = java_key_values["CurrentVersion"]
                version_key = rf"{key_path}\{version}"
                version = winreg.OpenKey(hkey, version_key)
                version_values = dict([winreg.EnumValue(version, i)[:2]
                                       for i in range(winreg.QueryInfoKey(version)[1])])
                java_home = version_values["JavaHome"]
                return Path(java_home)
            except WindowsError as exc:
                import errno
                if exc.errno != errno.ENOENT:
                    raise exc
        else:
            if hasattr(sys, "frozen"):
                print("CellProfiler Startup ERROR: "
                      "Could not find path to Java environment directory.\n"
                      "Please set the CP_JAVA_HOME system environment variable.\n"
                      "Visit https://broad.io/cpjava for instructions.")
                os.system("pause")  # Keep console window open until keypress.
                os._exit(1)
            raise RuntimeError("Failed to find the Java Runtime Environment. "
                               "Please download and install the Oracle JRE 1.7 or later")

    def find_jdk(self) -> Optional[Path]:
        """Find the JDK under Windows"""
        jdk_home = self.get_jdk_home()
        if jdk_home is not None:
            return jdk_home

        node = r"SOFTWARE"
        # Registry keys changed in Java 9
        # https://docs.oracle.com/javase/9/migrate/toc.htm#GUID-EEED398E-AE37-4D12-AB10-49F82F720027
        jdk_key_paths = (node + r"\JavaSoft\JDK",
                         node + r"\JavaSoft\Java Development Kit")
        hkey = winreg.HKEY_LOCAL_MACHINE

        for key_path in jdk_key_paths:
            try:
                java_key = winreg.OpenKey(hkey, key_path)
                java_key_values = dict([winreg.EnumValue(java_key, i)[:2]
                                        for i in range(winreg.QueryInfoKey(java_key)[1])])
                version = java_key_values["CurrentVersion"]
                version_key = rf"{key_path}\{version}"
                version = winreg.OpenKey(hkey, version_key)
                version_values = dict([winreg.EnumValue(version, i)[:2]
                                       for i in range(winreg.QueryInfoKey(version)[1])])
                jdk_home = version_values["JavaHome"]
                return Path(jdk_home)
            except WindowsError as exc:
                import errno
                if exc.errno != errno.ENOENT:
                    raise exc
        else:
            raise RuntimeError("Failed to find the Java Development Kit. "
                               "Please download and install the Oracle JDK 1.7 or later")

    def find_javac_cmd(self) -> Path:
        """Find the javac executable"""
        jdk_home = self.find_jdk()
        javac = jdk_home/"bin/javac.exe"
        if not javac.is_file():
            raise RuntimeError("Failed to find javac.exe in its usual location "
                               f"under the JDK ({javac})")
        return javac

    def find_jar_cmd(self) -> Path:
        """Find the jar executable"""
        jdk_home = self.find_jdk()
        jar = jdk_home/"bin/jar.exe"
        if not jar.is_file():
            raise RuntimeError("Failed to find jar.exe in its usual location "
                               f"under the JDK ({jar})")
        return jar

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
            jre_libexec = jre_home/"bin"
            arches = ("",)
            lib_prefix = ""
            lib_suffix = ".dll"
            for arch in arches:
                for place_to_look in ("client", "server"):
                    jvm_dir = jre_libexec/arch/place_to_look
                    jvm_so  = jvm_dir/(lib_prefix + "jvm" + lib_suffix)
                    if jvm_so.is_file():
                        return (jre_bin, jvm_so)
        else:
            return (jre_bin, None)
