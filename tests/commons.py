
__all__ = ("DummyKernel", "execute_code")

import logging
import textwrap

logging.basicConfig(
    format = "[%(asctime)s] %(levelname)s: %(message)s",
    level = 100)  # higher than highest level (CRITICAL = 50)

import callysto

class DummyKernel (callysto.BaseKernel):
    def do_execute_ (self, code, allow_stdin):
        return code

    def send_response (self, *args):
        self.last_results.append(args)

def execute_code (kernel, code):
    code = textwrap.dedent(code)
    kernel.last_results = []

    status_message = kernel.do_execute(
        code = code, silent = False,
        store_history = False,
        user_expressions = False,
        allow_stdin = False)

    return (status_message, kernel.last_results)
