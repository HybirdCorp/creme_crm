# -*- coding: utf-8 -*-

try:
    from os.path import join, dirname, abspath

    from activesync.commands.settings import Settings
    #from activesync.connection import Connection
    from activesync.tests.commands.base import BaseASTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class SettingsASTestCase(BaseASTestCase):
    def setUp(self):
        super(SettingsASTestCase, self).setUp()
        self.test_files_path = join(dirname(abspath(__file__)), '..', 'data', 'commands', 'settings')
        self.test_files = ['response_1.xml']
        self.test_files_paths = [join(self.test_files_path, f) for f in self.test_files]

    def test_settings01(self):
        s = Settings(*self.params)
        s.send(headers={'test_files': ";".join(self.test_files_paths)})
        self.assertEqual('fulbert@creme.com', s.smtp_address)
