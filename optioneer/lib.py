import re
from collections import namedtuple
from contextlib import contextmanager
import warnings

RegisteredOption = namedtuple('RegisteredOption',
                              'key default_value doc validator callback')
DeprecatedOption = namedtuple('DeprecatedOption', 'key msg rkey removal_version')


class OptioneerError(AttributeError, KeyError):
    """
    Exception for optioneer, backwards compatible with KeyError
    checks
    """


class Options(object):
    """ provide attribute-style access to a nested dict"""

    def __init__(self, config, d, prefix=""):
        object.__setattr__(self, "_config", config)
        object.__setattr__(self, "d", d)
        object.__setattr__(self, "prefix", prefix)

    def __setattr__(self, key, value):
        prefix = object.__getattribute__(self, "prefix")
        if prefix:
            prefix += "."
        prefix += key
        # you can't set new keys
        # can you can't overwrite subtrees
        if key in self.d and not isinstance(self.d[key], dict):
            self._config._set_option(prefix, value)
        else:
            msg = "You can only set the value of existing options"
            raise OptioneerError(msg)

    def __getattr__(self, key):
        prefix = object.__getattribute__(self, "prefix")
        if prefix:
            prefix += "."
        prefix += key
        try:
            value = object.__getattribute__(self, "d")[key]
        except KeyError:
            raise OptioneerError("No such option")
        if isinstance(value, dict):
            return self.__class__(self._config, value, prefix)
        else:
            return self._config._get_option(prefix)

    def __dir__(self):
        return list(self.d.keys())

    def __repr__(self):
        cls = self.__class__.__name__
        prefix = self.prefix
        space = "\n  "
        description = self._config.describe_option(prefix, print_desc=False)
        description = description.replace('\n', space)
        return "{}({}{})".format(cls, space, description)


_get_option_tmpl = """
get_option(pat)

Retrieves the value of the specified option.

Available options:

{opts_list}

Parameters
----------
pat : str
    Regexp which should match a single option.
    Note: partial matches are supported for convenience, but unless you use the
    full option name (e.g. x.y.z.option_name), your code may break in future
    versions if new options with similar names are introduced.

Returns
-------
result : the value of the option

Raises
------
OptionError : if no such option exists

Notes
-----
The available options with its descriptions:

{opts_desc}
"""

_set_option_tmpl = """
set_option(pat, value)

Sets the value of the specified option.

Available options:

{opts_list}

Parameters
----------
pat : str
    Regexp which should match a single option.
    Note: partial matches are supported for convenience, but unless you use the
    full option name (e.g. x.y.z.option_name), your code may break in future
    versions if new options with similar names are introduced.
value :
    new value of option.

Returns
-------
None

Raises
------
OptionError if no such option exists

Notes
-----
The available options with its descriptions:

{opts_desc}
"""

_describe_option_tmpl = """
describe_option(pat, _print_desc=False)

Prints the description for one or more registered options.

Call with not arguments to get a listing for all registered options.

Available options:

{opts_list}

Parameters
----------
pat : str
    Regexp pattern. All matching keys will have their description displayed.
_print_desc : bool, default True
    If True (default) the description(s) will be printed to stdout.
    Otherwise, the description(s) will be returned as a unicode string
    (for testing).

Returns
-------
None by default, the description(s) as a unicode string if _print_desc
is False

Notes
-----
The available options with its descriptions:

{opts_desc}
"""

_reset_option_tmpl = """
reset_option(pat)

Reset one or more options to their default value.

Pass "all" as argument to reset all options.

Available options:

{opts_list}

Parameters
----------
pat : str/regex
    If specified only options matching `prefix*` will be reset.
    Note: partial matches are supported for convenience, but unless you
    use the full option name (e.g. x.y.z.option_name), your code may break
    in future versions if new options with similar names are introduced.

Returns
-------
None

Notes
-----
The available options with its descriptions:

{opts_desc}
"""


def is_type_factory(type_):
    """

    Parameters
    ----------
    `type_` - a type to be compared against (e.g. type(x) == `type_`)

    Returns
    -------
    validator - a function of a single argument x , which raises
                ValueError if type(x) is not equal to `type_`

    """

    def inner(self, x):
        if type(x) != type_:
            msg = "Value must have type '{typ!s}'"
            raise ValueError(msg.format(typ=type_))

    return inner


