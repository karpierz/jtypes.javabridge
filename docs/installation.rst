Installation and testing
========================

Install using pip
-----------------

::

    python -m pip install --upgrade jtypes.javabridge[numpy]  # with numpy - not mandatory but highly recommended
    python -m pip install --upgrade jtypes.javabridge


Dependencies
------------

The *jtypes.javabridge* requires Python 3.9 or above, NumPy (not mandatory
but highly recommended) and the Java Runtime Environment (JRE).

Linux
^^^^^

On CentOS 6, the dependencies can be installed as follows::

    sudo yum install numpy java
    curl -O https://raw.github.com/pypa/pip/master/contrib/get-pip.py
    python get-pip.py

On Fedora 19, the dependencies can be installed as follows::

    sudo yum install numpy java python-pip openssl

On Ubuntu 14 and Debian 8, the dependencies can be installed as follows::

   sudo apt-get install default-jre python-pip python-numpy

On Arch Linux, the dependencies can be installed as follows::

   sudo pacman -S jre-openjdk python-pip python-numpy

MacOS X
^^^^^^^

1. Install the Xcode command-line tools. There are two ways:

   A. Install Xcode from the Mac App Store. (You can also download it
      from Apple's Mac Dev Center, but that may require membership in
      the Apple Developer Program.) Install the Xcode command-line
      tools by starting Xcode, going to Preferences, click on
      "Downloads" in the toolbar, and click the "Install" button on
      the line "Command Line Tools." For MacOS 10.9 and Xcode 5 and
      above, you may have to install the command-line tools by typing
      ``xcode-select --install`` and following the prompts.

   B. Download the Xcode command-line tools from Apple's Mac Dev
      Center and install. This may require membership in the Apple
      Developer Program.

2. Create and activate a `virtualenv` virtual environment if you don't
   want to clutter up your system-wide python installation with new
   packages.

3. ``python -m pip install --upgrade jtypes.javabridge[numpy]``  # with numpy - not mandatory but highly recommended
   ``python -m pip install --upgrade jtypes.javabridge``

Windows
^^^^^^^

You should install a Java Runtime Environment (JRE) or Java Development Kit
(JDK) appropriate for your Java project. The Windows build is tested with the
Oracle JRE/JDK 1.8. Note that the bitness needs to match your python: if you
use a 32-bit Python, then you need a 32-bit JRE/JDK; if you use a 64-bit
Python, then you need a 64-bit JRE/JDK.

The paths to PIP and Python should be in your PATH. The following steps should
perform the install:

1. Run Command Prompt as administrator. Set the path to Python and PIP if
   needed, e.g. (if Python and PIP installed to the default locations)::

        ``set PATH=%PATH%;c:\\Python312;c:\\Python312\\Scripts``

2. Issue the command::

        python -m pip install --upgrade jtypes.javabridge[numpy]  # with numpy - not mandatory but highly recommended
        python -m pip install --upgrade jtypes.javabridge


Running the unit tests
----------------------

1. Build and install in the source code tree so that the unit tests can run::

    python setup.py develop

2. Run the unit tests::

    python -m jt.javabridge.tests

You must build the extensions in-place on Windows, then run tests
if you use setup to run the tests::

    python setup.py build_ext -i
    python setup.py test

See the section :ref:`unit-testing` for how to run unit tests for your
own projects that use *jtypes.javabridge*.
