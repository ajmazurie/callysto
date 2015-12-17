
import functools
import logging
import re

import docopt

import utils

_logger = logging.getLogger(__file__)

class MagicCommandException (Exception):
    pass

class MagicCommandsManager:
    def __init__ (self):
        self._magic_commands_prefix = '%'
        self._magic_commands = {}

    def set_prefix (self, prefix):
        if (not utils.is_string(prefix)) or (len(prefix) != 1):
            raise ValueError("invalid value for prefix: must be a character")
        self._magic_commands_prefix = prefix

    def get_prefix (self):
        return self._magic_commands_prefix

    prefix = property(get_prefix, set_prefix)

    def _declare_command (self,
        name, callback_function, doc, overwrite, is_pre_flight):
        if (not utils.is_string(name)):
            raise ValueError(
                "invalid value for name: must be a string")
        if (not utils.is_callable(callback_function)):
            raise ValueError(
                "invalid value for callback_function: must be a callable")

        if (doc is None):
            doc = callback_function.__doc__

        if (self.has_command(name) and (not overwrite)):
            raise Exception("magic command '%s' already defined" % name)

        def _wrapper (args, *inputs):
            if (doc is None):
                kwargs = {}
            else:
                kwargs = docopt.docopt(doc, args, help = True)
                # note: we explicitly remove keys without values
                for key, value in kwargs.items():
                    if (value is None):
                        del kwargs[key]
                    else:
                        kwargs[key] = value.strip().strip('"').strip("'")

            _logger.debug(
                "executing %s-flight command '%s' (callback function: %s)" % (
                    "pre" if is_pre_flight else "post",
                    name.lower(), callback_function))

            return callback_function(*inputs, **kwargs)

        self._magic_commands[name.lower()] = (_wrapper, is_pre_flight)

        _logger.debug("added %s-flight command '%s' (callback function: %s)" % (
            "pre" if is_pre_flight else "post",
            name.lower(), callback_function))

    def declare_pre_flight_command (self,
        name, callback_function, doc = None, overwrite = False):
        """ Declare a pre-flight magic command; i.e., a command
            that will be executed on a cell's content prior to
            the processing of this cell by the kernel
        """
        self._declare_command(
            name, callback_function, doc, overwrite, True)

    def declare_post_flight_command (self,
        name, callback_function, doc = None, overwrite = False):
        """ Declare a post-flight magic command; i.e., a command
            that will be executed on the result of the processing
            of a cell's content by the kernel
        """
        self._declare_command(
            name, callback_function, doc, overwrite, False)

    def has_command (self, name):
        return (name.lower() in self._magic_commands)

    def remove_command (self, name):
        if (not self.has_command(name)):
            raise ValueError("magic command not found: %s" % name)
        del self._magic_commands[name.lower()]

    def parse_code (self, code):
        # detect magic commands, removing them from the input code
        pre_flight_commands, post_flight_commands, code_ = [], [], []
        for line in code.splitlines():
            if (line.strip().startswith(self.prefix)):
                line = line.strip()[1:]

                argv = line.split(' ', 1)
                name, args = argv[0], None if (len(argv) == 1) else argv[1]
                if (not self.has_command(name)):
                    raise MagicCommandException(
                        "unknown magic command: %s" % name)

                command, is_pre_flight = self._magic_commands[name.lower()]

                if (is_pre_flight):
                    pre_flight_commands.append((name,
                        functools.partial(command, args)))#lambda code: command(args, code)))
                    _logger.debug("%s %s" % (command, pre_flight_commands[-1]))
                else:
                    post_flight_commands.append((name,
                        functools.partial(command, args)))#lambda code, results: command(args, code, results)))
            else:
                code_.append(line)

        return (
            pre_flight_commands,
            post_flight_commands,
            '\n'.join(code_))