def is_instance_factory(type_):
    """

    Parameters
    ----------
    `type_` - the type to be checked against

    Returns
    -------
    validator - a function of a single argument x , which raises
                ValueError if x is not an instance of `type_`

    """
    if isinstance(type_, (tuple, list)):
        type_ = tuple(type_)
        type_repr = "|".join(map(str, type_))
    else:
        type_repr = "'{typ}'".format(typ=type_)

    def inner(self, x):
        if not isinstance(x, type_):
            msg = "Value must be an instance of {type_repr}"
            raise ValueError(msg.format(type_repr=type_repr))

    return inner


def is_one_of_factory(legal_values):
    callables = [c for c in legal_values if callable(c)]
    legal_values = [c for c in legal_values if not callable(c)]

    def inner(x):
        if x not in legal_values:

            if not any(c(x) for c in callables):
                pp_values = "|".join(map(str, legal_values))
                msg = "Value must be one of {pp_values}"
                if len(callables):
                    msg += " or a callable"
                raise ValueError(msg.format(pp_values=pp_values))

    return inner


class CallableDynamicDoc(object):
    # For user convenience, we'd like to have the available options described
    # in the docstring. For dev convenience we'd like to generate the
    # docstrings dynamically instead of maintaining them by hand. To this,
    # we use the class below which wraps functions inside a callable, and
    # converts __doc__ into a property function. The docstrings below are
    # templates using the py2.6+ advanced formatting syntax to plug in a
    # concise list of options, and option descriptions.

    def __init__(self, obj, func, doc_tmpl):
        self.__doc_tmpl__ = doc_tmpl
        self.obj = obj
        self.__func__ = func

    def __call__(self, *args, **kwds):
        return self.__func__(*args, **kwds)

    @property
    def __doc__(self):
        opts_desc = self.obj._describe_option('all', print_desc=False)
        keys = list(self.obj._registered_options.keys())
        opts_list = self.obj.pp_options_list(keys)
        return self.__doc_tmpl__.format(opts_desc=opts_desc,
                                        opts_list=opts_list)


