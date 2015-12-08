
__all__ = (
    "BaseKernel",
    "launch_kernel")

import docopt
import ipykernel.kernelapp
import ipykernel.kernelbase
import ipywidgets

import magics
import mimetype
import utils

import traceback
import sys
import logging

_logger = logging.getLogger(__file__)

class ExecutionException (Exception):
    pass

class PreFlightCommandException (magics.MagicCommandException):
    pass

class PostFlightCommandException (magics.MagicCommandException):
    pass

class BaseKernel (ipykernel.kernelbase.Kernel):
    implementation_name = "KERNEL_IMPLEMENTATION_NAME_PLACEHOLDER"
    implementation_version = "KERNEL_VERSION_PLACEHOLDER"

    language_name = "KERNEL_LANGUAGE_NAME_PLACEHOLDER"
    language_mimetype = "KERNEL_LANGUAGE_MIMETYPE_PLACEHOLDER"
    language_version = "KERNEL_LANGUAGE_VERSION_PLACEHOLDER"
    language_file_extension = "KERNEL_LANGUAGE_FILE_EXTENSION_PLACEHOLDER"

    @property
    def banner (self):
        banner_ = "%s %s" % (
            self.implementation_name, self.implementation_version)

        _logger.debug("banner requested; returned \"%s\"" % banner_)
        return banner_

    @property
    def language_info (self):
        language_info_ = {
            "name": self.language_name,
            "version": self.language_version,
            "mimetype": self.language_mimetype,
            "file_extension": self.language_file_extension}

        _logger.debug("language_info requested; returned %s" % language_info_)
        return language_info_

    implementation = implementation_name
    language = language_name

    def __init__ (self, **kwargs):
        _logger.debug("initializing kernel instance %s" % self)
        ipykernel.kernelbase.Kernel.__init__(self, **kwargs)

        self.magic_commands = magics.MagicCommandsManager()
        self.do_startup_(**kwargs)

        _logger.debug("initializing kernel instance %s: done" % self)

    def do_startup_ (self, **kwargs):
        pass

    def do_shutdown (self, restart = False):
        verb = "restarting" if (restart) else "shutting down"
        _logger.debug("%s kernel instance %s" % (verb, self))

        self.do_shutdown_(restart)

        _logger.debug("%s kernel instance %s: done" % (verb, self))

    def do_shutdown_ (self, will_restart = False):
        pass

    def do_execute (self, code, silent,
        store_history, user_expressions, allow_stdin):
        try:
            pre_flight_commands, post_flight_commands, code = \
                self.magic_commands.parse_code(code)

            if (code.strip() == '') and \
               (len(pre_flight_commands) == 0) and \
               (len(post_flight_commands) == 0):
                return

            _logger.debug("executing:\n%s" % code)

            # execute pre-flight magic commands, if any
            for (name, command) in pre_flight_commands:
                try:
                    output = command(code)
                except Exception:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    msg = "error with pre-flight command '%s': %s: %s" % (
                        name, exc_type.__name__, exc_value)
                    raise PreFlightCommandException(msg), None, exc_traceback

                if (output is not None):
                    assert utils.is_string(output), \
                        "invalid return value for pre-flight " + \
                        "magic command '%s': must be a string" % name
                    code = output

            if (code.strip() == ''):
                results = None
            else:
                try:
                    results = self.do_execute_(code)
                except Exception:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    msg = "error: %s: %s" % (exc_type.__name__, exc_value)
                    raise ExecutionException(msg), None, exc_traceback

                if (results is not None):
                    # ensure that the results are a list
                    if (utils.is_iterable(results)):
                        results = list(results)
                    else:
                        results = [results]

            # execute post-flight magic commands, if any
            for (name, command) in post_flight_commands:
                try:
                    output = command(code, results)
                except Exception:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    msg = "error with post-flight command '%s': %s: %s" % (
                        name, exc_type.__name__, exc_value)
                    raise PostFlightCommandException(msg), None, exc_traceback

                if (output is not None):
                    assert utils.is_iterable(output), \
                        "invalid return value for post-flight " + \
                        "magic command '%s': must be an iterable" % name
                    results = output

            _logger.debug("executing: done")

            # display the execution results, if wanted
            if (silent):
                _logger.debug("emitting nothing (silent notebook)")

            elif (results is not None):
                for result in results:
                    if (type(result) in (list, tuple)):
                        content_type, content = result[0], result[1:]
                        if (len(content) == 1):
                            content = content[0]
                    else:
                        content_type, content = None, result

                    # execution result is something that can be printed
                    if (content_type is None):
                        _logger.debug("emitting text (%d characters)" % \
                            len(content))

                        self.send_response(self.iopub_socket,
                            "stream", {
                                "name": "stdout",
                                "text": unicode(content)})

                    # execution result is raw data with a given content type
                    else:
                        # process this content type through IPython.display
                        # and other modules, if a processor is available
                        content_type, content = mimetype._process_content(
                            content_type, content)

                        _logger.debug("emitting data (%s, %d bytes)" % (
                            content_type, len(content)))

                        _logger.debug(content)

                        self.send_response(self.iopub_socket,
                            "display_data", {
                                "metadata": {},
                                "data": {content_type: content}})

        except KeyboardInterrupt:
            msg = "execution aborted by user"

            _logger.error(msg)
            self.send_response(self.iopub_socket, "stream",
                {"name": "stderr", "text": msg})

            return {
                "status": "abort",
                "execution_count": self.execution_count}

        except Exception as exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()

            msg = traceback.format_exception_only(
                exc_type, exc_value)[0].strip()
            if (str(exc_value).strip() == ''):
                msg += "(no message)"

            _logger.error(msg)
            self.send_response(self.iopub_socket, "stream",
                {"name": "stderr", "text": msg})

            return {
                "status": "error",
                "execution_count": self.execution_count,
                "ename": exc_type.__name__,
                "evalue": msg,
                "traceback": traceback.extract_tb(exc_traceback)}

        # the execution happened without error
        return {
            "status": "ok",
            "execution_count": self.execution_count,
            "payload": [],  # deprecated
            "user_expressions": {}}

    def do_execute_ (self, code):
        return

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def _validate_kernel (kernel_class):
    if (not issubclass(kernel_class, BaseKernel)) or \
       (kernel_class == BaseKernel):
        raise ValueError(
            "invalid value for kernel_class (must be a subclass of BaseKernel)")

def launch_kernel (kernel_class, debug = False):
    _validate_kernel(kernel_class)

    if (debug):
        logging.basicConfig(
            format = "[%(asctime)s] %(levelname)s: %(message)s",
            level = logging.DEBUG)

    _logger.debug("launching kernel application using %s" % kernel_class)
    ipykernel.kernelapp.IPKernelApp.launch_instance(kernel_class = kernel_class)
    _logger.debug("stopping kernel application using %s" % kernel_class)
