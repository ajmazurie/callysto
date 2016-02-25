
import operator
import unittest

from commons import *

class MagicCommandsTests (unittest.TestCase):

    def test_setting_magic_commands_prefix (self):
        dummy_kernel = DummyKernel()

        dummy_kernel.magic_commands.prefix = "!"
        self.assertEqual(dummy_kernel.magic_commands.prefix, "!")

    def test_adding_and_removing_magic_command (self):
        dummy_kernel = DummyKernel()

        # we can add pre- and post-flight magic commands
        dummy_kernel.declare_pre_flight_command(
            "pre-flight", lambda x: None)
        self.assertTrue(
            dummy_kernel.magic_commands.has_command("pre-flight"))

        dummy_kernel.declare_post_flight_command(
            "post-flight", lambda x: None)
        self.assertTrue(
            dummy_kernel.magic_commands.has_command("post-flight"))

        # we shouldn't be able to add a magic command twice by default,
        with self.assertRaises(Exception):
            dummy_kernel.declare_pre_flight_command(
                "pre-flight", lambda x: None)

        with self.assertRaises(Exception):
            dummy_kernel.declare_post_flight_command(
                "post-flight", lambda x: None)

        # except if we use the 'overwrite' parameter
        dummy_kernel.declare_pre_flight_command(
            "pre-flight", lambda x: None, overwrite = True)

        dummy_kernel.declare_post_flight_command(
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

    def test_magic_command_options_parsing (self):
        dummy_kernel = DummyKernel()

        def pre_flight_command_1 (code, **kwargs):
            """ Usage: pre-flight
            """
            global pre_flight_kwargs
            pre_flight_kwargs = kwargs
            return code.strip()

        def pre_flight_command_2 (code, **kwargs):
            """ Usage: pre-flight <foo> [--bar STRING] [--baz STRING]

                Options:
                    <foo> STRING  Foo
                    --bar STRING  Bar [default: )]
                    --baz STRING  Baz
            """
            global pre_flight_kwargs
            pre_flight_kwargs = kwargs
            return code.strip()

        def post_flight_command_1 (code, frames, **kwargs):
            """ Usage: post-flight
            """
            global post_flight_kwargs
            post_flight_kwargs = kwargs
            for frame in frames:
                yield frame

        def post_flight_command_2 (code, frames, **kwargs):
            """ Usage: post-flight <foo> [--bar STRING] [--baz STRING]

                Options:
                    <foo> STRING  Foo
                    --bar STRING  Bar [default: )]
                    --baz STRING  Baz
            """
            global post_flight_kwargs
            post_flight_kwargs = kwargs
            for frame in frames:
                yield frame

        dummy_kernel.declare_pre_flight_command(
            "pre-flight-1", pre_flight_command_1)

        dummy_kernel.declare_pre_flight_command(
            "pre-flight-2", pre_flight_command_2)

        dummy_kernel.declare_post_flight_command(
            "post-flight-1", post_flight_command_1)

        dummy_kernel.declare_post_flight_command(
            "post-flight-2", post_flight_command_2)

        assertSuccessfulRun(self, dummy_kernel,
            """%pre-flight-1
               dummy""", ["dummy"])

        self.assertEqual(len(pre_flight_kwargs), 0)

        assertSuccessfulRun(self, dummy_kernel,
            """%pre-flight-2 [
               dummy""", ["dummy"])

        self.assertTrue("<foo>" in pre_flight_kwargs)
        self.assertTrue("--bar" in pre_flight_kwargs)
        self.assertFalse("--baz" in pre_flight_kwargs)
        self.assertEqual(pre_flight_kwargs["<foo>"], "[")
        self.assertEqual(pre_flight_kwargs["--bar"], ")")

        assertSuccessfulRun(self, dummy_kernel,
            """%pre-flight-2 ( --bar ]
               dummy""", ["dummy"])

        self.assertTrue("<foo>" in pre_flight_kwargs)
        self.assertTrue("--bar" in pre_flight_kwargs)
        self.assertFalse("--baz" in pre_flight_kwargs)
        self.assertEqual(pre_flight_kwargs["<foo>"], "(")
        self.assertEqual(pre_flight_kwargs["--bar"], "]")

        assertSuccessfulRun(self, dummy_kernel,
            """%pre-flight-2 [ --baz ]
               dummy""", ["dummy"])

        self.assertTrue("<foo>" in pre_flight_kwargs)
        self.assertTrue("--bar" in pre_flight_kwargs)
        self.assertTrue("--baz" in pre_flight_kwargs)
        self.assertEqual(pre_flight_kwargs["<foo>"], "[")
        self.assertEqual(pre_flight_kwargs["--bar"], ")")
        self.assertEqual(pre_flight_kwargs["--baz"], "]")

        assertSuccessfulRun(self, dummy_kernel,
            """%post-flight-1
               dummy""", ["dummy"])

        self.assertEqual(len(post_flight_kwargs), 0)

        assertSuccessfulRun(self, dummy_kernel,
            """%post-flight-2 [
               dummy""", ["dummy"])

        self.assertTrue("<foo>" in post_flight_kwargs)
        self.assertTrue("--bar" in post_flight_kwargs)
        self.assertFalse("--baz" in post_flight_kwargs)
        self.assertEqual(post_flight_kwargs["<foo>"], "[")
        self.assertEqual(post_flight_kwargs["--bar"], ")")

        assertSuccessfulRun(self, dummy_kernel,
            """%post-flight-2 ( --bar ]
               dummy""", ["dummy"])

        self.assertTrue("<foo>" in post_flight_kwargs)
        self.assertTrue("--bar" in post_flight_kwargs)
        self.assertFalse("--baz" in post_flight_kwargs)
        self.assertEqual(post_flight_kwargs["<foo>"], "(")
        self.assertEqual(post_flight_kwargs["--bar"], "]")

        assertSuccessfulRun(self, dummy_kernel,
            """%post-flight-2 [ --baz ]
               dummy""", ["dummy"])

        self.assertTrue("<foo>" in post_flight_kwargs)
        self.assertTrue("--bar" in post_flight_kwargs)
        self.assertTrue("--baz" in post_flight_kwargs)
        self.assertEqual(post_flight_kwargs["<foo>"], "[")
        self.assertEqual(post_flight_kwargs["--bar"], ")")
        self.assertEqual(post_flight_kwargs["--baz"], "]")

    def test_pre_flight_commands (self):
        dummy_kernel = DummyKernel()
        dummy_kernel.magic_commands.prefix = '!' # non-default prefix

        class PreFlightCommands:
            def reset (self):
                self.command_1_was_run = False
                self.command_2_was_run = False
                self.command_3_was_run = False

            # command without parameter
            def command_1 (self, code):
                self.command_1_was_run = True
                return code.strip().upper()

            # command with parameter
            def command_2 (self, code, **kwargs):
                """ Usage: command_2 <prefix> [--suffix STRING]

                    Options:
                        <prefix> STRING  Prefix
                        --suffix STRING  Suffix [default: )]
                """
                self.command_2_was_run = True
                prefix = kwargs["<prefix>"]
                suffix = kwargs["--suffix"]

                return prefix + code + suffix

            # command throwing an exception
            def command_3 (self, code):
                self.command_3_was_run = True
                raise Exception("dummy_error")

        pre_flight = PreFlightCommands()

        dummy_kernel.declare_pre_flight_command(
            "pre-flight-1", pre_flight.command_1)

        dummy_kernel.declare_pre_flight_command(
            "pre-flight-2", pre_flight.command_2)

        dummy_kernel.declare_pre_flight_command(
            "pre-flight-3", pre_flight.command_3)

        # without magic commands being mentioned,
        code = "test"

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands._parse_code(code)

        # - none of the magic commands should appear after parsing
        self.assertEqual(len(pre_flight_commands), 0)
        self.assertEqual(len(post_flight_commands), 0)

        # - the code should run without error
        pre_flight.reset()
        assertSuccessfulRun(self, dummy_kernel, code, [code])

        # - and none of the magic commands should have run
        self.assertFalse(pre_flight.command_1_was_run)
        self.assertFalse(pre_flight.command_2_was_run)
        self.assertFalse(pre_flight.command_3_was_run)

        # with a magic command being mentioned however,
        code = """
            !pre-flight-1
            test
            """

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands._parse_code(code)

        # - this magic command should be parsed from the user code
        self.assertEqual(len(pre_flight_commands), 1)
        self.assertEqual(len(post_flight_commands), 0)
        self.assertEqual(pre_flight_commands[0][0], "pre-flight-1")

        # - the code should run without error
        pre_flight.reset()
        assertSuccessfulRun(self, dummy_kernel, code, ["TEST"])

        # - the magic command referenced should have run
        self.assertTrue(pre_flight.command_1_was_run)
        self.assertFalse(pre_flight.command_2_was_run)
        self.assertFalse(pre_flight.command_3_was_run)

        # after removing the magic command,
        dummy_kernel.magic_commands.remove_command("pre-flight-1")

        # - any code referring to it should fail
        pre_flight.reset()
        assertUnsuccessfulRun(self, dummy_kernel, code, exception_validator = \
            lambda x: "Unknown magic command" in x["evalue"])

        # - the magic command referenced should not have run
        self.assertFalse(pre_flight.command_1_was_run)
        self.assertFalse(pre_flight.command_2_was_run)
        self.assertFalse(pre_flight.command_3_was_run)

        # - any code not referring to it should run
        assertSuccessfulRun(self, dummy_kernel, "test", ["test"])

        # with a parameterized magic command,
        code = """
            !pre-flight-2 ( --suffix ]
            test
            """

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands._parse_code(code)

        # - this magic command should be mentioned
        self.assertEqual(len(pre_flight_commands), 1)
        self.assertEqual(len(post_flight_commands), 0)
        self.assertEqual(pre_flight_commands[0][0], "pre-flight-2")

        # - the code should run without error
        pre_flight.reset()
        assertSuccessfulRun(self, dummy_kernel, code, ["(\ntest]"])

        # - the magic command referenced should have run
        self.assertFalse(pre_flight.command_1_was_run)
        self.assertTrue(pre_flight.command_2_was_run)
        self.assertFalse(pre_flight.command_3_was_run)

        # but if we do not provide the right arguments,
        code = """
            !pre-flight-2 --suffix ]
            test
            """

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands._parse_code(code)

        # - this magic command should be mentioned
        self.assertEqual(len(pre_flight_commands), 1)
        self.assertEqual(len(post_flight_commands), 0)
        self.assertEqual(pre_flight_commands[0][0], "pre-flight-2")

        # - the code should run with error
        pre_flight.reset()
        assertUnsuccessfulRun(self, dummy_kernel, code, exception_validator = \
            lambda x: "Invalid syntax" in x["evalue"])

        # - the magic command referenced should not have run
        self.assertFalse(pre_flight.command_1_was_run)
        self.assertFalse(pre_flight.command_2_was_run)
        self.assertFalse(pre_flight.command_3_was_run)

        # with the exception-raising command,
        code = """
            !pre-flight-3
            test
            """

        # - the code should not run
        pre_flight.reset()
        assertUnsuccessfulRun(self, dummy_kernel, code, exception_validator = \
            lambda x: x["evalue"].endswith("dummy_error"))

        # - the magic command referenced should have run
        self.assertFalse(pre_flight.command_1_was_run)
        self.assertFalse(pre_flight.command_2_was_run)
        self.assertTrue(pre_flight.command_3_was_run)

        # if we combine several magic commands,
        code = """
            !pre-flight-1
            !pre-flight-2 ( --suffix ]
            test
            """

        dummy_kernel.declare_pre_flight_command(
            "pre-flight-1", pre_flight.command_1)

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands._parse_code(code)

        # - all these magic commands should be mentioned
        self.assertEqual(len(pre_flight_commands), 2)
        self.assertEqual(len(post_flight_commands), 0)
        self.assertEqual(pre_flight_commands[0][0], "pre-flight-1")
        self.assertEqual(pre_flight_commands[1][0], "pre-flight-2")

        # - the code should run without error
        pre_flight.reset()
        assertSuccessfulRun(self, dummy_kernel, code, ["(TEST]"])

        # - the magic commands referenced should have run
        self.assertTrue(pre_flight.command_1_was_run)
        self.assertTrue(pre_flight.command_2_was_run)
        self.assertFalse(pre_flight.command_3_was_run)

    def test_post_flight_commands (self):
        dummy_kernel = DummyKernel()
        dummy_kernel.magic_commands.prefix = '!' # non-default prefix

        # dummy executor, which split a string into characters
        def do_execute_ (self, code):
            for character in code.strip():
                yield character

        dummy_kernel.update_executor(do_execute_)

        class PostFlightCommands:
            def reset (self):
                self.command_1_was_run = False
                self.command_2_was_run = False
                self.command_3_was_run = False

            # command without parameters
            def command_1 (self, code, results):
                self.command_1_was_run = True
                for frame in reversed(list(results)):
                    yield frame

            # command with parameters
            def command_2 (self, code, results, **kwargs):
                """ Usage: command_2 <prefix> [--suffix STRING]

                    Options:
                        <prefix> STRING  Prefix
                        --suffix STRING  Suffix [default: )]
                """
                self.command_2_was_run = True
                prefix = kwargs["<prefix>"]
                suffix = kwargs["--suffix"]

                for (mimetype, result, metadata) in results:
                    yield (mimetype, prefix + result + suffix, metadata)

            # command throwing an exception
            def command_3 (self, code, results):
                self.command_3_was_run = True
                raise Exception("dummy_error")
                yield

        post_flight = PostFlightCommands()

        dummy_kernel.declare_post_flight_command(
            "post-flight-1", post_flight.command_1)

        dummy_kernel.declare_post_flight_command(
            "post-flight-2", post_flight.command_2)

        dummy_kernel.declare_post_flight_command(
            "post-flight-3", post_flight.command_3)

        # without magic command being mentioned,0
        code = "test"

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands._parse_code(code)

        # - none of the magic commands should appear after parsing
        self.assertEqual(len(pre_flight_commands), 0)
        self.assertEqual(len(post_flight_commands), 0)

        # - the code should run without error
        post_flight.reset()
        assertSuccessfulRun(self, dummy_kernel, code, ["t", "e", "s", "t"])

        # - and none of the magic commands should have run
        self.assertFalse(post_flight.command_1_was_run)
        self.assertFalse(post_flight.command_2_was_run)
        self.assertFalse(post_flight.command_3_was_run)

        # with a magic command being mentioned however,
        code = """
            !post-flight-1
            test
            """

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands._parse_code(code)

        # - this magic command should be parsed from the user code
        self.assertEqual(len(pre_flight_commands), 0)
        self.assertEqual(len(post_flight_commands), 1)
        self.assertEqual(post_flight_commands[0][0], "post-flight-1")

        # - the code should run without error
        post_flight.reset()
        assertSuccessfulRun(self, dummy_kernel, code, ["t", "s", "e", "t"])

        # - the magic command referenced should have run
        self.assertTrue(post_flight.command_1_was_run)
        self.assertFalse(post_flight.command_2_was_run)
        self.assertFalse(post_flight.command_3_was_run)

        # after removing the magic command,
        dummy_kernel.magic_commands.remove_command("post-flight-1")

        # - any code referring to it should fail
        post_flight.reset()
        assertUnsuccessfulRun(self, dummy_kernel, code, exception_validator = \
            lambda x: "Unknown magic command" in x["evalue"])

        # - the magic command referenced should not have run
        self.assertFalse(post_flight.command_1_was_run)
        self.assertFalse(post_flight.command_2_was_run)
        self.assertFalse(post_flight.command_3_was_run)

        # - any code not referring to it should run
        post_flight.reset()
        assertSuccessfulRun(self, dummy_kernel, "test", ["t", "e", "s", "t"])

        # with a parameterized magic command,
        code = """
            !post-flight-2 ( --suffix ]
            test
            """

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands._parse_code(code)

        # - this magic command should be mentioned
        self.assertEqual(len(pre_flight_commands), 0)
        self.assertEqual(len(post_flight_commands), 1)
        self.assertEqual(post_flight_commands[0][0], "post-flight-2")

        # - the code should run without error
        post_flight.reset()
        assertSuccessfulRun(self, dummy_kernel, code,
            ["(t]", "(e]", "(s]", "(t]"])

        # - the magic command referenced should have run
        self.assertFalse(post_flight.command_1_was_run)
        self.assertTrue(post_flight.command_2_was_run)
        self.assertFalse(post_flight.command_3_was_run)

        # but if we do not provide the right arguments,
        code = """
            !post-flight-2 --suffix ]
            test
            """

        pre_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands._parse_code(code)

        # - this magic command should be mentioned
        self.assertEqual(len(pre_flight_commands), 0)
        self.assertEqual(len(post_flight_commands), 1)
        self.assertEqual(post_flight_commands[0][0], "post-flight-2")

        # - the code should run with error
        post_flight.reset()
        assertUnsuccessfulRun(self, dummy_kernel, code, exception_validator = \
            lambda x: "Invalid syntax" in x["evalue"])

        # - the magic command referenced should not have run
        self.assertFalse(post_flight.command_1_was_run)
        self.assertFalse(post_flight.command_2_was_run)
        self.assertFalse(post_flight.command_3_was_run)

        # with the exception-raising command,
        code = """
            !post-flight-3
            test
            """

        # - the code should not run
        post_flight.reset()
        assertUnsuccessfulRun(self, dummy_kernel, code, exception_validator = \
            lambda x: x["evalue"].endswith("dummy_error"))

        # - the magic command referenced should have run
        self.assertFalse(post_flight.command_1_was_run)
        self.assertFalse(post_flight.command_2_was_run)
        self.assertTrue(post_flight.command_3_was_run)

        # if we combine several magic commands,
        code = """
            !post-flight-1
            !post-flight-2 ( --suffix ]
            test
            """

        dummy_kernel.declare_post_flight_command(
            "post-flight-1", post_flight.command_1)

        post_flight_commands, post_flight_commands, code_ = \
            dummy_kernel.magic_commands._parse_code(code)

        # - all these magic commands should be mentioned
        self.assertEqual(len(pre_flight_commands), 0)
        self.assertEqual(len(post_flight_commands), 2)
        self.assertEqual(post_flight_commands[0][0], "post-flight-1")
        self.assertEqual(post_flight_commands[1][0], "post-flight-2")

        # - the code should run without error
        post_flight.reset()
        assertSuccessfulRun(self, dummy_kernel, code,
            ["(t]", "(s]", "(e]", "(t]"])

        # - the magic commands referenced should have run
        self.assertTrue(post_flight.command_1_was_run)
        self.assertTrue(post_flight.command_2_was_run)
        self.assertFalse(post_flight.command_3_was_run)

if (__name__ == "__main__"):
    unittest.main()
