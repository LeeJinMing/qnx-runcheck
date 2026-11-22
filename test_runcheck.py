import contextlib
import io
import subprocess
import unittest
from unittest.mock import patch

import runcheck


class RuncheckTest(unittest.TestCase):
    def invoke(self, responses):
        argv = ["runcheck.py", "--target", "developer@127.0.0.1", "--port", "2222"]
        replies = iter(responses)
        def simulate(command, **options):
            result = next(replies)
            if command[0] == "qcc" and result.returncode == 0:
                runcheck.Path(command[-1]).write_bytes(b"test executable")
            if "cat > " in command[-1]:
                self.assertEqual(options["stdin"].read(), b"test executable")
            return result
        with patch("sys.argv", argv), patch("runcheck.subprocess.run", side_effect=simulate) as invoke, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                status = runcheck.main()
            except SystemExit as error:
                status = error.code
            return status, [call.args[0] for call in invoke.call_args_list]

    @staticmethod
    def response(status=0, stdout="", stderr=""):
        return subprocess.CompletedProcess([], status, stdout, stderr)

    def test_dispatches_compile_identity_copy_and_run(self):
        status, commands = self.invoke([
            self.response(), self.response(stdout="QNX\n8.0.0\nx86_64\n"),
            self.response(stdout="/tmp/qnx-runcheck.AbC12345\n"), self.response(),
            self.response(stdout="Target: QNX 8.0.0 x86_64\n"), self.response(),
        ])
        self.assertEqual(status, 0)
        self.assertEqual([cmd[0] for cmd in commands], ["qcc", "ssh", "ssh", "ssh", "ssh", "ssh"])
        self.assertIn("-Vgcc_ntox86_64", commands[0])
        self.assertIn("StrictHostKeyChecking=yes", commands[1])
        self.assertIn("-T", commands[3])
        self.assertEqual(commands[3][-1], "umask 077; cat > /tmp/qnx-runcheck.AbC12345/probe")
        self.assertIn("chmod 700 /tmp/qnx-runcheck.AbC12345/probe", commands[4][-1])

    def test_compiler_error_never_contacts_target(self):
        status, commands = self.invoke([self.response(1, stderr="invalid source")])
        self.assertEqual(status, 10)
        self.assertEqual(len(commands), 1)

    def test_stopped_target_never_gets_upload(self):
        status, commands = self.invoke([self.response(), self.response(255, stderr="Connection refused")])
        self.assertEqual(status, 20)
        self.assertEqual(len(commands), 2)

    def test_wrong_operating_system_never_gets_upload(self):
        status, commands = self.invoke([self.response(), self.response(stdout="Linux\n8.0\nx86_64\n")])
        self.assertEqual(status, 20)
        self.assertEqual(len(commands), 2)

    def test_failed_upload_cleans_up_without_running_probe(self):
        status, commands = self.invoke([
            self.response(), self.response(stdout="QNX\n8.0.0\nx86_64\n"),
            self.response(stdout="/tmp/qnx-runcheck.AbC12345\n"),
            self.response(1, stderr="Permission denied"), self.response(),
        ])
        self.assertEqual(status, 30)
        self.assertEqual(len(commands), 5)
        self.assertIn("rmdir /tmp/qnx-runcheck.AbC12345", commands[-1][-1])


if __name__ == "__main__":
    unittest.main()
