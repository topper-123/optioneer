=========
optioneer
=========


.. image:: https://img.shields.io/pypi/v/optioneer.svg
        :target: https://pypi.python.org/pypi/optioneer

.. image:: https://img.shields.io/pypi/status/optioneer.svg
        :target: https://pypi.python.org/pypi/optioneer

.. image:: https://travis-ci.com/topper-123/optioneer.svg?branch=master
    :target: https://travis-ci.com/topper-123/optioneer

.. image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
    :target: https://github.com/topper-123/optioneer/blob/master/LICENSE

.. image:: https://img.shields.io/pypi/pyversions/optioneer.svg
    :target: https://pypi.python.org/pypi/optioneer

Optioneer makes in-program options, that:

* are nestable and groupable,
* are tab-able in the REPL for easy options discoverability
* give each option a optional doc string, for easily explaining the option
* may deprecate according to a transparent deprecation cycle
* may be validated upon change
* can do custom  callbacks

Optioneer is based on the ``core/config.py`` module in
`pandas <https.//pandas.pydata.org>`_.

Installation
------------

Installing is easy using pip:

.. code-block:: bash

    pip install optioneer

Usage guide
-----------
In a ``config.py`` file set up your options:

.. code-block:: python

    from optioneer import Optioneer
    options_maker = Optioneer()
    options_maker.register_option('api_key', 'abcdefg')
    options_maker.register_option('display.width', 200, doc='Width of our display')
    options_maker.register_option('display.height', 200, doc='Height of our display')
    options_maker.register_option('color', 'red', validator=options_maker.is_str)

    options = options_maker.options

Then, in the relevant location of your library, just do
``from config import options`` and you're got your options set up.

Users of your library can now access the options from the relevant location
in your package, e.g. if you've made it available in the top-level
``__init__.py`` of a package called ``mylib``:

>>> import mylib
>>> import mylib.options
Options(
  api_key: No description available.
      [default: abcdefg] [currently: abcdefg]
  color: No description available.
      [default: red] [currently: red]
  display.height: Height of our display
      [default: 200] [currently: 200]
  display.width: Width of our display
      [default: 200] [currently: 200]
  )

Notice how the repr output shows the relevant options and their descriptions.

The relevant options are discoverable using tabs in the REPL:

>>> mylib.options.<TAB>
option.api_key options.color options.display
>>> mylib.options.display.<TAB>
options.display.height options.display.width

You can also easily see the options and their values and docs for subgroups in
the repr string:

>>> mylib.options.display
Options(
  display.height: Height of our display
      [default: 200] [currently: 200]
  display.width: Width of our display
      [default: 200] [currently: 200]
  )

Callbacks
---------
By providing a callback when registering options, changing options may trigger
a desired actions. For example, if you in your ``config.py`` do:

.. code-block:: python

    options_maker.register_option('shout', True, callback=lambda x: print("YEAH!"))

Then the user, when changing that option will see:

>>> mylib.options.shout = False
YEAH!

Of course, the callback can be more realistic than above, e.g. logging or
setting some internal option or something else.

Deprecating options
-------------------

If you want to deprecate an option, ``optioneer`` allows you to do that:

.. code-block:: python

    options_maker.deprecate_option('api_key', msg='An api key is no longer needed')

Now your users get a deprecation warning, if they access this option:

>>> mylib.options.api_key
An api key is no longer needed
C:\Users\TP\Documents\Python\optioneer\optioneer\lib.py:677: FutureWarning: An api key is no longer needed
  warnings.warn(deprecated_option.msg, FutureWarning)
Out[20]: 'abcdefg'

If an options should be renamed and/or a marker should be for when the option will
be removed, that is also possible:

.. code-block:: python

    options_maker.register_option('display.length', 300, doc='Length of our display')
    options_maker.deprecate_option('display.height', redirect_key='display.length',
                                   removal_version='v1.3')

Then accessing the option will show

>>> mylib.options.display.height
C:\Users\TP\Documents\Python\optioneer\optioneer\lib.py:689: FutureWarning: 'display.height' is deprecated and will be removed in v1.3, please use 'display.length' instead.
  warnings.warn(msg, FutureWarning)
Out[24]: 300

Deprecated options will not show up in repr output or when tab-completing.

Dependencies
------------
Optioneer has no external dependencies.

Optioneer uses pytest for testing.

License
-------
Optioneer is BSD 3-licensed.
