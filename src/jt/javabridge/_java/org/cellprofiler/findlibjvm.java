// Copyright (c) 2014 Adam Karpierz
// SPDX-License-Identifier: BSD-3-Clause

// Code adapted from https://markmail.org/message/4kh7yqwbipdgjwxa

import java.io.File;

class findlibjvm
{
    private static String os_name = System.getProperty("os.name");

    public static void main(String args[])
    {
        String[] paths = {};
        String libjvm = null;
        if ( isWindows() )
        {
            String java_home = System.getProperty("java.home");
            paths = new String[] {
                java_home + "/bin/client",
                java_home + "/bin/server",
                java_home + "/jre/bin/client",
                java_home + "/jre/bin/server",
            };
            libjvm = "jvm.dll";
        }
        else if ( isMacOS() )
        {
            String java_home = System.getProperty("java.home");
            paths = new String[] {
                java_home + "/lib/client",
                java_home + "/lib/server",
                java_home + "/jre/lib/client",
                java_home + "/jre/lib/server",
            };
            libjvm = "libjvm.dylib";
        }
        else
        {
            String java_library_path = System.getProperty("java.library.path");
            paths = java_library_path.split(File.pathSeparator);
            libjvm = "libjvm.so";
        }

        for ( String path : paths )
        {
            File f = new File(path, libjvm);
            if ( f.exists() )
            {
                System.out.println(path);
                break;
            }
        }
    }

    public static boolean isWindows()
    {
        return os_name.toLowerCase().contains("windows");
    }

    public static boolean isLinux()
    {
        return os_name.toLowerCase().contains("linux");
    }

    public static boolean isMacOS()
    {
        return os_name.toLowerCase().contains("mac os");
    }

    public static boolean isBSD()
    {
        return (os_name.toLowerCase().contains("freebsd") ||
                os_name.toLowerCase().contains("openbsd") ||
                os_name.toLowerCase().contains("netbsd"));
    }

    public static boolean isSunOS()
    {
        return (os_name.toLowerCase().contains("sunos") ||
                os_name.toLowerCase().contains("solaris"));
    }

    public static boolean isAIX()
    {
        return os_name.toLowerCase().indexOf("aix") > 0;
    }

    public static boolean isPosix()
    {
        // Digital Unix             // ?
        // HP (Hewlett Packard) UX  // ?
        // MPE/iX                   // ?
        return (isLinux() ||
                isMacOS() ||
                os_name.toLowerCase().contains("irix") ||
                isBSD()   ||  // ?
                isSunOS() ||  // ?
                // os_name.toLowerCase().contains("nix") ||
                isAIX() );    // ?
    }
}
