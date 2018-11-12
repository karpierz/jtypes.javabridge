.. -*- visual-line-mode -*-

High-level API
===============

The high-level API can wrap a Java object or class so that its methods and
fields can be referenced by dot syntax. It also has functions that offload
some of the burden of exception handling and type conversion, thus providing
a mid-level compromise between ease of use and performance.

Signatures
----------

*jtypes.javabridge* uses method signatures when it uses the JNI method lookup
APIs. The method signatures are also used to convert between Python and Java
primitives and objects. If you use the high-level API, as opposed to scripting,
you will need to learn how to construct a signature for a class method.
For example, java.lang.String has the following three methods:
::

    public char charAt(int index)
    public int indexOf(String str)
    public byte [] getString(String charsetName)
    
charAt has the signature, "(I)C", because it takes one integer argument (I) and
its return value is a char (C).

indexOf has the signature, "(Ljava/lang/String;)I", "L" and ";" bracket a
class name which is represented as a path instead of with the dotted syntax.

getString has the signature, "(Ljava/lang/String;)[B. "[B" uses "[" to indicate
that an array will be returned and "B" indicates that the array is of type, byte.

The signature syntax is described in `JNI Types and Data Structures
<http://docs.oracle.com/javase/1.5.0/docs/guide/jni/spec/types.html>`_.
An example: “(ILjava/lang/String;)[I” takes an integer and string as parameters
and returns an array of integers. 

Cheat sheet: 

Z
   boolean
B
   byte
C
   char
S
   short
I
   int
J
   long
F
   float
D
   double
L
   class (e.g., Lmy/class;)
\[
   array of (e.g., [B = byte array)


The signatures are difficult, but you can cheat: the JDK has a
Java class file disassembler called ``javap`` that prints out the
signatures of everything in a class.

Wrapping Java objects using reflection
--------------------------------------
.. autoclass:: jt.javabridge.JWrapper(o)
.. autoclass:: jt.javabridge.JClassWrapper(class_name)
.. autoclass:: jt.javabridge.JProxy(class_name)

Operations on Java objects
--------------------------
.. autofunction:: jt.javabridge.call
.. autofunction:: jt.javabridge.make_call
.. autofunction:: jt.javabridge.static_call
.. autofunction:: jt.javabridge.make_static_call
.. autofunction:: jt.javabridge.get_field
.. autofunction:: jt.javabridge.set_field
.. autofunction:: jt.javabridge.get_static_field
.. autofunction:: jt.javabridge.set_static_field
.. autofunction:: jt.javabridge.is_instance_of
.. autofunction:: jt.javabridge.make_instance
.. autofunction:: jt.javabridge.to_string
.. autofunction:: jt.javabridge.get_nice_arg

Hand-coding Python objects that wrap Java objects
-------------------------------------------------
The functions ``make_new`` and ``make_method`` create Python methods that wrap
Java constructors and methods, respectively. The function can be used to create
Python wrapper classes for Java classes. Example::

    >>> from jt import javabridge
    >>> class Integer:
            new_fn = javabridge.make_new("java/lang/Integer", "(I)V")
            def __init__(self, i):
                self.new_fn(i)
            intValue = javabridge.make_method("intValue", "()I", "Retrieve the integer value")
    >>> i = Integer(435)
    >>> i.intValue()
    435

.. autofunction:: jt.javabridge.make_new
.. autofunction:: jt.javabridge.make_method

Useful collection wrappers
--------------------------
The collection wrappers take a Java object that implements some interface
and return a corresponding Python object that wraps the interface's methods
and in addition provide Python-style access to the Java object. The Java
object itself is, by convention, saved as self.o in the Python object.

.. autofunction:: jt.javabridge.get_collection_wrapper
.. autofunction:: jt.javabridge.get_dictionary_wrapper
.. autofunction:: jt.javabridge.get_enumeration_wrapper
.. autofunction:: jt.javabridge.jdictionary_to_string_dictionary
.. autofunction:: jt.javabridge.jenumeration_to_string_list
.. autofunction:: jt.javabridge.iterate_collection
.. autofunction:: jt.javabridge.iterate_java
.. autofunction:: jt.javabridge.make_list
.. autofunction:: jt.javabridge.get_map_wrapper
.. autofunction:: jt.javabridge.make_map

Reflection
----------
These functions make class wrappers suitable for introspection.
These wrappers are examples of the kinds of wrappers that you can build
yourself using ``make_method`` and ``make_new``.

.. autofunction:: jt.javabridge.get_class_wrapper
.. autofunction:: jt.javabridge.get_field_wrapper
.. autofunction:: jt.javabridge.class_for_name
.. autofunction:: jt.javabridge.get_constructor_wrapper
.. autofunction:: jt.javabridge.get_method_wrapper

Executing in the correct thread
-------------------------------
Ensure that callables, runnables and futures that use AWT run in
the AWT main thread, which is not accessible from Python for some operating
systems.

.. autofunction:: jt.javabridge.make_future_task
.. autofunction:: jt.javabridge.execute_runnable_in_main_thread
.. autofunction:: jt.javabridge.execute_future_in_main_thread
.. autofunction:: jt.javabridge.execute_callable_in_main_thread
.. autofunction:: jt.javabridge.get_future_wrapper

Exceptions
----------

.. autoexception:: jt.javabridge.JavaError
.. autoexception:: jt.javabridge.JavaException
.. autoexception:: jt.javabridge.JVMNotFoundError