class Optioneer:
    """
    The Optioneer class configures an options object and provides
    a uniform API for working with options.

    Overview
    ========

    This class supports the following requirements:
    - options are referenced using keys in dot.notation, e.g. "x.y.option - z".
    - keys are case-insensitive.
    - functions should accept partial/regex keys, when unambiguous.
    - options can be registered at init-time
    - options have a default value, and (optionally) a description and
      validation function associated with them.
    - options can be deprecated, in which case referencing them
      should produce a warning.
    - deprecated options can optionally be rerouted to a replacement
      so that accessing a deprecated option reroutes to a differently
      named option.
    - options can be reset to their default value.
    - all option can be reset to their default value at once.
    - all options in a certain sub - namespace can be reset at once.
    - the user can set / get / reset or ask for the description of an option.
    - a developer can register and mark an option as deprecated.
    - you can register a callback to be invoked when the option value
      is set or reset. Changing the stored value is considered misuse, but
      is not verboten.

    Implementation
    ==============

    - Data is stored using nested dictionaries, and should be accessed
      through the provided API.

    - "Registered options" and "Deprecated options" have metadata associated
      with them, which are stored in auxiliary dictionaries keyed on the
      fully-qualified key, e.g. "x.y.z.option".

    - your config module should be imported by the package's __init__.py file.
      placing any register_option() calls there will ensure those options
      are available as soon as your package is loaded. If you use
      register_option in a module, it will only be available after that module
      is imported,Options which you should be aware of.

    - `config_prefix` is a context_manager (for use with the `with` keyword)
      which can save developers some typing, see the docstring.
    """
    def __init__(self):
        self._deprecated_options = {}  # holds deprecated option metadata
        self._registered_options = {}  # holds registered option metadata
        self._global_config = {}  # holds current values for registered options
        self._reserved_keys = ['all']  # keys which have a special meaning
        self.options = Options(config=self, d=self._global_config)

        # bind the methods with their docstrings into a callable
        # and use that as the functions exposed in the instance
        self.get_option = CallableDynamicDoc(self, self._get_option,
                                             _get_option_tmpl)
        self.set_option = CallableDynamicDoc(self, self._set_option,
                                             _set_option_tmpl)
        self.reset_option = CallableDynamicDoc(self, self._reset_option,
                                               _reset_option_tmpl)
        self.describe_option = CallableDynamicDoc(self, self._describe_option,
                                                  _describe_option_tmpl)

    def _get_single_key(self, pat, silent):
        keys = self._select_options(pat)
        if len(keys) == 0:
            if not silent:
                self._warn_if_deprecated(pat)
            raise OptioneerError('No such keys(s): {pat!r}'.format(pat=pat))
        if len(keys) > 1:
            raise OptioneerError('Pattern matched multiple keys')
        key = keys[0]

        if not silent:
            self._warn_if_deprecated(key)

        key = self._translate_key(key)

        return key

    def _get_option(self, pat, silent=False):
        key = self._get_single_key(pat, silent)

        # walk the nested dict
        root, k = self._get_root(key)
        return root[k]

    def _set_option(self, *args, **kwargs):
        # must at least 1 arg deal with constraints later
        nargs = len(args)
        if not nargs or nargs % 2 != 0:
            raise ValueError("Must provide an even number of non-keyword "
                             "arguments")

        # default to false
        silent = kwargs.pop('silent', False)

        if kwargs:
            msg = '_set_option() got an unexpected keyword argument "{kwarg}"'
            raise TypeError(msg.format(list(kwargs.keys())[0]))

        for k, v in zip(args[::2], args[1::2]):
            key = self._get_single_key(k, silent)

            option = self._get_registered_option(key)
            if option and option.validator:
                option.validator(v)

            # walk the nested dict
            root, k = self._get_root(key)
            root[k] = v

            if option.callback:
                if silent:
                    with warnings.catch_warnings(record=True):
                        option.callback(key)
                else:
                    option.callback(key)

    def _describe_option(self, pat='', print_desc=True):

        keys = self._select_options(pat)
        if len(keys) == 0:
            raise OptioneerError('No such keys(s)')

        description = u''
        for key in keys:  # filter by pat
            description += self._build_option_description(key)

        if print_desc:
            print(description)
        else:
            return description

    def _reset_option(self, pat, silent=False):

        keys = self._select_options(pat)

        if len(keys) == 0:
            raise OptioneerError('No such keys(s)')

        if len(keys) > 1 and len(pat) < 4 and pat != 'all':
            raise ValueError('You must specify at least 4 characters when '
                             'resetting multiple keys, use the special '
                             'keyword "all" to reset all the options to '
                             'their default value')

        for key in keys:
            self._set_option(key, self._registered_options[key].default_value,
                             silent=silent)

    def get_default_value(self, pat):
        key = self._get_single_key(pat, silent=True)
        return self._get_registered_option(key).default_value

    @contextmanager
    def option_context(self, *args):
        """
        Context manager to temporarily set options in a `with` statement context.

        You need to invoke as ``option_context(pat, val, [(pat, val), ...])``.

        Examples
        --------

        >>> with option_context('display.max_rows', 10, 'display.max_columns', 5):
        ...     ...
        """
        if not (len(args) % 2 == 0 and len(args) >= 2):
            raise ValueError('Need to invoke as'
                             ' option_context(pat, val, [(pat, val), ...]).')

        ops = list(zip(args[::2], args[1::2]))

        undo = []
        for pat, val in ops:
            undo.append((pat, self._get_option(pat, silent=True)))

        for pat, val in ops:
            self._set_option(pat, val, silent=True)

        yield self.options

        if undo:
            for pat, val in undo:
                self._set_option(pat, val, silent=True)

    def register_option(self, key, default_value, doc='',
                        validator=None, callback=None):
        """Register an option in the config object

        Parameters
        ----------
        key           - a fully-qualified key, e.g. "x.y.option - z".
        default_value - the default value of the option
        doc           - a string description of the option
        validator     - a function of a single argument, should raise
                        `ValueError` if called with a value which is not
                        a legal value for the option.
        callback      - a function of a single argument `key`, which is
                        called immediately after an option value is set/reset.
                        `key` is the full name of the option.

        Returns
        -------
        Nothing.

        Raises
        ------
        ValueError if `validator` is set and `default_value` is not a
            valid value.

        """
        import tokenize
        import keyword
        key = key.lower()

        if key in self._registered_options:
            msg = "Option '{key}' has already been registered"
            raise OptioneerError(msg.format(key=key))
        if key in self._reserved_keys:
            msg = "Option '{key}' is a reserved key"
            raise OptioneerError(msg.format(key=key))

        # the default value should be legal
        if validator:
            validator(default_value)

        # walk the nested dict, creating dicts as needed along the path
        path = key.split('.')

        for k in path:
            if not bool(re.match('^' + tokenize.Name + '$', k)):
                raise ValueError("{k} is not a valid identifier".format(k=k))
            if keyword.iskeyword(k):
                raise ValueError("{k} is a python keyword".format(k=k))

        cursor = self._global_config
        msg = "Path prefix to option '{option}' is already an option"
        for i, p in enumerate(path[:-1]):
            if not isinstance(cursor, dict):
                raise OptioneerError(msg.format(option='.'.join(path[:i])))
            if p not in cursor:
                cursor[p] = {}
            cursor = cursor[p]

        if not isinstance(cursor, dict):
            raise OptioneerError(msg.format(option='.'.join(path[:-1])))

        cursor[path[-1]] = default_value  # initialize

        # save the option metadata
        self._registered_options[key] = RegisteredOption(
            key=key, default_value=default_value, doc=doc,
            validator=validator, callback=callback)

    def deprecate_option(self, key, msg=None, redirect_key=None, removal_version=None):
        """
        Mark option `key` as deprecated, if code attempts to access this
        option, a warning will be produced, using `msg` if given, or a
        default message if not.
        if `redirect_key` is given, any access to the key will be re-routed
        to `redirect_key`.

        Neither the existence of `key` nor that if `redirect_key` is checked.
        If they do not exist, any subsequent access will fail as usual,
        after the deprecation warning is given.

        Parameters
        ----------
        key - the name of the option to be deprecated. must be a
                fully-qualified option name (e.g "x.y.z.redirect_key").

        msg - (Optional) a warning message to output when the key is referenced
              if no message is given a default message will be emitted.

        redirect_key - (Optional) the name of an option to redirect access to.
                       If specified, any referenced `key` will be re-routed to
                       `redirect_key` including set/get/reset.
                       `redirect_key` must be a fully-qualified option name
                       (e.g "x.y.z.redirect_key") used by the default message if no
                       `msg` is specified.

        removal_version - (Optional) specifies the version in which this option
                      will be removed. used by the default message if no `msg`
                      is specified.

        Returns
        -------
        Nothing

        Raises
        ------
        OptionError - if key has already been deprecated.
        """
        key = key.lower()

        if key in self._deprecated_options:
            msg = "Option '{key}' has already been defined as deprecated."
            raise OptioneerError(msg.format(key=key))

        self._deprecated_options[key] = DeprecatedOption(key, msg,
                                                         redirect_key, removal_version)

    #
    # functions internal to the class

    def _select_options(self, pat):
        """returns a list of keys matching `pat`

        if pat=="all", returns all registered options
        """

        # short-circuit for exact key
        if pat in self._registered_options:
            return [pat]

        # else look through all of them
        keys = sorted(self._registered_options.keys())
        if pat == 'all':  # reserved key
            return keys

        return [k for k in keys if re.search(pat, k, re.I)]

    def _get_root(self, key):
        path = key.split('.')
        cursor = self._global_config
        for p in path[:-1]:
            cursor = cursor[p]
        return cursor, path[-1]

    def _is_deprecated(self, key):
        """ Returns True if the given option has been deprecated """

        key = key.lower()
        return key in self._deprecated_options

    def _get_deprecated_option(self, key):
        """
        Retrieves the metadata for a deprecated option, if `key` is deprecated.

        Returns
        -------
        DeprecatedOption (namedtuple) if key is deprecated, None otherwise
        """

        try:
            deprecated_option = self._deprecated_options[key]
        except KeyError:
            return None
        else:
            return deprecated_option

    def _get_registered_option(self, key):
        """
        Retrieves the option metadata if `key` is a registered option.

        Returns
        -------
        RegisteredOption (namedtuple) if key is deprecated, None otherwise
        """
        return self._registered_options.get(key)

    def _translate_key(self, key):
        """
        if key id deprecated and a replacement key defined, will return the
        replacement key, otherwise returns `key` as - is
        """

        deprecated_option = self._get_deprecated_option(key)
        if deprecated_option:
            return deprecated_option.rkey or key
        else:
            return key

    def _warn_if_deprecated(self, key):
        """
        Checks if `key` is a deprecated option and if so, prints a warning.

        Returns
        -------
        bool - True if `key` is deprecated, False otherwise.
        """

        deprecated_option = self._get_deprecated_option(key)
        if deprecated_option:
            if deprecated_option.msg:
                print(deprecated_option.msg)
                warnings.warn(deprecated_option.msg, FutureWarning)
            else:
                msg = "'{key}' is deprecated".format(key=key)
                if deprecated_option.removal_version:
                    msg += (' and will be removed in {version}'
                            .format(version=deprecated_option.removal_version))
                if deprecated_option.rkey:
                    msg += (", please use '{rkey}' instead."
                            .format(rkey=deprecated_option.rkey))
                else:
                    msg += ', please refrain from using it.'

                warnings.warn(msg, FutureWarning)
            return True
        return False

    def _build_option_description(self, key):
        """
        Builds a formatted description of a registered option and prints it.
        """

        option = self._get_registered_option(key)
        deprecated_option = self._get_deprecated_option(key)

        description = u'{key}: '.format(key=key)

        if option.doc:
            description += u'\n'.join(option.doc.strip().split('\n'))
        else:
            description += u'No description available.'

        if option:
            description += (u'\n    [default: {default}] [currently: {cur}]'
                            .format(default=option.default_value,
                                    cur=self._get_option(key, True)))

        if deprecated_option:
            description += u'\n    (Deprecated'
            description += (u', use `{rkey}` instead.'
                  .format(rkey=deprecated_option.rkey
                          if deprecated_option.rkey else u''))
            description += u')'

        description += '\n'
        return description

    def pp_options_list(self, keys, width=80, _print=False):
        """
        Builds a concise listing of available options, grouped by prefix.
        """

        from textwrap import wrap
        from itertools import groupby

        def pp(name, ks):
            pfx = ('- ' + name + '.[' if name else '')
            ls = wrap(', '.join(ks), width, initial_indent=pfx,
                      subsequent_indent='  ', break_long_words=False)
            if ls and ls[-1] and name:
                ls[-1] = ls[-1] + ']'
            return ls

        ls = []
        singles = [x for x in sorted(keys) if x.find('.') < 0]
        if singles:
            ls += pp('', singles)
        keys = [x for x in keys if x.find('.') >= 0]

        for k, g in groupby(sorted(keys), lambda x: x[:x.rfind('.')]):
            ks = [x[len(k) + 1:] for x in list(g)]
            ls += pp(k, ks)
        s = '\n'.join(ls)
        if _print:
            print(s)
        else:
            return s

    #
    # helpers

    @contextmanager
    def config_prefix(self, prefix):
        """
        context manager for multiple invocations of API with a common prefix.

        supported API functions: (register / get / set )__option.

        Warning: This is not thread - safe, and won't work properly if you
        import the API functions into your module using the "from x import y"
        construct.

        Example:

        import my_module.config as cf
        with cf.config_prefix("display.font"):
            cf.register_option("color", "red")
            cf.register_option("size", " 5 pt")
            cf.set_option(size, " 6 pt")
            cf.get_option(size)
            ...

            etc'

        will register options "display.font.color", "display.font.size",
        set the value of "display.font.size"... and so on.
        """

        def wrap(func):
            def inner(key, *args, **kwds):
                pkey = '{prefix}.{key}'.format(prefix=prefix, key=key)
                return func(pkey, *args, **kwds)

            return inner

        _register_option = self.register_option
        _get_option = self.get_option
        _set_option = self.set_option
        self.set_option = wrap(_set_option)
        self.get_option = wrap(_get_option)
        self.register_option = wrap(_register_option)
        yield None
        self.set_option = _set_option
        self.get_option = _get_option
        self.register_option = _register_option

    # These factories and methods are handy for use as the validator
    # arg in register_option

    # common type validators, for convenience
    # usage: register_option(... , validator = config.is_int)
    is_int = is_type_factory(int)
    is_bool = is_type_factory(bool)
    is_float = is_type_factory(float)
    is_str = is_type_factory(str)
    is_text = is_instance_factory((str, bytes))

    @staticmethod
    def is_callable(obj):
        """
        check for callabiliby of an object.

        Parameters
        ----------
        `obj` - the object to be checked

        Returns
        -------
        validator - returns True if object is callable
            raises ValueError otherwise.

        """
        if not callable(obj):
            raise ValueError("Value must be a callable")
        return True
