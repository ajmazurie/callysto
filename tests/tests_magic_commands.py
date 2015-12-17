
import operator
import unittest

from commons import *

class MagicCommandsTests (unittest.TestCase):

    def test_setting_magic_commands_prefix (self):
        dummy_kernel = DummyKernel()

        dummy_kernel.magic_commands.prefix = "!"
        self.assertEqual(dummy_kernel.magic_commands.prefix, "!")

    def test_adding_magic_command (self):
        dummy_kernel = DummyKernel()

        # we can add pre- and post-flight magic commands
        dummy_kernel.magic_commands.declare_pre_flight_command(
            "pre-flight", lambda x: None)
        self.assertTrue(
            dummy_kernel.magic_commands.has_command("pre-flight"))

        dummy_kernel.magic_commands.declare_post_flight_command(
            "post-flight", lambda x: None)
        self.assertTrue(
            dummy_kernel.magic_commands.has_command("post-flight"))

        # we shouldn't be able to add a magic command twice by default,
        with self.assertRaises(Exception):
            dummy_kernel.magic_commands.declare_pre_flight_command(
                "pre-flight", lambda x: None)

        with self.assertRaises(Exception):
            dummy_kernel.magic_commands.declare_post_flight_command(
                "post-flight", lambda x: None)

        # except if we use the 'overwrite' parameter
        dummy_kernel.magic_commands.declare_pre_flight_command(
            "pre-flight", lambda x: None, overwrite = True)

        dummy_kernel.magic_commands.declare_post_flight_command(
            "post-flight", lambda x: None, overwrite = True)

        # we can remove existing magic commands,
        dummy_kernel.magic_commands.remove_command("pre-flight")
        self.assertFalse(
            dummy_kernel.magic_commands.has_command("pre-flight"))

        dummy_kernel.magic_commands.remove_command("post-flight")
        self.assertFalse(
            dummy_kernel.magic_commands.has_command("post-flight"))

        # but not twice
        with self.assertRaises(ValueError):
            dummy_kernel.magic_commands.remove_command("pre-flight")

        with self.assertRaises(ValueError):
            dummy_kernel.magic_commands.remove_command("post-flight")

    def test_pre_flight_commands (self):
        dummy_kernel = DummyKernel()
        dummy_kernel.magic_commands.prefix = '!' # non-default prefix

        class PreFlightCommands:
            command_1_was_run = False
            command_2_was_run = False
            command_3_was_run = False

            # command without parameter
            def command_1 (self, code):
                self.command_1_was_run = True
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
                self.command_2_was_run = True
                prefix = kwargs["--prefix"]
                suffix = kwargs["--suffix"]

                return prefix + code + suffix

            # command throwing an exception
            def command_3 (self, code):
                self.command_3_was_run = True
                raise Exception("dummy_error")

        pre_flight = PreFlightCommands()

        dummy_kernel.magic_commands.declare_pre_flight_command(
            "pre-flight-1", pre_flight.command_1)

        dummy_kernel.magic_commands.declare_pre_flight_command(
            "pre-flight-2", pre_flight.command_2)

        dummy_kernel.magic_commands.declare_pre_flight_command(
            "pre-flight-3", pre_flight.command_3)

        # without magic commands being mentioned,
        code = "test"

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands.parse_code(code)

        # - none of the magic commands should appear after parsing
        self.assertEqual(len(pre_flight_commands), 0)
        self.assertEqual(len(post_flight_commands), 0)

        # - the code should run without error
        assertSuccessfulRun(self, dummy_kernel, code, [code])

        # - and none of the magic commands should have run
        self.assertFalse(pre_flight.command_1_was_run)
        pre_flight.command_1_was_run = False

        self.assertFalse(pre_flight.command_2_was_run)
        pre_flight.command_2_was_run = False

        self.assertFalse(pre_flight.command_3_was_run)
        pre_flight.command_3_was_run = False

        # with a magic command being mentioned however,
        code = """
            !pre-flight-1
            test
            """

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands.parse_code(code)

        # - this magic command should be mentioned
        self.assertEqual(len(pre_flight_commands), 1)
        self.assertEqual(len(post_flight_commands), 0)
        self.assertEqual(pre_flight_commands[0][0], "pre-flight-1")

        # - the code should run without error
        assertSuccessfulRun(self, dummy_kernel, code, ["\nTEST"])

        # - the magic command referenced should have run
        self.assertTrue(pre_flight.command_1_was_run)
        pre_flight.command_1_was_run = False

        self.assertFalse(pre_flight.command_2_was_run)
        pre_flight.command_2_was_run = False

        self.assertFalse(pre_flight.command_3_was_run)
        pre_flight.command_3_was_run = False

        # after removing the magic command,
        dummy_kernel.magic_commands.remove_command("pre-flight-1")

        # - any code referring to it should fail
        assertUnsuccessfulRun(self, dummy_kernel, code, [None])

        # - the magic command referenced should not have run
        self.assertFalse(pre_flight.command_1_was_run)
        pre_flight.command_1_was_run = False

        self.assertFalse(pre_flight.command_2_was_run)
        pre_flight.command_2_was_run = False

        self.assertFalse(pre_flight.command_3_was_run)
        pre_flight.command_3_was_run = False

        # - any code not referring to it should run
        assertSuccessfulRun(self, dummy_kernel, "test", ["test"])

        # with a parameterized magic command,
        code = """
            !pre-flight-2 --prefix [
            test
            """

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands.parse_code(code)

        # - this magic command should be mentioned
        self.assertEqual(len(pre_flight_commands), 1)
        self.assertEqual(len(post_flight_commands), 0)
        self.assertEqual(pre_flight_commands[0][0], "pre-flight-2")

        # - the code should run without error
        assertSuccessfulRun(self, dummy_kernel, code, ["[\ntest)"])

        # - the magic command referenced should have run
        self.assertFalse(pre_flight.command_1_was_run)
        pre_flight.command_1_was_run = False

        self.assertTrue(pre_flight.command_2_was_run)
        pre_flight.command_2_was_run = False

        self.assertFalse(pre_flight.command_3_was_run)
        pre_flight.command_3_was_run = False

        # with the exception-raising command,
        code = """
            !pre-flight-3
            test
            """

        # - the code should not run
        assertUnsuccessfulRun(self, dummy_kernel, code, [None])

        # - the magic command referenced should have run
        self.assertFalse(pre_flight.command_1_was_run)
        pre_flight.command_1_was_run = False

        self.assertFalse(pre_flight.command_2_was_run)
        pre_flight.command_2_was_run = False

        self.assertTrue(pre_flight.command_3_was_run)
        pre_flight.command_3_was_run = False

        # if we combine several magic commands,
        code = """
            !pre-flight-1
            !pre-flight-2 --suffix ]
            test
            """

        dummy_kernel.magic_commands.declare_pre_flight_command(
            "pre-flight-1", pre_flight.command_1)

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands.parse_code(code)

        # - all these magic commands should be mentioned
        self.assertEqual(len(pre_flight_commands), 2)
        self.assertEqual(len(post_flight_commands), 0)
        self.assertEqual(pre_flight_commands[0][0], "pre-flight-1")
        self.assertEqual(pre_flight_commands[1][0], "pre-flight-2")

        # - the code should run without error
        assertSuccessfulRun(self, dummy_kernel, code, ["(\nTEST]"])

        # - the magic commands referenced should have run
        self.assertTrue(pre_flight.command_1_was_run)
        pre_flight.command_1_was_run = False

        self.assertTrue(pre_flight.command_2_was_run)
        pre_flight.command_2_was_run = False

        self.assertFalse(pre_flight.command_3_was_run)
        pre_flight.command_3_was_run = False

    def test_post_flight_commands (self):
        dummy_kernel = DummyKernel()
        dummy_kernel.magic_commands.prefix = '!' # non-default prefix

        # dummy executor, which split a string into characters
        dummy_kernel.update_executor(lambda self, code: list(code.strip()))

        class PostFlightCommands:
            command_1_was_run = False
            command_2_was_run = False
            command_3_was_run = False

            # command without parameters
            def command_1 (self, code, results):
                self.command_1_was_run = True
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
                self.command_2_was_run = True
                prefix = kwargs["--prefix"]
                suffix = kwargs["--suffix"]

                return [prefix + result + suffix for result in results]

            # command throwing an exception
            def command_3 (self, code, results):
                self.command_3_was_run = True
                raise Exception("dummy_error")

        post_flight = PostFlightCommands()

        dummy_kernel.magic_commands.declare_post_flight_command(
            "post-flight-1", post_flight.command_1)

        dummy_kernel.magic_commands.declare_post_flight_command(
            "post-flight-2", post_flight.command_2)

        dummy_kernel.magic_commands.declare_post_flight_command(
            "post-flight-3", post_flight.command_3)

        # without magic command being mentioned,0
        code = "test"

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands.parse_code(code)

        # - none of the magic commands should appear after parsing
        self.assertEqual(len(pre_flight_commands), 0)
        self.assertEqual(len(post_flight_commands), 0)

        # - the code should run without error
        assertSuccessfulRun(self, dummy_kernel, code,
            ["t", "e", "s", "t"])

        # - and none of the magic commands should have run
        self.assertFalse(post_flight.command_1_was_run)
        post_flight.command_1_was_run = False

        self.assertFalse(post_flight.command_2_was_run)
        post_flight.command_2_was_run = False

        self.assertFalse(post_flight.command_3_was_run)
        post_flight.command_3_was_run = False

        # with a magic command being mentioned however,
        code = """
            !post-flight-1
            test
            """

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands.parse_code(code)

        # - this magic command should be mentioned
        self.assertEqual(len(pre_flight_commands), 0)
        self.assertEqual(len(post_flight_commands), 1)
        self.assertEqual(post_flight_commands[0][0], "post-flight-1")

        # - the code should run without error
        assertSuccessfulRun(self, dummy_kernel, code,
            ["t", "s", "e", "t"])

        # - the magic command referenced should have run
        self.assertTrue(post_flight.command_1_was_run)
        post_flight.command_1_was_run = False

        self.assertFalse(post_flight.command_2_was_run)
        post_flight.command_2_was_run = False

        self.assertFalse(post_flight.command_3_was_run)
        post_flight.command_3_was_run = False

        # after removing the magic command,
        dummy_kernel.magic_commands.remove_command("post-flight-1")

        # - any code referring to it should fail
        assertUnsuccessfulRun(self, dummy_kernel, code, [None])

        # - the magic command referenced should not have run
        self.assertFalse(post_flight.command_1_was_run)
        post_flight.command_1_was_run = False

        self.assertFalse(post_flight.command_2_was_run)
        post_flight.command_2_was_run = False

        self.assertFalse(post_flight.command_3_was_run)
        post_flight.command_3_was_run = False

        # - any code not referring to it should run
        assertSuccessfulRun(self, dummy_kernel, "test",
            ["t", "e", "s", "t"])

        # with a parameterized magic command,
        code = """
            !post-flight-2 --prefix [
            test
            """

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands.parse_code(code)

        # - this magic command should be mentioned
        self.assertEqual(len(pre_flight_commands), 0)
        self.assertEqual(len(post_flight_commands), 1)
        self.assertEqual(post_flight_commands[0][0], "post-flight-2")

        # - the code should run without error
        assertSuccessfulRun(self, dummy_kernel, code,
            ["[t)", "[e)", "[s)", "[t)"])

        # - the magic command referenced should have run
        self.assertFalse(post_flight.command_1_was_run)
        post_flight.command_1_was_run = False

        self.assertTrue(post_flight.command_2_was_run)
        post_flight.command_2_was_run = False

        self.assertFalse(post_flight.command_3_was_run)
        post_flight.command_3_was_run = False

        # with the exception-raising command,
        code = """
            !post-flight-3
            test
            """

        # - the code should not run
        assertUnsuccessfulRun(self, dummy_kernel, code, [None])

        # - the magic command referenced should have run
        self.assertFalse(post_flight.command_1_was_run)
        post_flight.command_1_was_run = False

        self.assertFalse(post_flight.command_2_was_run)
        post_flight.command_2_was_run = False

        self.assertTrue(post_flight.command_3_was_run)
        post_flight.command_3_was_run = False

        # if we combine several magic commands,
        code = """
            !post-flight-1
            !post-flight-2 --suffix ]
            test
            """

        dummy_kernel.magic_commands.declare_post_flight_command(
            "post-flight-1", post_flight.command_1)

        post_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands.parse_code(code)

        # - all these magic commands should be mentioned
        self.assertEqual(len(pre_flight_commands), 0)
        self.assertEqual(len(post_flight_commands), 2)
        self.assertEqual(post_flight_commands[0][0], "post-flight-1")
        self.assertEqual(post_flight_commands[1][0], "post-flight-2")

        # - the code should run without error
        assertSuccessfulRun(self, dummy_kernel, code,
            ["(t]", "(s]", "(e]", "(t]"])

        # - the magic commands referenced should have run
        self.assertTrue(post_flight.command_1_was_run)
        post_flight.command_1_was_run = False

        self.assertTrue(post_flight.command_2_was_run)
        post_flight.command_2_was_run = False

        self.assertFalse(post_flight.command_3_was_run)
        post_flight.command_3_was_run = False

if (__name__ == "__main__"):
    unittest.main()
