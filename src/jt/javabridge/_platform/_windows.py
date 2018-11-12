# Copyright (c) 2014-2018, Adam Karpierz
# Licensed under the BSD license
# http://opensource.org/licenses/BSD-3-Clause

from __future__ import absolute_import

import sys
import os
from os import path
import re
import logging
if sys.version_info.major >= 3:
    import winreg
else:
    import _winreg as winreg

from ...jvm.lib import cli
from ...jvm.platform import _jvmfinder

logger = logging.getLogger(__name__)


class JVMFinder(_jvmfinder.JVMFinder):

    def __init__(self, java_version=None):

        super(JVMFinder, self).__init__(java_version)

        self._methods = (
        )

    def find_jvm(self):

        # Look for JAVA_HOME and in the registry

        java_home = self.find_javahome()
        if java_home is None:
            return None
        for jre_home in (java_home, path.join(java_home,"jre")):
            jre_bin = path.join(jre_home,'bin')
            for place_to_look in ('client','server'):
                jvm_dir = path.join(jre_bin,place_to_look)
                if path.isfile(path.join(jvm_dir,"jvm.dll")):
                    new_path = ';'.join((os.environ['PATH'], jvm_dir, jre_bin))
                    if (sys.version_info.major < 3 and
                        isinstance(os.environ['PATH'], bytes) and isinstance(new_path, unicode)):
                        # Don't inadvertantly set an environment variable
                        # to unicode: causes subprocess.check_call to fail
                        # in Python 2
                        new_path = new_path.encode("utf-8")
                    os.environ['PATH'] = new_path
                    return jvm_dir
        else:
            return None

    def find_javahome(self):

        """Find JAVA_HOME if it doesn't exist"""

        java_home = os.environ.get("JAVA_HOME")
        if java_home is not None:
            return java_home

        node = r"SOFTWARE"
        # Registry keys changed in Java 9
        # https://docs.oracle.com/javase/9/migrate/toc.htm#GUID-EEED398E-AE37-4D12-AB10-49F82F720027
        jre_key_paths = (node + r"\JavaSoft\JRE", node + r"\JavaSoft\Java Runtime Environment")
        hkey = winreg.HKEY_LOCAL_MACHINE

        for key_path in jre_key_paths:
            try:
                java_key = winreg.OpenKey(hkey, key_path)
                java_key_values = dict([winreg.EnumValue(java_key, i)[:2]
                                        for i in range(winreg.QueryInfoKey(java_key)[1])])
                version = java_key_values["CurrentVersion"]
                version_key = r"{}\{}".format(key_path, version)
                version = winreg.OpenKey(hkey, version_key)
                version_values = dict([winreg.EnumValue(version, i)[:2]
                                       for i in range(winreg.QueryInfoKey(version)[1])])
                java_home = version_values["JavaHome"]
                return java_home
            except WindowsError as exc:
                import errno
                if exc.errno != errno.ENOENT:
                    raise exc
        else:
            raise RuntimeError("Failed to find the Java Runtime Environment. "
                               "Please download and install the Oracle JRE 1.7 or later")

    def find_jdk(self):

        """Find the JDK under Windows"""

        jdk_home = os.environ.get("JDK_HOME")
        if jdk_home is not None:
            return jdk_home

        node = r"SOFTWARE"
        # Registry keys changed in Java 9
        # https://docs.oracle.com/javase/9/migrate/toc.htm#GUID-EEED398E-AE37-4D12-AB10-49F82F720027
        jdk_key_paths = (node + r"\JavaSoft\JDK", node + r"\JavaSoft\Java Development Kit")
        hkey = winreg.HKEY_LOCAL_MACHINE

        for key_path in jdk_key_paths:
            try:
                java_key = winreg.OpenKey(hkey, key_path)
                java_key_values = dict([winreg.EnumValue(java_key, i)[:2]
                                        for i in range(winreg.QueryInfoKey(java_key)[1])])
                version = java_key_values["CurrentVersion"]
                version_key = r"{}\{}".format(key_path, version)
                version = winreg.OpenKey(hkey, version_key)
                version_values = dict([winreg.EnumValue(version, i)[:2]
                                       for i in range(winreg.QueryInfoKey(version)[1])])
                jdk_home = version_values["JavaHome"]
                return jdk_home
            except WindowsError as exc:
                import errno
                if exc.errno != errno.ENOENT:
                    raise exc
        else:
            raise RuntimeError("Failed to find the Java Development Kit. "
                               "Please download and install the Oracle JDK 1.7 or later")

    def find_javac_cmd(self):

        """Find the javac executable"""

        jdk_home = self.find_jdk()
        javac = path.join(jdk_home, "bin", "javac.exe")
        if not path.isfile(javac):
            raise RuntimeError("Failed to find javac.exe in its usual location "
                               "under the JDK ({})".format(javac))
        return javac

    def find_jar_cmd(self):

        """Find the jar executable"""

        jdk_home = self.find_jdk()
        jar = path.join(jdk_home, "bin", "jar.exe")
        if not path.isfile(jar):
            raise RuntimeError("Failed to find jar.exe in its usual location "
                               "under the JDK ({})".format(jar))
        return jar

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
            jre_libexec = path.join(jre_home, "bin")
            arches = ("",)
            lib_prefix = ""
            lib_suffix = ".dll"
            for arch in arches:
                for place_to_look in ("client", "server"):
                    jvm_dir = path.join(jre_libexec, arch, place_to_look)
                    jvm_so  = path.join(jvm_dir, lib_prefix + "jvm" + lib_suffix)
                    if path.isfile(jvm_so):
                        return (jre_bin, jvm_so)
        else:
            return (jre_bin, None)
