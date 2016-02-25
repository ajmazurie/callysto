
__all__ = (
    "DummyKernel",
    "assertSuccessfulRun",
    "assertUnsuccessfulRun")

import logging
import textwrap
import types

logging.basicConfig(
    format = "[%(asctime)s] %(levelname)s: %(message)s",
    level = 100)  # higher than highest level (CRITICAL = 50)

import callysto

# dummy kernel for testing purpose; its default do_execute_() method
# merely echoes the user input code, and the send_response() doesn't
# actually communicate with the Jupyter server but stores the frames
# for further analysis.
class DummyKernel (callysto.BaseKernel):
    def do_execute_ (self, code):
        yield code

    def send_response (self, *args):
        self._last_results.append(args)

    def update_executor (self, function):
        self.do_execute_ = types.MethodType(function, self)

# run a piece of code on a kernel (subclass of DummyKernel)
# and return the frames that were going to be send to Jupyter
def _execute (kernel, code):
    assert (isinstance(kernel, DummyKernel))
    kernel._last_results = []

    status_message = kernel.do_execute(
        code = textwrap.dedent(code),
        silent = False,
        store_history = False,
        user_expressions = False,
        allow_stdin = False)

    return (status_message, kernel._last_results)

def assertSuccessfulRun (unit_class, kernel, code, expected_results):
    status_message, results = _execute(kernel, code)

    if (not status_message["status"] == "ok"):
        raise Exception(status_message)

    unit_class.assertEqual(status_message["status"], "ok")
    unit_class.assertEqual(len(results), len(expected_results))

    for (result, expected_result) in zip(results, expected_results):
        _, target, data = result

        if (target == "stream"):
            unit_class.assertEqual(data["name"], "stdout")
            unit_class.assertEqual(data["text"].strip(), expected_result)

        elif (target == "display_data"):
            unit_class.assertEqual(data["data"], expected_result)

def assertUnsuccessfulRun (unit_class, kernel, code, exception_validator = None, expected_results = None):
    status_message, results = _execute(kernel, code)

    if (expected_results is None):
        expected_results = [None]

    unit_class.assertEqual(status_message["status"], "error")
    if (exception_validator is not None):
        unit_class.assertTrue(exception_validator(status_message))

    unit_class.assertEqual(len(results), len(expected_results))

    for (result, expected_result) in zip(results, expected_results):
        _, target, data = result

        if (expected_result is None):
            unit_class.assertEqual(data["name"], "stderr")
        else:
            if (target == "stream"):
                unit_class.assertEqual(data["name"], "stdout")
                unit_class.assertEqual(data["text"].strip(), expected_result)

            elif (target == "display_data"):
                unit_class.assertEqual(data["data"], expected_result)
