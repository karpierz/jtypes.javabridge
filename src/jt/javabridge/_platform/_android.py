# Copyright (c) 2014-2018, Adam Karpierz
# Licensed under the BSD license
# http://opensource.org/licenses/BSD-3-Clause

from __future__ import absolute_import

import sys
import os
from os import path
import re
import logging

from ...jvm.lib import cli, CalledProcessError
from ...jvm.platform import _jvmfinder

logger = logging.getLogger(__name__)


class JVMFinder(_jvmfinder.JVMFinder):

    def __init__(self, java_version=None):

        super(JVMFinder, self).__init__(java_version)

        self._methods = (
        )

    def find_javahome(self):

        """Find JAVA_HOME if it doesn't exist"""

        java_home = os.environ.get("JAVA_HOME")
        if java_home is not None:
            return java_home

        """
        103c103
        <    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        ---
        >    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        """
        try:
            cmd = ("bash", "-c", "type -p java")
            java_bin, _ = cli.cmd(*cmd)
            java_bin = java_bin.strip().decode("utf-8")
            cmd = ("readlink", "-f", java_bin)
            java_dir, _ = cli.cmd(*cmd)
            java_dir = java_dir.strip().decode("utf-8")
        except CalledProcessError:
            raise Exception("Error finding javahome on linux: {}".format("".join(cmd)))
        java_version_string, _ = cli.cmd("bash", "-c", "java -version")
        if re.search("^openjdk", java_version_string, re.MULTILINE) is not None:
            jdk_dir = path.join(java_dir,"..","..","..")
        elif re.search("^java", java_version_string, re.MULTILINE) is not None:
            jdk_dir = path.join(java_dir,"..","..")
        else:
            raise RuntimeError("Failed to determine JDK vendor. "
                               "OpenJDK and Oracle JDK are supported.")
        return path.abspath(jdk_dir)

    def find_jdk(self):

        """Find the JDK under Android"""

        jdk_home = os.environ.get("JDK_HOME")
        if jdk_home is not None:
            return jdk_home

        jdk_home = self.find_javahome()
        if jdk_home.endswith("jre") or jdk_home.endswith("jre/"):
            jdk_home = jdk_home[:jdk_home.rfind("jre")]
        return jdk_home

    def find_javac_cmd(self):

        """Find the javac executable"""

        # will be along path for other platforms
        return "javac"

    def find_jar_cmd(self):

        """Find the jar executable"""

        # will be along path for other platforms
        return "jar"
