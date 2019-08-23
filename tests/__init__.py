#!/usr/bin/env python3
"""Run tests for this base image.

Each test must be a valid docker-compose.yaml file with a ``odoo`` service.
"""
import logging
import unittest

from itertools import product
from os import environ
from os.path import dirname, join
from subprocess import Popen

logging.basicConfig(level=logging.DEBUG)

DIR = dirname(__file__)
ODOO_PREFIX = ("odoo", "--stop-after-init", "--workers=0")
ODOO_VERSIONS = frozenset(environ.get(
    "DOCKER_TAG", "7.0 8.0 9.0 10.0 11.0 12.0").split())
PG_VERSIONS = frozenset(environ.get(
    "PG_VERSIONS", "11").split())
SCAFFOLDINGS_DIR = join(DIR, "scaffoldings")


def matrix(odoo=ODOO_VERSIONS, pg=PG_VERSIONS,
           odoo_skip=frozenset(), pg_skip=frozenset()):
    """All possible combinations.

    We compute the variable matrix here instead of in ``.travis.yml`` because
    this generates faster builds, given the scripts found in ``hooks``
    directory are already multi-version-build aware.
    """
    return map(
        dict,
        product(
            product(("ODOO_MINOR",), ODOO_VERSIONS & odoo - odoo_skip),
            product(("DB_VERSION",), PG_VERSIONS & pg - pg_skip),
        )
    )


class ScaffoldingCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.compose_run = ("docker-compose", "run", "--rm", "odoo")

    def popen(self, *args, **kwargs):
        """Shortcut to open a subprocess and ensure it works."""
        logging.info("Subtest execution: %s", self._subtest)
        self.assertFalse(Popen(*args, **kwargs).wait())

    def compose_test(self, workdir, sub_env, *commands):
        """Execute commands in a docker-compose environment.

        :param workdir:
            Path where the docker compose commands will be executed. It should
            contain a valid ``docker-compose.yaml`` file.

        :param dict sub_env:
            Specific environment variables that will be appended to current
            ones to execute the ``docker-compose`` tests.

            You can set in this dict a ``COMPOSE_FILE`` key to choose different
            docker-compose files in the same directory.

        :param tuple()... commands:
            List of commands to be tested in the odoo container.
        """
        full_env = dict(environ, **sub_env)
        with self.subTest(PWD=workdir, **sub_env):
            try:
                self.popen(
                    ("docker-compose", "build"),
                    cwd=workdir,
                    env=full_env,
                )
                for command in commands:
                    with self.subTest(command=command):
                        self.popen(
                            self.compose_run + command,
                            cwd=workdir,
                            env=full_env,
                        )
            finally:
                self.popen(
                    ("docker-compose", "down", "-v"),
                    cwd=workdir,
                    env=full_env,
                )

    def test_addons_filtered(self):
        """Test addons filtering with ``ONLY`` keyword in ``addons.yaml``."""
        project_dir = join(SCAFFOLDINGS_DIR, "dotd")
        for sub_env in matrix():
            self.compose_test(
                project_dir,
                dict(sub_env, DBNAME="prod"),
                ("test", "-e", "auto/addons/web"),
                ("test", "-e", "auto/addons/private_addon"),
                ("bash", "-c",
                 'test "$(addons list -p)" == disabled_addon,private_addon'),
                ("bash", "-c", 'test "$(addons list -ip)" == private_addon'),
                ("bash", "-c", 'addons list -c | grep ,crm,'),
                # absent_addon is missing and should fail
                ("bash", "-c", "! addons list -px"),
            )
            self.compose_test(
                project_dir,
                dict(sub_env, DBNAME="limited_private"),
                ("test", "-e", "auto/addons/web"),
                ("test", "!", "-e", "auto/addons/private_addon"),
                ("bash", "-c", 'test -z "$(addons list -p)"'),
                ("bash", "-c",
                 '[ "$(addons list -s. -pwfake1 -wfake2)" == fake1.fake2 ]'),
                ("bash", "-c", "! addons list -wrepeat -Wrepeat"),
                ("bash", "-c", 'addons list -c | grep ,crm,'),
            )
            self.compose_test(
                project_dir,
                dict(sub_env, DBNAME="limited_core"),
                ("test", "!", "-e", "auto/addons/web"),
                ("test", "!", "-e", "auto/addons/private_addon"),
                ("bash", "-c", 'test -z "$(addons list -p)"'),
                ("bash", "-c", 'test "$(addons list -c)" == crm,sale'),
            )
        # Skip Odoo versions that don't support __manifest__.py files
        for sub_env in matrix(odoo_skip={"7.0", "8.0", "9.0"}):
            self.compose_test(
                project_dir,
                dict(sub_env, DBNAME="prod"),
                ("bash", "-c",
                 'test "$(addons list -ped)" == base,web,website'),
                # ``dummy_addon`` and ``private_addon`` exist
                ("test", "-d", "auto/addons/dummy_addon"),
                ("test", "-h", "auto/addons/dummy_addon"),
                ("test", "-f", "auto/addons/dummy_addon/__init__.py"),
                ("test", "-e", "auto/addons/dummy_addon"),
                # Addon from extra repo takes higher priority than core version
                ("realpath", "auto/addons/product"),
                ("bash", "-c", 'test "$(realpath auto/addons/product)" == '
                 '/opt/odoo/custom/src/other-doodba/odoo/src/private/product'),
                ("bash", "-c",
                 'test "$(addons list -e)" == dummy_addon,product'),
            )
            self.compose_test(
                project_dir,
                dict(sub_env, DBNAME="limited_private"),
                ("test", "-e", "auto/addons/dummy_addon"),
                ("bash", "-c",
                 'test "$(addons list -e)" == dummy_addon,product'),
            )
            self.compose_test(
                project_dir,
                dict(sub_env, DBNAME="limited_core"),
                ("test", "-e", "auto/addons/dummy_addon"),
                ("bash", "-c",
                 '[ "$(addons list -s. -pwfake1 -wfake2)" == fake1.fake2 ]'),
                ("bash", "-c",
                 'test "$(addons list -e)" == dummy_addon,product'),
                ("bash", "-c", 'test "$(addons list -c)" == crm,sale'),
                ("bash", "-c", 'test "$(addons list -cWsale)" == crm'),
            )

    def test_qa(self):
        """Test that QA tools are in place and work as expected."""
        folder = join(SCAFFOLDINGS_DIR, "settings")
        commands = (
            ("./custom/scripts/qa-insider-test",),
            ("/qa/node_modules/.bin/eslint", "--version"),
            ("/qa/venv/bin/flake8", "--version"),
            ("/qa/venv/bin/pylint", "--version"),
            ("/qa/venv/bin/python", "--version"),
            ("/qa/venv/bin/python", "-c", "import pylint_odoo"),
            ("test", "-d", "/qa/mqt"),
        )
        for sub_env in matrix():
            self.compose_test(folder, sub_env, *commands)

    def test_settings(self):
        """Test settings are filled OK"""
        folder = join(SCAFFOLDINGS_DIR, "settings")
        commands = (
            # Odoo should install
            ("--stop-after-init",),
            # Odoo settings work
            ("./custom/scripts/test_settings.py",),
        )
        # Odoo 8.0 has no shell, and --load-language doesn't work fine in 9.0
        for sub_env in matrix(odoo={"9.0"}):
            self.compose_test(folder, sub_env, *commands)
        # Extra tests for versions >= 10.0, that support --load-language fine
        commands += (
            # DB was created with the correct language
            ("bash", "-c",
             """test "$(psql -Atqc "SELECT code FROM res_lang
                                    WHERE active = TRUE")" == es_ES"""),
        )
        for sub_env in matrix(odoo_skip={"8.0", "9.0"}):
            self.compose_test(folder, sub_env, *commands)

    def test_smallest(self):
        """Tests for the smallest possible environment."""
        commands = (
            # Must generate a configuration file
            ("test", "-f", "/opt/odoo/auto/odoo.conf"),
            ("test", "-d", "/opt/odoo/custom/src/private"),
            ("test", "-d", "/opt/odoo/custom/ssh"),
            ("test", "-x", "/usr/local/bin/unittest"),
            ("addons", "list", "-cpix"),
            ("pg_activity", "--version"),
            # Must be able to install base addon
            ODOO_PREFIX + ("--init", "base"),
            # Auto updater must work
            ("autoupdate",),
            ("click-odoo-update",),
        )
        smallest_dir = join(SCAFFOLDINGS_DIR, "smallest")
        for sub_env in matrix(odoo_skip={"7.0", "8.0"}):
            self.compose_test(
                smallest_dir, sub_env, *commands,
                ("python", "-c", "import watchdog"),
            )
        for sub_env in matrix(odoo={"7.0", "8.0"}):
            self.compose_test(
                smallest_dir, sub_env,
                # Odoo <= 8.0 does not autocreate the database
                ("createdb",),
                *commands
            )

    def test_dotd(self):
        """Test environment with common ``*.d`` directories."""
        for sub_env in matrix():
            self.compose_test(
                join(SCAFFOLDINGS_DIR, "dotd"), sub_env,
                # ``custom/build.d`` was properly executed
                ("test", "-f", "/home/odoo/created-at-build"),
                # ``custom/entrypoint.d`` was properly executed
                ("test", "-f", "/home/odoo/created-at-entrypoint"),
                # ``custom/conf.d`` was properly concatenated
                ("grep", "test-conf", "auto/odoo.conf"),
                # ``custom/dependencies`` were installed
                ("test", "!", "-e", "/usr/sbin/sshd"),
                ("test", "!", "-e", "/var/lib/apt/lists/lock"),
                ("busybox", "whoami"),
                ("bash", "-c", "echo $NODE_PATH"),
                ("node", "-e", "require('test-npm-install')"),
                ("aloha_world",),
                ("python", "-c", "import Crypto; print(Crypto.__version__)"),
                ("sh", "-c", "rst2html.py --version | grep 'Docutils 0.14'"),
                # ``requirements.txt`` from addon repos were processed
                ("python", "-c", "import cfssl"),
                # Local executable binaries found in $PATH
                ("sh", "-c", "pip install --user -q flake8 && which flake8"),
                # Addon cleanup works correctly
                ("test", "!", "-e", "custom/src/private/dummy_addon"),
                ("test", "!", "-e", "custom/src/dummy_repo/dummy_link"),
                ("test", "-d", "custom/src/private/private_addon"),
                ("test", "-f", "custom/src/private/private_addon/__init__.py"),
                ("test", "-e", "auto/addons/private_addon"),
                # ``odoo`` command works
                ("odoo", "--version"),
                # Implicit ``odoo`` command also works
                ("--version",),
            )

    def test_dependencies(self):
        """Test dependencies installation."""
        dependencies_dir = join(SCAFFOLDINGS_DIR, "dependencies")
        for sub_env in matrix():
            self.compose_test(
                dependencies_dir, sub_env,
                ("test", "!", "-f", "custom/dependencies/apt.txt"),
                ("test", "!", "-f", "custom/dependencies/gem.txt"),
                ("test", "!", "-f", "custom/dependencies/npm.txt"),
                ("test", "!", "-f", "custom/dependencies/pip.txt"),
                # It should have module_auto_update available
                ("test", "-d", "custom/src/server-tools/module_auto_update"),
                # Patched Werkzeug version
                ("bash", "-c", ('test "$(python -c "import werkzeug; '
                                'print(werkzeug.__version__)")" == 0.14.1')),
                # apt_build.txt
                ("test", "-f", "custom/dependencies/apt_build.txt"),
                ("test", "!", "-e", "/usr/sbin/sshd"),
                # apt-without-sequence.txt
                ("test", "-f", "custom/dependencies/apt-without-sequence.txt"),
                ("test", "!", "-e", "/bin/busybox"),
                # 070-apt-bc.txt
                ("test", "-f", "custom/dependencies/070-apt-bc.txt"),
                ("test", "-e", "/usr/bin/bc"),
                # 150-npm-aloha_world-install.txt
                ("test", "-f", ("custom/dependencies/"
                                "150-npm-aloha_world-install.txt")),
                ("node", "-e", "require('test-npm-install')"),
                # 200-pip-without-ext
                ("test", "-f", "custom/dependencies/200-pip-without-ext"),
                ("python", "-c", "import Crypto; print(Crypto.__version__)"),
                ("sh", "-c", "rst2html.py --version | grep 'Docutils 0.14'"),
                # 270-gem.txt
                ("test", "-f", "custom/dependencies/270-gem.txt"),
                ("aloha_world",),
            )

    def test_modified_uids(self):
        """tests if we can build an image with a custom uid and gid of odoo"""
        uids_dir = join(SCAFFOLDINGS_DIR, "uids_1001")
        for sub_env in matrix():
            self.compose_test(
                uids_dir, sub_env,
                # verify that odoo user has the given ids
                ("bash", "-c", 'test "$(id -u)" == "1001"'),
                ("bash", "-c", 'test "$(id -g)" == "1002"'),
                ("bash", "-c", 'test "$(id -u -n)" == "odoo"'),
                # all those directories need to belong to odoo (user or group odoo)
                ("bash", "-c", 'test "$(stat -c \'%U:%G\' /var/lib/odoo)" == "odoo:odoo"'),
                ("bash", "-c", 'test "$(stat -c \'%U:%G\' /opt/odoo/auto/addons)" == "root:odoo"'),
                ("bash", "-c", 'test "$(stat -c \'%U:%G\' /opt/odoo/custom/src)" == "root:odoo"'),
            )

    def test_default_uids(self):
        uids_dir = join(SCAFFOLDINGS_DIR, "uids_default")
        for sub_env in matrix():
            self.compose_test(
                uids_dir, sub_env,
                # verify that odoo user has the given ids
                ("bash", "-c", 'test "$(id -u)" == "1000"'),
                ("bash", "-c", 'test "$(id -g)" == "1000"'),
                ("bash", "-c", 'test "$(id -u -n)" == "odoo"'),
                # all those directories need to belong to odoo (user or group odoo)
                ("bash", "-c", 'test "$(stat -c \'%U:%G\' /var/lib/odoo)" == "odoo:odoo"'),
                ("bash", "-c", 'test "$(stat -c \'%U:%G\' /opt/odoo/auto/addons)" == "root:odoo"'),
                ("bash", "-c", 'test "$(stat -c \'%U:%G\' /opt/odoo/custom/src)" == "root:odoo"'),
            )


if __name__ == "__main__":
    unittest.main()
