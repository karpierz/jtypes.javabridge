The low-level API
=================

This API wraps the Java Native Interface (JNI) at the lowest level.
It provides primitives for creating an environment and making calls on it.

Java array objects are handled as numpy arrays.

Each thread has its own environment. When you start a thread, you must attach
to the VM to get that thread's environment and access Java from that thread.
You must detach from the VM before the thread exits.

.. autofunction:noindex: jt.javabridge.attach
.. autofunction:noindex: jt.javabridge.detach

In order to get the environment:

.. autofunction:: jt.javabridge.get_env

Examples::
    >>> from jt.javabridge import get_env
    >>> env = get_env()
    >>> s = env.new_string(u"Hello, world.")
    >>> c = env.get_object_class(s)
    >>> method_id = env.get_method_id(c, "length", "()I")
    >>> method_id
    <Java method with sig=()I at 0xa0a4fd0>
    >>> result = env.call_method(s, method_id)
    >>> result
    13
    
.. autoclass:: jt.javabridge.JB_Env

   .. automethod:: jt.javabridge.JB_Env.get_version()
   
   .. line-block:: **Class discovery**
   
   .. automethod:: jt.javabridge.JB_Env.find_class(name)
   .. automethod:: jt.javabridge.JB_Env.get_object_class(o)
   .. automethod:: jt.javabridge.JB_Env.is_instance_of(o, c)
   
   .. line-block:: **Calling Java object and class (static) methods:**
   
   .. automethod:: jt.javabridge.JB_Env.get_method_id(c, name, sig)
   .. automethod:: jt.javabridge.JB_Env.get_static_method_id(c, name, sig)
   .. automethod:: jt.javabridge.JB_Env.from_reflected_method(method, sig, is_static)
   .. automethod:: jt.javabridge.JB_Env.new_object(c, m, \*args)
   .. automethod:: jt.javabridge.JB_Env.call_method(o, m, \*args)
   .. automethod:: jt.javabridge.JB_Env.call_static_method(c, m, \*args)
   
   .. line-block:: **Accessing Java object and class (static) fields:**
   
   .. automethod:: jt.javabridge.JB_Env.get_field_id(c, name, sig)
   .. automethod:: jt.javabridge.JB_Env.get_static_field_id(c, name, sig)
   .. automethod:: jt.javabridge.JB_Env.get_static_object_field
   .. automethod:: jt.javabridge.JB_Env.get_static_boolean_field
   .. automethod:: jt.javabridge.JB_Env.get_static_byte_field
   .. automethod:: jt.javabridge.JB_Env.get_static_short_field
   .. automethod:: jt.javabridge.JB_Env.get_static_int_field
   .. automethod:: jt.javabridge.JB_Env.get_static_long_field
   .. automethod:: jt.javabridge.JB_Env.get_static_float_field
   .. automethod:: jt.javabridge.JB_Env.get_static_double_field
   .. automethod:: jt.javabridge.JB_Env.set_static_object_field
   .. automethod:: jt.javabridge.JB_Env.set_static_boolean_field
   .. automethod:: jt.javabridge.JB_Env.set_static_byte_field
   .. automethod:: jt.javabridge.JB_Env.set_static_short_field
   .. automethod:: jt.javabridge.JB_Env.set_static_int_field
   .. automethod:: jt.javabridge.JB_Env.set_static_long_field
   .. automethod:: jt.javabridge.JB_Env.set_static_float_field
   .. automethod:: jt.javabridge.JB_Env.set_static_double_field
   .. automethod:: jt.javabridge.JB_Env.get_object_field
   .. automethod:: jt.javabridge.JB_Env.get_boolean_field
   .. automethod:: jt.javabridge.JB_Env.get_byte_field
   .. automethod:: jt.javabridge.JB_Env.get_short_field
   .. automethod:: jt.javabridge.JB_Env.get_int_field
   .. automethod:: jt.javabridge.JB_Env.get_long_field
   .. automethod:: jt.javabridge.JB_Env.get_float_field
   .. automethod:: jt.javabridge.JB_Env.get_double_field
   .. automethod:: jt.javabridge.JB_Env.set_object_field
   .. automethod:: jt.javabridge.JB_Env.set_boolean_field
   .. automethod:: jt.javabridge.JB_Env.set_byte_field
   .. automethod:: jt.javabridge.JB_Env.set_char_field
   .. automethod:: jt.javabridge.JB_Env.set_short_field
   .. automethod:: jt.javabridge.JB_Env.set_long_field
   .. automethod:: jt.javabridge.JB_Env.set_float_field
   .. automethod:: jt.javabridge.JB_Env.set_double_field

   .. line-block:: **String functions**
   
   .. automethod:: jt.javabridge.JB_Env.new_string(u)
   .. automethod:: jt.javabridge.JB_Env.new_string_utf(s)
   .. automethod:: jt.javabridge.JB_Env.get_string(s)
   .. automethod:: jt.javabridge.JB_Env.get_string_utf(s)

   .. line-block:: **Array functions**   
   
   .. automethod:: jt.javabridge.JB_Env.get_array_length(array)
   .. automethod:: jt.javabridge.JB_Env.get_boolean_array_elements(array)
   .. automethod:: jt.javabridge.JB_Env.get_byte_array_elements(array)
   .. automethod:: jt.javabridge.JB_Env.get_short_array_elements(array)
   .. automethod:: jt.javabridge.JB_Env.get_int_array_elements(array)
   .. automethod:: jt.javabridge.JB_Env.get_long_array_elements(array)
   .. automethod:: jt.javabridge.JB_Env.get_float_array_elements(array)
   .. automethod:: jt.javabridge.JB_Env.get_double_array_elements(array)
   .. automethod:: jt.javabridge.JB_Env.get_object_array_elements(array)
   .. automethod:: jt.javabridge.JB_Env.make_boolean_array(array)
   .. automethod:: jt.javabridge.JB_Env.make_byte_array(array)
   .. automethod:: jt.javabridge.JB_Env.make_short_array(array)
   .. automethod:: jt.javabridge.JB_Env.make_int_array(array)
   .. automethod:: jt.javabridge.JB_Env.make_long_array(array)
   .. automethod:: jt.javabridge.JB_Env.make_float_array(array)
   .. automethod:: jt.javabridge.JB_Env.make_double_array(array)
   .. automethod:: jt.javabridge.JB_Env.make_object_array(len, klass)
   .. automethod:: jt.javabridge.JB_Env.set_object_array_element(jbo, index, v)

   .. line-block:: **Exception handling**
   
   .. automethod:: jt.javabridge.JB_Env.exception_occurred()
   .. automethod:: jt.javabridge.JB_Env.exception_describe()
   .. automethod:: jt.javabridge.JB_Env.exception_clear()   
   
.. autoclass:: jt.javabridge.JB_Object
   :members:
