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

``optioneer`` makes in-program options, that:

* can be nested and grouped,
* can be discovered in the REPL when tab-completing,
* can give each option a doc string, for easily explaining the option
* may deprecate options according to a transparent deprecation cycle
* may validate options when they're changed
* can do custom callbacks

``optioneer`` does not do CLI options, but is used strictly to create in-program
options.

As such, its best use case is probably to create options for library code
that is used by other programs. In fact, ``optioneer`` is a reworked and
self-contained version of the ``core/config.py`` module in
`pandas <https.//pandas.pydata.org>`_ and options created by ``optioneer``
work very similarly to ``pandas.options``.

Installation
------------

Installing is easy using pip:

.. code-block:: bash

    pip install optioneer

Usage guide
-----------
In a ``config.py`` file in your package set up your options:

.. code-block:: python

    from optioneer import Optioneer

    options_maker = Optioneer()
    options_maker.register_option('api_key', 'abcdefg', doc='The API key to our service')
    options_maker.register_option('display.width', 200, doc='Width of our display')
    options_maker.register_option('display.height', 200, doc='Height of our display')
    options_maker.register_option('color', 'red', validator=options_maker.is_str)

    options = options_maker.options

Then, in the relevant location of your library, just do
``from .config import options`` and you've got your options set up.

Users of your library can now access the options from the chosen location
in your package. For example, if you've made it available in the top-level
``__init__.py`` of a package called ``mylib``:

.. code-block:: python

    >>> import mylib
    >>> import mylib.options
    Options(
      api_key: The API key to our service.
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

.. code-block:: python

    >>> mylib.options.<TAB>
    option.api_key options.color options.display
    >>> mylib.options.display.<TAB>
    options.display.height options.display.width

You can also easily see the options and their values and docs for subgroups in
the repr string:

.. code-block:: python

    >>> mylib.options.display
    Options(
      display.height: Height of our display
          [default: 200] [currently: 200]
      display.width: Width of our display
          [default: 200] [currently: 200]
      )

Callbacks
---------
By providing a callback when registering options, changed options may trigger
a desired actions. For example, if you in your ``config.py`` do:

.. code-block:: python

    def callback_func(key, value):
        print("key: {!r} value: {!r}".format(key, value))
    options_maker.register_option('a.args', True, callback=callback_func)

Then changing that option will trigger the callback:

.. code-block:: python

    >>> mylib.options.args = False
    key: 'a.args' value: False

Of course, the callback can be more realistic than in the example above, e.g.
logging or setting some internal option or something else.

Deprecating options
-------------------

If you need to deprecate an option, ``optioneer`` allows you to do that:

.. code-block:: python

    options_maker.deprecate_option('api_key', msg='An api key is no longer needed')

Now your users get a deprecation warning, if they access this option:

.. code-block:: python

    >>> mylib.options.api_key
    An api key is no longer needed
    C:\Users\TP\Documents\Python\optioneer\optioneer\lib.py:677: FutureWarning: An api key is no longer needed
      warnings.warn(deprecated_option.msg, FutureWarning)
    Out[20]: 'abcdefg'

If an options should be renamed and/or a marker should be set for when the
option will be removed, that is also possible:

.. code-block:: python

    options_maker.register_option('display.length', 300, doc='Length of our display')
    options_maker.deprecate_option('display.height', redirect_key='display.length',
                                   removal_version='v1.3')

Then accessing the ``display.height`` option will show

.. code-block:: python

    >>> mylib.options.display.height
    C:\Users\TP\Documents\Python\optioneer\optioneer\lib.py:689: FutureWarning: 'display.height' is deprecated and will be removed in v1.3, please use 'display.length' instead.
      warnings.warn(msg, FutureWarning)
    Out[24]: 300

Deprecated options will not show up in the repr output or when tab-completing.

Dependencies
------------
``optioneer`` has no external dependencies.

``optioneer`` uses pytest for testing.

License
-------
``optioneer`` is BSD 3-licensed.
