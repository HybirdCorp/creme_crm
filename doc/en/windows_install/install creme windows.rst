.. _Creme installation on Windows:

How to install Creme CRM on Windows
===================================

:Author: Raphaël BECK
:Version: 2-9-2011 for Creme version 1.1
:Copyright: Hybird
:License: GNU FREE DOCUMENTATION LICENSE version 1.3

Optional
^^^^^^^^
- To maintain your Creme CRM easily updated you can use hg via TortoiseHG

  - Download it from `bitbucket <http://tortoisehg.bitbucket.org/download/index.html>`_ take care to take the good version for your OS (i.e. : 64bits or 32bits)
  - Install it

    .. image:: images/tortoise_1.PNG

    .. image:: images/tortoise_2.PNG

    .. image:: images/tortoise_3.PNG

    .. image:: images/tortoise_4.PNG

    .. image:: images/tortoise_5.PNG

    .. image:: images/tortoise_6.PNG



- To enjoy a complete Creme experience download and install the `latest firefox version <http://www.mozilla.org/firefox/>`_


Installation
============

Download Creme CRM
^^^^^^^^^^^^^^^^^^^^^

If you HAVE installed TortoiseHG:
"""""""""""""""""""""""""""""""""
  - Right click in the folder you want to install Creme
  - TortoiseHG / Clone

    .. image:: images/tortoise_7.png
  - In source enter https://bitbucket.org/hybird/creme_crm

    .. image:: images/tortoise_8.PNG
  - Destination should be the current directory you right clicked in
  - Click clone and wait
  - Then click close, a directory named creme_crm should be appeared

    .. image:: images/tortoise_9.PNG


If you HAVEN'T installed TortoiseHG:
""""""""""""""""""""""""""""""""""""
- Go on https://bitbucket.org/hybird/creme_crm
- Click on get source and select your favorite format (zip or gz or bz2)

  .. image:: images/bitbucket_1.PNG
- Extract sources of Creme from the archive (example for zip archive right clic/extract all)

Download & install
^^^^^^^^^^^^^^^^^^

`Python 2.6.6 <http://www.python.org/getit/releases/2.6.6/>`_
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
- Download & install `64 bits version <http://www.python.org/ftp/python/2.6.6/python-2.6.6.amd64.msi>`_

  .. image:: images/python_1.PNG

  .. image:: images/python_2.PNG

  .. image:: images/python_3.PNG

  .. image:: images/python_4.PNG

- OR `32 bits version <http://www.python.org/ftp/python/2.6.6/python-2.6.6.msi>`_
- Add python directory to the PATH

  - On Windows Seven:

   - Right clic on Computer
   - Advanced system settings
   - Environment Variables
   - Search PATH in System variables, then clic on it and Edit
   - Add the following (assuming python is installed in C:\\Python26)

     - ";C:\\Python26"

       .. image:: images/path_1.PNG

`Wamp <http://www.wampserver.com/download.php#bottom>`_
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
- Download & install 64 bits  `<http://www.wampserver.com/dl64.php>`_
- OR 32 bits `<http://www.wampserver.com/dl32.php>`_

.. image:: images/wamp_1.PNG

.. image:: images/wamp_2.PNG

.. image:: images/wamp_3.PNG

.. image:: images/wamp_4.PNG

.. image:: images/wamp_5.PNG

.. image:: images/wamp_6.PNG

.. image:: images/wamp_7.PNG

.. image:: images/wamp_8.PNG

.. image:: images/wamp_9.PNG

.. image:: images/wamp_10.PNG

.. image:: images/wamp_11.png

.. image:: images/wamp_12.PNG



`MySQL python connector <http://www.codegood.com/archives/4>`_
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
- Download & install 64 bits version `MySQL-python-1.2.2.win-amd64-py2.6.exe <http://www.codegood.com/download/3/>`_

  .. image:: images/mysql-connector_1.PNG

  .. image:: images/mysql-connector_2.PNG
- OR 32 bits version `MySQL-python-1.2.2.win32-py2.6.exe <http://www.codegood.com/download/2/>`_
- 2 DLLs could be required, place them into %WINDIR%\\system32 (Generaly C:\\Windows\\System32)

  - `libguide40.dll <http://www.fichier-dll.fr/libguide40.dll,11261>`_
  - `libmmd.dll <http://www.fichier-dll.fr/libmmd.dll,1970>`_

.. Note ::
    From here, if any installer reports that python2.6 is not found (generally happens on 64bits OS) read [1]_.

Java
""""
- Download from `java.com <http://www.java.com/fr/download/windows_xpi.jsp?locale=fr>`_
- The same way you have done for python in PATH

  - Create JAVA_HOME with the value "C:\\Program Files (x86)\\Java\\jre6" (or the directory where you have installed java, take care of the ")

    .. image:: images/javahome.PNG
  - Add ;"C:\\Program Files (x86)\\Java\\jre6\\bin" in PATH (or the directory where you have installed java, take care of the ")

    .. image:: images/java_path.PNG

`Easy-install <http://pypi.python.org/pypi/setuptools#files>`_
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

It's a python package installer which is really easy to use. You can also install download & install each package by your own without it.

- `setuptools-0.6c11.win32-py2.6.exe <http://pypi.python.org/packages/2.6/s/setuptools/setuptools-0.6c11.win32-py2.6.exe#md5=1509752c3c2e64b5d0f9589aafe053dc>`_

  .. image:: images/easy_install_1.PNG

  .. image:: images/easy_install_2.PNG

How to install a package with easy install
------------------------------------------
  - Type "cmd" in run (or Windows+R)

  - cd C:\\Python26\\Scripts
  - easy_install.exe your_package_name
  - For example easy_install.exe django

    .. image:: images/easy_install_3.PNG

Install following packages
**************************
      .. Note ::
        For some of those packages, you **MAY** need to have a compiler.
        Actually only PIL and pycrypto need to be compiled, so either you can download their installer separately or download one of the following compilers and compile them.

      - `Visual Studio 2008 Express <http://www.microsoft.com/visualstudio/en-us/products/2008-editions/express>`_ take care to get the 2008 version (not 2010 or above)
      - `MinGW <http://sourceforge.net/projects/mingw/files/Automated%20MinGW%20Installer/mingw-get-inst/>`_

        - Download & install the latest

          .. image:: images/mingw_1.PNG

          .. image:: images/mingw_2.PNG

          .. image:: images/mingw_3.PNG

          .. image:: images/mingw_4.PNG

- **Required packages**

  - Django 1.3 (type **django**)
  - Django-mediagenerator 1.10.4 (type **django_mediagenerator**)
  - South 0.7 (type **south**)
  - pytz-2011e (type **pytz**)

- Optionnal packages

  - creme.graphs:

    - pygraphviz (type **pygraphviz**)

    .. Note ::
        Don't forget to install Graphviz first

  - creme.activesync:
      - PIL >= 1.1.7 (type **PIL** or download separately from `effbot <http://effbot.org/downloads/PIL-1.1.7.win32-py2.6.exe>`_)

      - restkit 2.2.1 (type **restkit==2.2.1**)
      - pycrypto 2.3 (type **pycrypto** or download separately from `here <http://www.voidspace.org.uk/downloads/pycrypto-2.3.win32-py2.6.zip>`_ or go to the `complete page <http://www.voidspace.org.uk/python/modules.shtml#pycrypto>`_)

        .. image:: images/pycrypto_1.PNG


Configuration
=============
.. TODO: Configuration title should be as the same level than Installation

- Create the database in mysql

  .. image:: images/wamp_13.PNG
- Enter your settings in creme_crm/creme/settings.py

  .. image:: images/settings_1.PNG
- Open a cmd

  - cd C:\\Users\\%USERNAME%\\Desktop\\creme_crm (assuming you have extracted Creme on the desktop)
  - python manage.py syncdb

    .. image:: images/manage_1.PNG
  - python manage.py migrate
  - python manage.py creme_populate -v
  - python manage.py generatemedia
  - python manage.py runserver
  - Open your browser, go to  `http://127.0.0.1:8000/ <http://127.0.0.1:8000/>`_ and **enjoy** your new instance of Creme


------------------------------

Notes
======
.. [1] Python not found:

- Take a notepad and copy the following into (each line **MUST NOT** begin with a space, a tab, etc)::

    Windows Registry Editor Version 5.00

    [HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\Python]

    [HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\Python\PythonCore]

    [HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\Python\PythonCore\2.6]

    [HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\Python\PythonCore\2.6\Help]

    [HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\Python\PythonCore\2.6\Help\Main Python Documentation]
    @="C:\\Python26\\Doc\\python264.chm"

    [HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\Python\PythonCore\2.6\InstallPath]
    @="C:\\Python26\\"

    [HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\Python\PythonCore\2.6\InstallPath\InstallGroup]
    @="Python 2.6"

    [HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\Python\PythonCore\2.6\Modules]

    [HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\Python\PythonCore\2.6\PythonPath]
    @="C:\\Python26\\Lib;C:\\Python26\\DLLs;C:\\Python26\\Lib\\lib-tk"


- Save the file as something like python-fix-x64.reg (the .reg is really important!)
- Execute it and re-run setuptools







