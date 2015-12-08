# Example Bash kernel, mimicking a terminal; adapted from
# 'bash_kernel' (https://github.com/takluyver/bash_kernel/)

__all__ = ("BashKernel",)

import logging
import re
import signal

from pexpect import replwrap, EOF

import callysto

_logger = logging.getLogger(__file__)

class BashKernel (callysto.BaseKernel):
    implementation_name = "Bash Kernel"
    implementation_version = "0.0"

    language_name = "bash"
    language_mimetype = "text/x-sh"
    language_file_extension = ".sh"

    def do_startup_ (self, **kwargs):
        # we set the signal handler for SIGNIT to SIG_DFL (default function)
        # for the underlying BASH child process to be interruptible; we need
        # to do it now since we won't be able to do it from the child process
        previous_handler = signal.signal(signal.SIGINT, signal.SIG_DFL)
        try:
            self._bash = replwrap.bash()
        finally:
            # then we set it back to its original value
            signal.signal(signal.SIGINT, previous_handler)

    def do_execute_ (self, code):
        try:
            # send any command to the underlying BASH process,
            # then send the results to the Jupyter notebook
            yield self._bash.run_command(code.strip(), timeout = None)

            # retrieve the exit code of the last executed command
            try:
                exit_code = int(self._bash.run_command("echo $?").strip())
            except:
                exit_code = 1

            # if different from zero,
            if (exit_code != 0):
                # send whatever text the process sent
                # so far to the Jupyter notebook
                yield self._bash.child.before

                # then raise an exception
                raise Exception(
                    "process returned a non-zero exit code: %d" % exit_code)

        except KeyboardInterrupt as exception:
            # if the user used a keyboard interrupt, we
            # propagate it to the underlying BASH process
            self._bash.child.sendintr()
            self._bash._expect_prompt()

            yield self._bash.child.before
            raise exception

        except EOF:
            yield self._bash.child.before
            self.do_startup_()

if (__name__ == "__main__"):
    callysto.launch_kernel(BashKernel, debug = True)
