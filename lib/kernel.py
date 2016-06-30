
__all__ = (
    "BaseKernel",)

import inspect
import json
import logging
import logging.config
import shutil
import sys, os
import tempfile
import traceback

import future.utils
import ipykernel.kernelapp
import ipykernel.kernelbase
import jupyter_client.kernelspec

import magics
import renderers.core
import utils

_logger = logging.getLogger(__name__)

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

        # expose shortcuts to the magic commands and renderers API
        self.magic_commands = magics.MagicCommandsManager()

        self.declare_pre_flight_command = \
            self.magic_commands.declare_pre_flight_command

        self.declare_post_flight_command = \
            self.magic_commands.declare_post_flight_command

        self.register_renderer = renderers.core.register_renderer
        self.deregister_renderer = renderers.core.deregister_renderer

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
            # extract pre/post flight commands, if any
            pre_flight_commands, post_flight_commands, user_code = \
                self.magic_commands._parse_code(code)

            # if there is no user code nor pre/post flight commands, do nothing
            if (user_code.strip() == '') and \
               (len(pre_flight_commands) == 0) and \
               (len(post_flight_commands) == 0):
                return

            # (1/4) execute pre-flight magic commands, if any
            for (mc_name, mc_function) in pre_flight_commands:
                try:
                    # input: string; output: string (or None)
                    mc_output = mc_function(user_code)

                except Exception as exception:
                    future.utils.raise_with_traceback(Exception(
                        "Error while running pre-flight command '%s': "
                        "%s" % (mc_name, exception)))

                # output, if any, becomes the new user code
                if (mc_output is not None):
                    assert utils.is_string(mc_output), (
                        "Invalid return value for pre-flight "
                        "magic command '%s': Must be a string" % mc_name)
                    user_code = mc_output

            # (2/4) pass the user code to the kernel and retrieve frames
            if (user_code.strip() == ''):
                result_frames = []
            else:
                try:
                    _logger.debug("executing:\n%s" % user_code)
                    # input: string; output: generator
                    result_frames = self.do_execute_(user_code)
                    result_frames = renderers.core._check_frames(result_frames)
                    _logger.debug("executing: done")

                except Exception as exception:
                    future.utils.raise_with_traceback(Exception(
                        "Error while evaluating user code: %s" % exception))

            # (3/4) execute post-flight magic commands, if any
            for (mc_name, mc_function) in post_flight_commands:
                try:
                    # input: generator; output: generator
                    mc_output = mc_function(user_code, result_frames)
                    mc_output = renderers.core._check_frames(mc_output)

                except Exception as exception:
                    future.utils.raise_with_traceback(Exception(
                        "Error while running post-flight command '%s': "
                        "%s" % (mc_name, exception)))

                # output becomes the new result frame(s)
                result_frames = mc_output

            # (4/4) render the kernel results and send them to the notebook
            if (silent):
                _logger.debug("emitting nothing (silent notebook)")
            else:
                n_frames, n_subframes = 0, 0
                for (mime_type, content, metadata) in result_frames:
                    # feed the content to any compatible renderer and
                    # send the resulting sub-frame(s) to the notebook
                    try:
                        subframes = renderers.core._render_content(
                            mime_type, content, metadata)

                    except Exception as exception:
                        future.utils.raise_with_traceback(Exception(exception))

                    for (mime_type_, content_, metadata_) in subframes:
                        length_ = len(content_)
                        metadata_ = {} if (metadata_ is None) else metadata_

                        if (mime_type_ == "text/plain"):
                            _logger.debug("emitting text"
                                " (%d %s)" % (
                                    len(content_),
                                    utils.plural("character", length_)))

                            response = ("stream", {
                                "name": "stdout",
                                "text": unicode(content_)})
                        else:
                            _logger.debug("emitting data"
                                " (%s, %d %s, metadata = %s)" % (
                                    mime_type_,
                                    len(content_),
                                    utils.plural("byte", length_),
                                    metadata_))

                            response = ("display_data", {
                                "metadata": metadata_,
                                "data": {mime_type_: content_}})

                        self.send_response(self.iopub_socket, *response)
                        n_subframes += 1

                    n_frames += 1

                _logger.debug("emitted %d %s from %d %s" % (
                    n_subframes, utils.plural("subframe", n_subframes),
                    n_frames, utils.plural("frame", n_frames)))

        except KeyboardInterrupt:
            msg = "Execution aborted by user"

            _logger.error(msg)
            self.send_response(self.iopub_socket, "stream",
                {"name": "stderr", "text": msg})

            return {
                "status": "abort",
                "execution_count": self.execution_count}

        except Exception as exception:
            # retrieve the exception message (last line of traceback)
            exc_type, exc_value, exc_traceback = sys.exc_info()

            msg = traceback.format_exception_only(
                exc_type, exc_value)[0].strip()

            # if the exception is of type Exception, we strip the type
            if (msg.startswith("Exception: ")):
                msg = msg[11:]

            # if the exception has no message attached, says so explicitly
            if (str(exc_value).strip() == ''):
                msg += "(no message)"

            self.send_response(self.iopub_socket, "stream",
                {"name": "stderr", "text": msg})

            # create a more detailed error message for the
            # logger, including the whole stack trace
            stack, msg_ = traceback.extract_tb(exc_traceback), msg
            for (file_name, line, func_name, text) in stack:
                msg_ += "\n%s:%d in %s: %s" % (
                    file_name, line, func_name, text)

            _logger.error(msg_)

            return {
                "status": "error",
                "execution_count": self.execution_count,
                "ename": exc_type.__name__,
                "evalue": msg,
                "traceback": stack}

        # the execution happened without error
        return {
            "status": "ok",
            "execution_count": self.execution_count,
            "payload": [],  # deprecated
            "user_expressions": {}}

    def do_execute_ (self, code):
        yield

    @classmethod
    def launch (cls, debug = None):
        """ Launch a singleton instance of this kernel

            Note that this is a blocking operation; no more than one
            kernel instance can be launched from the same thread.
        """
        if (debug is None):
            debug = str(os.getenv("CALLYSTO_DEBUG", ""))
            debug = (debug.lower() in ("1", "true", "yes"))

        logging.config.dictConfig({
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "custom_formatter": {
                    "format": "[%(asctime)s] %(levelname)s: %(message)s"}},
            "handlers": {
                "custom_handler": {
                    "class": "logging.StreamHandler",
                    "formatter": "custom_formatter"}},
            "loggers": {"": {
                "handlers": ["custom_handler"],
                "level": logging.DEBUG if (debug) else logging.INFO,
                "propagate": True}}})

        if (debug):
            _logger.info("running in debug mode")

        _logger.debug("starting kernel application using %s" % cls)
        ipykernel.kernelapp.IPKernelApp.launch_instance(kernel_class = cls)
        _logger.debug("stopping kernel application using %s" % cls)

    @classmethod
    def install (cls, all_users = False, prefix = None):
        """ Install this kernel
        """
        # create the kernel specifications file
        kspec = {
            "argv": [
                "python",
                "-m", inspect.getmodule(cls).__name__,
                "-f", "{connection_file}"],
            "display_name": cls.implementation_name,
            "language": cls.language_name}

        _logger.debug("kernel specifications: %s" % kspec)

        kspec_path = tempfile.mkdtemp()
        kspec_fn = os.path.join(kspec_path, "kernel.json")

        json.dump(kspec, open(kspec_fn, "w"),
            indent = 4, sort_keys = True, separators = (',', ': '))

        # install the kernel specifications file
        kspec_manager = jupyter_client.kernelspec.KernelSpecManager()
        kspec_manager.install_kernel_spec(
            kspec_path,
            kernel_name = cls.implementation_name,
            user = not all_users,
            prefix = prefix)

        shutil.rmtree(kspec_path)
