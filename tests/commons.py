
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

class DummyKernel (callysto.BaseKernel):
    def do_execute_ (self, code):
        return code

    def send_response (self, *args):
        self._last_results.append(args)

    def update_executor (self, function):
        self.do_execute_ = types.MethodType(function, self)

def _execute (kernel, code):
    code = textwrap.dedent(code)
    kernel._last_results = []

    status_message = kernel.do_execute(
        code = code, silent = False,
        store_history = False,
        user_expressions = False,
        allow_stdin = False)

    return status_message, kernel._last_results

def assertSuccessfulRun (unit_class, kernel, code, expected_results):
    status_message, results = _execute(kernel, code)

    unit_class.assertEqual(status_message["status"], "ok")
    unit_class.assertEqual(len(results), len(expected_results))

    for result, expected_result in zip(results, expected_results):
        _, target, data = result

        if (target == "stream"):
            unit_class.assertEqual(data["name"], "stdout")
            unit_class.assertEqual(data["text"], expected_result)

        elif (target == "display_data"):
            unit_class.assertEqual(data["data"], expected_result)

def assertUnsuccessfulRun (unit_class, kernel, code, expected_results):
    status_message, results = _execute(kernel, code)

    unit_class.assertEqual(status_message["status"], "error")
    unit_class.assertEqual(len(results), len(expected_results))

    for result, expected_result in zip(results, expected_results):
        _, target, data = result

        if (expected_result is None):
            unit_class.assertEqual(data["name"], "stderr")
        else:
            if (target == "stream"):
                unit_class.assertEqual(data["name"], "stdout")
                unit_class.assertEqual(data["text"], expected_result)

            elif (target == "display_data"):
                unit_class.assertEqual(data["data"], expected_result)
