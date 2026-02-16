from io import StringIO

from django.core.management import call_command

from creme.creme_core.management.commands.build_secret_key import (
    Command as BuildSecretKeyCommand,
)

from .. import base


class BuildSecretKeyTestCase(base.CremeTestCase):
    def test_ok(self):
        cmd = BuildSecretKeyCommand()
        cmd.stdout = stdout = StringIO()

        with self.assertNoException():
            call_command(cmd, verbosity=0)

        self.assertEqual(50, len(stdout.getvalue()))  # TODO: improve...
