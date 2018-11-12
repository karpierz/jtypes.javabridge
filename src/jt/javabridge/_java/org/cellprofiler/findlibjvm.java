// Copyright (c) 2014-2018, Adam Karpierz
// Licensed under the BSD license
// http://opensource.org/licenses/BSD-3-Clause

// Code adapted from http://markmail.org/message/4kh7yqwbipdgjwxa

import java.io.File;

class findlibjvm
{
    public static void main(String args[])
    {
        String os_name = System.getProperty("os.name");    // <AK> added
        boolean is_windows = os_name.contains("Windows");  // <AK> added
        String[] paths;
        if ( is_windows )  // <AK> added
        {
            String java_home = System.getProperty("java.home");
            paths = new String[] {
                java_home + "/bin/client",
                java_home + "/bin/server",
                java_home + "/jre/bin/client",
                java_home + "/jre/bin/server",
            };
        }
        else
        {
            String java_library_path = System.getProperty("java.library.path");
            paths = java_library_path.split(File.pathSeparator);  // <AK> was: .split(":");
        }
        for ( String path : paths )
        {
            File f = new File(path,
                              is_windows ? "jvm.dll": "libjvm.so");  // <AK> was: "libjvm.so");
            if ( f.exists() )
            {
                System.out.println(path);
                break;
            }
        }
    }
}
