import pytest
import subprocess
import re
import os


class Runner():
    def __init__(self, command):
        self.command = command
        self.out = None

    def run(self, *args):
        command = [self.command] + list(args)
        self.out = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def stdout(self):
        return self.out.stdout

    def stderr(self):
        return self.out.stderr

    def has_succeeded(self):
        return 0 == self.out.returncode

    def output_contains(self, r):
        reg = re.compile(r)
        return reg.findall(str(self.stdout())) is not None

    def output_exact(self, text):
        return str(self.stdout) == text

    def output_matches_file(self, filename):
        with open(filename) as f:
            return f.read() == str(self.stdout())

    def flush(self):
        self.out = None


@pytest.fixture
def runner():
    return Runner("riseml")


def test_help(runner):
    runner.run("-h")
    runner.output_matches_file("help.txt")


def test_user_login(runner):
    runner.run("user", "login",
               "--api-host", os.environ["RISEML_ENDPOINT"],
               "--sync-host", os.environ["RISEML_SYNC_ENDPOINT"],
               "--api-key", os.environ["RISEML_APIKEY"],
    )
    assert runner.has_succeeded()


def test_system_info(runner):
    runner.run("system", "info")
    assert runner.has_succeeded()
    assert runner.output_contains('Total\s*\d{1,3}.*')


def test_status(runner):
    runner.run("status")
    assert runner.has_succeeded()
    assert runner.output_contains('ID\s+PROJECT\s+STATE\s+AGE\s+TYPE')


def test_system_test(runner):
    runner.run("system", "test")
    assert runner.has_succeeded()
    runner.flush()

    runner.run("status")
    assert runner.output_contains("smoke-test\s*●\s*RUNNING")
