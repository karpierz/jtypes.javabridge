# Copyright (c) 2014 Adam Karpierz
# SPDX-License-Identifier: BSD-3-Clause

from typing import Optional, Tuple
from pathlib import Path
import sys
import os
import re
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

    def find_javahome(self) -> Optional[Path]:
        """Find JAVA_HOME if it doesn't exist"""

        if "CP_JAVA_HOME" in os.environ:
            # Prefer CellProfiler's JAVA_HOME if it's set.
            return Path(os.environ["CP_JAVA_HOME"])

        java_home = self.get_java_home()
        if java_home is not None:
            return java_home

        try:
            cmd = ("bash", "-c", "type -p java")
            java_bin = run(*cmd, text=True,
                           stdout=run.PIPE, stderr=run.STDOUT).stdout.strip()
            cmd = ("readlink", "-f", java_bin)
            java_dir = Path(run(*cmd, text=True,
                                stdout=run.PIPE, stderr=run.STDOUT).stdout.strip())
        except run.CalledProcessError:
            raise Exception("Error finding javahome on linux: {}".format("".join(cmd)))
        java_version_string = run("bash", "-c", "java -version",
                                  text=True, stdout=run.PIPE, stderr=run.STDOUT).stdout
        if re.search("^openjdk", java_version_string, re.MULTILINE) is not None:
            pattern = 'openjdk version "([^"]+)"'
            match = re.search(pattern, java_version_string, re.MULTILINE)
            if not match:
                raise RuntimeError("Failed to parse version from {}".format(
                                   java_version_string))
            version = match.groups()[0]
            if version < "1.8":
                jdk_dir = java_dir.parent.parent.parent
            else:
                jdk_dir = java_dir.parent.parent
        elif re.search("^java", java_version_string, re.MULTILINE) is not None:
            jdk_dir = java_dir.parent.parent
        else:
            raise RuntimeError("Failed to determine JDK vendor. "
                               "OpenJDK and Oracle JDK are supported.")
        return jdk_dir.absolute()

    def find_jdk(self) -> Optional[Path]:
        """Find the JDK under Android"""
        jdk_home = self.get_jdk_home()
        if jdk_home is not None:
            return jdk_home
        jdk_home = str(self.find_javahome())
        if jdk_home.endswith(("jre", "jre/")):
            jdk_home = jdk_home[:jdk_home.rfind("jre")]
        return Path(jdk_home)

    def find_javac_cmd(self) -> Path:
        """Find the javac executable"""
        # will be along path for other platforms
        return Path("javac")

    def find_jar_cmd(self) -> Path:
        """Find the jar executable"""
        # will be along path for other platforms
        return Path("jar")
