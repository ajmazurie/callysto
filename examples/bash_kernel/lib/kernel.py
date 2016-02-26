"""
Example Bash kernel, mimicking a terminal; adapted from
'bash_kernel' (https://github.com/takluyver/bash_kernel/)

TO DO: add SSH connection through magic command
"""

__all__ = ("BashKernel",)

import getpass
import logging
import re
import signal

from pexpect import EOF
import pexpect.replwrap
import pexpect.pxssh

import callysto

_logger = logging.getLogger(__name__)

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
            self._local_repl = pexpect.replwrap.bash()
            self._ssh_repl = None
        finally:
            # then we set it back to its original value
            signal.signal(signal.SIGINT, previous_handler)

        self.declare_pre_flight_command(
            "ssh-login", self.connect_with_ssh)

        self.declare_pre_flight_command(
            "ssh-logout", self.disconnect_from_ssh)

    def connect_with_ssh (self, code, **kwargs):
        """ Usage: ssh-login <ADDRESS> [--user STRING] [--password STRING]

            Options:
                <ADDRESS>           hostname
                --user STRING       username
                --password STRING   password
        """
        if (self._ssh_repl is not None):
            raise Exception("A SSH connection is already up")

        hostname = kwargs["<ADDRESS>"]
        username = kwargs.get("--user", getpass.getuser())
        password = kwargs.get("--password", '')

        _logger.debug("SSH logging to %s@%s" % (username, hostname))

        try:
            connection = pexpect.pxssh.pxssh(echo = False)
            connection.login(hostname, username, password)

        except pexpect.pxssh.ExceptionPxssh as exception:
            raise Exception("Unable to log to %s: %s" % (hostname, exception))

        _logger.debug("SSH logging: done")

        class SSHREPLWrapper (pexpect.replwrap.REPLWrapper):
            def _expect_prompt (self, timeout = -1):
                self.child.prompt(timeout)

        self._ssh_repl = SSHREPLWrapper(
            connection, connection.PROMPT, None)

    def disconnect_from_ssh (self, code, **kwargs):
        """ Usage: ssh-logout
        """
        if (self._ssh_repl is not None):
            _logger.debug("SSH logging out")
            self._ssh_repl.child.logout()
            _logger.debug("SSH logging out: done")
            self._ssh_repl = None

    def do_execute_ (self, code):
        if (self._ssh_repl is not None):
            repl = self._ssh_repl
        else:
            repl = self._local_repl

        try:
            # send any command to the underlying BASH process,
            # then send the results to the Jupyter notebook
            yield repl.run_command(code.strip(), timeout = None)

            # retrieve the exit code of the last executed command
            try:
                exit_code = int(repl.run_command("echo $?").strip())
            except:
                exit_code = 1

            # if different from zero,
            if (exit_code != 0):
                # send whatever text the process sent
                # so far to the Jupyter notebook
                content = repl.child.before
                if (content.strip() != str(exit_code)):
                    yield content

                # then raise an exception
                raise Exception(
                    "Process returned a non-zero exit code: %d" % exit_code)

        except KeyboardInterrupt as exception:
            # if the user used a keyboard interrupt, we
            # propagate it to the underlying BASH process
            repl.child.sendintr()
            repl._expect_prompt()

            yield repl.child.before
            raise exception

        except EOF:
            yield repl.child.before
            self.do_startup_()

if (__name__ == "__main__"):
    BashKernel.launch(debug = True)
