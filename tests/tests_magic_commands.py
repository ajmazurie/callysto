
from commons import *

import operator
import types
import unittest

class MagicCommandsTests (unittest.TestCase):

    def test_setting_magic_commands_prefix (self):
        dummy_kernel = DummyKernel()

        dummy_kernel.magic_commands.prefix = "!"
        self.assertEqual(dummy_kernel.magic_commands.prefix, "!")

    def test_adding_magic_command (self):
        dummy_kernel = DummyKernel()

        dummy_kernel.magic_commands.declare_pre_flight_command(
            "pre-flight", lambda x: None)
        self.assertTrue(
            dummy_kernel.magic_commands.has_command("pre-flight"))

        dummy_kernel.magic_commands.declare_post_flight_command(
            "post-flight", lambda x: None)
        self.assertTrue(
            dummy_kernel.magic_commands.has_command("post-flight"))

        dummy_kernel.magic_commands.remove_command("pre-flight")
        self.assertFalse(
            dummy_kernel.magic_commands.has_command("pre-flight"))

        dummy_kernel.magic_commands.remove_command("post-flight")
        self.assertFalse(
            dummy_kernel.magic_commands.has_command("post-flight"))

    def test_pre_flight_commands (self):
        dummy_kernel = DummyKernel()
        dummy_kernel.magic_commands.prefix = '!' # non-default prefix

        class PreFlight:
            was_run = False

            # command without parameter
            def command_1 (self, code):
                self.was_run = True
                return code.upper()

            # command with parameter
            def command_2 (self, code, **kwargs):
                """ Dummy pre-flight command

                    Usage:
                        command_2 [--prefix STRING] [--suffix STRING]

                    Options:
                        --prefix STRING  Prefix [default: (]
                        --suffix STRING  Suffix [default: )]
                """
                self.was_run = True
                prefix = kwargs["--prefix"]
                suffix = kwargs["--suffix"]

                return prefix + code + suffix

            # command throwing an exception
            def command_3 (self, code):
                raise Exception("dummy_error")

        pre_flight = PreFlight()

        dummy_kernel.magic_commands.declare_pre_flight_command(
            "pre-flight-1", pre_flight.command_1)

        dummy_kernel.magic_commands.declare_pre_flight_command(
            "pre-flight-2", pre_flight.command_2)

        dummy_kernel.magic_commands.declare_pre_flight_command(
            "pre-flight-3", pre_flight.command_3)

        # without the magic command
        code = "test"
        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands.parse_code(code)

        self.assertEqual(len(pre_flight_commands), 0)
        self.assertEqual(len(post_flight_commands), 0)

        status_message, results = execute_code(dummy_kernel, code)

        self.assertFalse(pre_flight.was_run)
        pre_flight.was_run = False

        self.assertEqual(status_message["status"], "ok")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][2]["text"], code)

        # with the magic command
        code = """
            !pre-flight-1
            test
            """

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands.parse_code(code)

        self.assertEqual(len(pre_flight_commands), 1)
        self.assertEqual(len(post_flight_commands), 0)

        self.assertEqual(pre_flight_commands[0][0], "pre-flight-1")

        status_message, results = execute_code(dummy_kernel, code)

        self.assertTrue(pre_flight.was_run)
        pre_flight.was_run = False

        self.assertEqual(status_message["status"], "ok")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][2]["text"], "\nTEST")

        # after removing the magic command
        dummy_kernel.magic_commands.remove_command("pre-flight-1")

        # ... any code referring to it should fail
        status_message, results = execute_code(dummy_kernel, code)

        self.assertEqual(status_message["status"], "error")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][2]["name"], "stderr")

        # ... but not code not referring to it
        status_message, results = execute_code(dummy_kernel, "test")

        self.assertEqual(status_message["status"], "ok")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][2]["text"], "test")

        # with the parameterized magic command
        code = """
            !pre-flight-2 --prefix [
            test
            """

        status_message, results = execute_code(dummy_kernel, code)

        self.assertTrue(pre_flight.was_run)
        pre_flight.was_run = False

        self.assertEqual(status_message["status"], "ok")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][2]["text"], "[\ntest)")

        # with the exception-raising command
        code = """
            !pre-flight-3
            test
            """

        status_message, results = execute_code(dummy_kernel, code)

        self.assertFalse(pre_flight.was_run)
        pre_flight.was_run = False

        self.assertEqual(status_message["status"], "error")
        self.assertTrue(status_message["evalue"].endswith("dummy_error"))

    def test_post_flight_commands (self):
        dummy_kernel = DummyKernel()
        dummy_kernel.magic_commands.prefix = '!' # non-default prefix

        def executor (self, code, allow_stdin):
            return list(code.strip())

        dummy_kernel.do_execute_ = types.MethodType(executor, dummy_kernel)

        class PostFlight:
            was_run = False

            # command without parameters
            def command_1 (self, code, results):
                self.was_run = True
                return reversed(results)

            # command with parameters
            def command_2 (self, code, results, **kwargs):
                """ Dummy post-flight command

                    Usage:
                        command_2 [--prefix STRING] [--suffix STRING]

                    Options:
                        --prefix STRING  Prefix [default: (]
                        --suffix STRING  Suffix [default: )]
                """
                self.was_run = True
                prefix = kwargs["--prefix"]
                suffix = kwargs["--suffix"]

                return [prefix + result + suffix for result in results]

            # command throwing an exception
            def command_3 (self, code, results):
                raise Exception("dummy_error")

        post_flight = PostFlight()

        dummy_kernel.magic_commands.declare_post_flight_command(
            "post-flight-1", post_flight.command_1)

        dummy_kernel.magic_commands.declare_post_flight_command(
            "post-flight-2", post_flight.command_2)

        dummy_kernel.magic_commands.declare_post_flight_command(
            "post-flight-3", post_flight.command_3)

        # without the magic command
        code = "test"
        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands.parse_code(code)

        self.assertEqual(len(pre_flight_commands), 0)
        self.assertEqual(len(post_flight_commands), 0)

        status_message, results = execute_code(dummy_kernel, code)

        self.assertFalse(post_flight.was_run)
        post_flight.was_run = False

        self.assertEqual(status_message["status"], "ok")
        self.assertEqual(len(results), 4)
        self.assertEqual(
            map(operator.itemgetter("text"),
            map(operator.itemgetter(2), results)),
            ["t", "e", "s", "t"])

        # with the magic command
        code = """
            !post-flight-1
            test
            """

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands.parse_code(code)

        self.assertFalse(post_flight.was_run)
        post_flight.was_run = False

        self.assertEqual(len(pre_flight_commands), 0)
        self.assertEqual(len(post_flight_commands), 1)

        self.assertEqual(post_flight_commands[0][0], "post-flight-1")

        status_message, results = execute_code(dummy_kernel, code)

        self.assertTrue(post_flight.was_run)
        post_flight.was_run = False

        self.assertEqual(status_message["status"], "ok")
        self.assertEqual(len(results), 4)
        self.assertEqual(
            map(operator.itemgetter("text"),
            map(operator.itemgetter(2), results)),
            ["t", "s", "e", "t"])

        # after removing the magic command
        dummy_kernel.magic_commands.remove_command("post-flight-1")

        # ... any code referring to it should fail
        status_message, results = execute_code(dummy_kernel, code)

        self.assertFalse(post_flight.was_run)
        post_flight.was_run = False

        self.assertEqual(status_message["status"], "error")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][2]["name"], "stderr")

        # ... but not code not referring to it
        status_message, results = execute_code(dummy_kernel, "test")

        self.assertFalse(post_flight.was_run)
        post_flight.was_run = False

        self.assertEqual(status_message["status"], "ok")
        self.assertEqual(len(results), 4)
        self.assertEqual(
            map(operator.itemgetter("text"),
            map(operator.itemgetter(2), results)),
            ["t", "e", "s", "t"])

        # with the parameterized magic command
        code = """
            !post-flight-2 --prefix [
            test
            """

        status_message, results = execute_code(dummy_kernel, code)

        self.assertTrue(post_flight.was_run)
        post_flight.was_run = False

        self.assertEqual(status_message["status"], "ok")
        self.assertEqual(len(results), 4)
        self.assertEqual(
            map(operator.itemgetter("text"),
            map(operator.itemgetter(2), results)),
            ["[t)", "[e)", "[s)", "[t)"])

        # with the exception-raising command
        code = """
            !post-flight-3
            test
            """

        status_message, results = execute_code(dummy_kernel, code)

        self.assertFalse(post_flight.was_run)
        post_flight.was_run = False

        self.assertEqual(status_message["status"], "error")
        self.assertTrue(status_message["evalue"].endswith("dummy_error"))

if (__name__ == "__main__"):
    unittest.main()
