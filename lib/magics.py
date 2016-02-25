
import functools
import logging
import re

import docopt

import utils

_logger = logging.getLogger(__name__)

class MagicCommandsManager:
    def __init__ (self):
        self._magic_commands_prefix = '%'
        self._magic_commands = {}

    def set_prefix (self, prefix):
        if (not utils.is_string(prefix)) or (len(prefix) != 1):
            raise ValueError("Invalid value for prefix: must be a character")
        self._magic_commands_prefix = prefix

    def get_prefix (self):
        return self._magic_commands_prefix

    prefix = property(get_prefix, set_prefix)

    def _declare_command (self,
        name, callback_function, doc, overwrite, is_pre_flight):

        if (not utils.is_string(name)):
            raise ValueError(
                "Invalid value for magic command name: "
                "Must be a string")

        if (not utils.is_callable(callback_function)):
            raise ValueError(
                "Invalid value for magic command callback function: "
                "Must be a callable")

        if (doc is None):
            doc = callback_function.__doc__

        if (self.has_command(name) and (not overwrite)):
            raise Exception(
                "Invalid value for magic command name: "
                "Name '%s' already taken" % name)

        def _wrapper (doc, mc_args, *args_from_kernel):
            if (doc is None):
                kwargs = {}
            else:
                # we parse the arguments using docopt
                try:
                    if (mc_args is None):
                        mc_args = ''
                    kwargs = docopt.docopt(doc, mc_args, help = True)

                except docopt.DocoptExit as exception:
                    usage = ' '.join(map(
                        lambda x: x.strip(), str(exception).splitlines()))
                    raise Exception("Invalid syntax, %s" % usage)

                # we explicitly remove keys without values
                for (key, value) in kwargs.items():
                    if (value is None):
                        del kwargs[key]
                    else:
                        # remove any surrounding quotes
                        # and whitespaces from the value
                        kwargs[key] = re.sub(r"^['\"\s]|['\"\s]$", '', value)

            _logger.debug(
                "executing %s-flight command '%s' "
                "(callback function: %s)" % (
                    "pre" if is_pre_flight else "post",
                    name.lower(), callback_function))

            return callback_function(*args_from_kernel, **kwargs)

        self._magic_commands[name.lower()] = (
            functools.partial(_wrapper, doc), is_pre_flight)

        _logger.debug(
            "added %s-flight command '%s' (callback function: %s)" % (
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
            raise ValueError("Unknown magic command: %s" % name)
        del self._magic_commands[name.lower()]

    def _parse_code (self, code):
        # detect magic commands, removing them from the input code
        pre_flight_commands, post_flight_commands, code_ = [], [], []

        for line in code.splitlines():
            if (line.strip().startswith(self.prefix)):
                line = line.strip()[1:]

                mc_argv = line.split(' ', 1)
                mc_args = None if (len(mc_argv) == 1) else mc_argv[1]

                mc_name = mc_argv[0]
                if (not self.has_command(mc_name)):
                    raise Exception("Unknown magic command: %s" % mc_name)

                mc, is_pre_flight = self._magic_commands[mc_name.lower()]
                if (is_pre_flight):
                    commands = pre_flight_commands
                else:
                    commands = post_flight_commands

                commands.append((mc_name, functools.partial(mc, mc_args)))
            else:
                code_.append(line)

        return (
            pre_flight_commands,
            post_flight_commands,
            '\n'.join(code_))
