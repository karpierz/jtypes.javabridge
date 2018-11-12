@echo off
setlocal
set JAVA8_HOME=C:\Program Files\Java\jdk1.8.0_181
if not defined JAVA_HOME (set JAVA_HOME=%JAVA8_HOME%)
set javac="%JAVA_HOME%"\bin\javac -encoding UTF-8 -g:none -deprecation -Xlint:unchecked ^
    -source 1.8 -target 1.8 -bootclasspath "%JAVA8_HOME%\jre\lib\rt.jar"
pushd "%~dp0"\src\jt\javabridge\_java
set py=C:\Windows\py.exe -3.6 -B
%javac% ^
    org\cellprofiler\javabridge\*.java ^
    org\cellprofiler\runnablequeue\*.java
%py% -m class2py org\cellprofiler\javabridge\CPython.class
%py% -m class2py org\cellprofiler\javabridge\CPython$StackFrame.class
%py% -m class2py org\cellprofiler\javabridge\CPython$WrappedException.class
%py% -m class2py org\cellprofiler\runnablequeue\RunnableQueue.class
%py% -m class2py org\cellprofiler\runnablequeue\RunnableQueue$1.class
del /F/Q ^
    org\cellprofiler\javabridge\*.class ^
    org\cellprofiler\runnablequeue\*.class
popd
pushd "%~dp0"\tests
rmdir /Q/S java\classes 2> nul & mkdir java\classes
dir /S/B/O:N ^
    ..\src\jt\javabridge\_java\org\cellprofiler\javabridge\*.java ^
    ..\src\jt\javabridge\_java\org\cellprofiler\runnablequeue\*.java ^
    java\org\cellprofiler\javabridge\test\*.java ^
    java\org\cellprofiler\runnablequeue\*.java ^
    2> nul > build.fil
%javac% -d java/classes -classpath java/lib/* @build.fil
del /F/Q build.fil
popd
endlocal
