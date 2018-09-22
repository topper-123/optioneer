Usage guide
-----------

Optioneer makes in-program options, that:

* are nestable and groupable,
* are tab-able in the REPL for easy options discoverability
* give each option a optional doc string, for easily explaining the option
* may deprecate according to a transparent deprecation cycle
* may be validated upon change
* can do custom  callbacks

Examples
--------
In a ``config.py`` file set up your options:

>>> from optioneer import Optioneer
>>> opt_maker = Optioneer()
>>> opt_maker.register_option('api_key', 'abcdefg')
>>> opt_maker.register_option('display.width', 200, doc='Width of our display')
>>> opt_maker.register_option('display.height', 200, doc='Height of our display')
>>> opt_maker.register_option('color', 'red', validator=opt_maker.is_str)
>>> options = opt_maker.options

Then, in the relevant location of your library, just do
``from config import options`` and you're got your options set up.

Notice that the options allow options discovery using tab in the REPL:

>>> options.<TAB>
option.api_key options.color options.display
>>> options.display.<TAB>
options.display.height options.display.width

You can also easily see the options and their values and docs in the repr string:

>>> options
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
>>> options.display
Options(
  display.height: Height of our display
      [default: 200] [currently: 200]
  display.width: Width of our display
      [default: 200] [currently: 200]
  )

Callbacks
---------
By providing a callback when registering options, changing options may trigger
a desired actions. For example:

>>> opt_maker.register_option('shout', True, callback=lambda x: print("YEAH!"))
>>> options.shout = False
YEAH!

Of course, the callback can be more realistic than above, e.g. logging or setting
some internal option on a class or something else.

Deprecating options
-------------------

If you want to deprecate an option, ``optioneer`` allows you to do that:

>>> opt_maker.deprecate_option('api_key', msg='An api key is no longer needed')

Now your users get a deprecation warning, if they access this option:

>>> options.api_key
An api key is no longer needed
C:\Users\TP\Documents\Python\optioneer\optioneer\lib.py:677: FutureWarning: An api key is no longer needed
  warnings.warn(deprecated_option.msg, FutureWarning)
Out[20]: 'abcdefg'

If an options should be renamed and/or a marker should be for when the option will
be removed, that is also possible:

>>> opt_maker.register_option('display.length', 300, doc='Length of our display')
>>> opt_maker.deprecate_option('display.height', redirect_key='display.length',
...                            removal_version='v1.3')
>>> options.display.height
C:\Users\TP\Documents\Python\optioneer\optioneer\lib.py:689: FutureWarning: 'display.height' is deprecated and will be removed in v1.3, please use 'display.length' instead.
  warnings.warn(msg, FutureWarning)
Out[24]: 300
