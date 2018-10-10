# -*- coding: utf-8 -*-

"""``optioneer`` makes in-program options, that:

* can be nested and grouped,
* can be discovered in the REPL when tab-completing,
* can give each option a doc string, for easily explaining the option
* may deprecate options according to a transparent deprecation cycle
* may validate options when they're changed
* can do custom callbacks

``optioneer`` does not do CLI options, but is used strictly to create
in-program options.

Usage guide
-----------
In a ``config.py`` file in your package, set up your options:

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
      api_key: 'abcdefg' [default: 'abcdefg']
          The API key to our service
      color: 'red' [default: 'red']
          No description available.
      display.height: 200 [default: 200]
          Height of our display
      display.width: 200 [default: 200]
          Width of our display
      )
"""

__author__ = """Terji Petersen"""
__email__ = 'contribute@tensortable.com'
__version__ = '1.0.3'

from . import lib
from .lib import Optioneer
