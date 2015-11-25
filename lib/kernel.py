
__all__ = (
    "BaseKernel",
    "launch_kernel")

import ipykernel.kernelapp
import ipykernel.kernelbase
import ipywidgets

import mimetype
import utils

import logging

_logger = logging.getLogger(__file__)

class BaseKernel (ipykernel.kernelbase.Kernel):
    implementation_name = "KERNEL_IMPLEMENTATION_NAME_PLACEHOLDER"
    implementation_version = "KERNEL_VERSION_PLACEHOLDER"
    implementation = implementation_name

    language_name = "KERNEL_LANGUAGE_NAME_PLACEHOLDER"
    language_mimetype = "KERNEL_LANGUAGE_MIMETYPE_PLACEHOLDER"
    language_version = "KERNEL_LANGUAGE_VERSION_PLACEHOLDER"
    language_file_extension = "KERNEL_LANGUAGE_FILE_EXTENSION_PLACEHOLDER"
    language = language_name

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

    def __init__ (self, **kwargs):
        _logger.debug("initializing kernel instance %s" % self)

        ipykernel.kernelbase.Kernel.__init__(self, **kwargs)
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
        was_interrupted = False
        was_successful = True

        try:
            if (code.strip() == ''):
                return

            _logger.debug("executing:\n%s" % code)
            results = self.do_execute_(code, allow_stdin)
            _logger.debug("executing: done")

            # display the execution results, if wanted
            if (silent):
                _logger.debug("emitting nothing (silent notebook)")

            elif (results is not None):
                # ensure that the results are a list
                if (utils.is_iterable(results)):
                    results = list(results)
                else:
                    results = [results]

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
                        if (type(content_type) == mimetype.CONTENT):
                            content_type, content = mimetype._process_content(
                                content_type, content)

                        _logger.debug("emitting data (%s, %d bytes)" % (
                            content_type, len(content)))

                        self.send_response(self.iopub_socket,
                            "display_data", {
                                "metadata": {},
                                "data": {content_type: content}})

        except KeyboardInterrupt:
            _logger.error("execution aborted due to interrupt key")
            was_successful = False
            was_interrupted = True

            self.send_response(self.iopub_socket, "stream", {
                "name": "stderr", "text": "error: interrupted by user"})

        except Exception as exception:
            _logger.error("execution aborted due to error: %s" % exception)
            was_successful = False

            self.send_response(self.iopub_socket, "stream", {
                "name": "stderr", "text": "error: %s" % exception})

        # the execution happened without error
        if (was_successful):
            return {
                "status": "ok",
                "execution_count": self.execution_count,
                "payload": [],  # deprecated
                "user_expressions": {}}

        # the execution was interrupted by the user
        if (was_interrupted):
            return {
                "status": "abort",
                "execution_count": self.execution_count}

        # the execution happened with error(s)
        return {
            "status": "error",
            "execution_count": self.execution_count,
            "ename": "error",
            "evalue": 1234,
            "traceback": [str(exception)]}

    def do_execute_ (self, code, allow_stdin):
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
