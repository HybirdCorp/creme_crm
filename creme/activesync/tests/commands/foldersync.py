# -*- coding: utf-8 -*-

try:
    from os.path import join, dirname, abspath

    from creme.activesync.commands.foldersync import FolderSync
    from .base import BaseASTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class FolderSyncASTestCase(BaseASTestCase):
    def setUp(self):
        super(FolderSyncASTestCase, self).setUp()
        self.test_files_path = join(dirname(abspath(__file__)), '..', 'data', 'commands', 'foldersync')
        self.test_files = ['response_for_synckey0.xml', 'response_for_nochanges.xml']
        self.test_files_paths = [join(self.test_files_path, f) for f in self.test_files]

    def test_foldersync01(self):
        fs = FolderSync(*self.params)
        fs.send(0, sync_key=0, headers={'test_files': ";".join(self.test_files_paths)})
        added_folders = fs.add

        self.assertEqual('00AxEWaaGE7UKRUUweABOXMA==001===========AQQAAAAzNAsA', fs.synckey)
        self.assertEqual([
                         {'displayname': 'Inbox',
                          'parentid': '0',
                          'serverid': '00000000-0000-0000-0000-000000000001',
                          'type': 2},
                         {'displayname': 'Drafts',
                          'parentid': '0',
                          'serverid': '00000000-0000-0000-0000-000000000004',
                          'type': 3},
                         {'displayname': 'Junk',
                          'parentid': '0',
                          'serverid': '00000000-0000-0000-0000-000000000005',
                          'type': 12},
                         {'displayname': 'Sent',
                          'parentid': '0',
                          'serverid': '00000000-0000-0000-0000-000000000003',
                          'type': 5},
                         {'displayname': 'Trash',
                          'parentid': '0',
                          'serverid': '00000000-0000-0000-0000-000000000002',
                          'type': 4},
                         {'displayname': 'Contacts', 'parentid': '0', 'serverid': '2:0', 'type': 9},
                         {'displayname': 'Calendrier des anniversaires (Read only)',
                          'parentid': '0',
                          'serverid': '1:APjQQOlXt1lBjisYruV/OmmcxhJhYFDmS6MqtzLYT0UX',
                          'type': 13},
                         {'displayname': 'Vacances en France (Read only)',
                          'parentid': '0',
                          'serverid': '1:AYxGR1YlgfROttOgMSSWvosGaLesTUEfRozSstAtx7cU',
                          'type': 13},
                         {'displayname': 'Calendrier de Aqua',
                          'parentid': '0',
                          'serverid': '1:AIsHBEPRMgBFl6P6f+LWfehHq8JUTJczTbnrPlJ+MR+4',
                          'type': 8},
                         {'displayname': 'Calendrier de Aqua',
                          'parentid': '0',
                          'serverid': '3:AIsHBEPRMgBFl6P6f+LWfehHq8JUTJczTbnrPlJ+MR+4',
                          'type': 7},
                         {'displayname': 'Calendrier 2',
                          'parentid': '0',
                          'serverid': '1:AB5a/CLTPSlNpjP6zK3t69AdHZ17AdRuSILDUiFGUNNe',
                          'type': 13},
                         {'displayname': 'Calendrier 2',
                          'parentid': '0',
                          'serverid': '3:AB5a/CLTPSlNpjP6zK3t69AdHZ17AdRuSILDUiFGUNNe',
                          'type': 15}], added_folders)

        previous_sync_key = fs.synckey

        fs = FolderSync(*self.params)
        fs.send(0, sync_key=previous_sync_key, headers={'test_files': ";".join(self.test_files_paths) })
        self.assertEqual('2', fs.synckey)
        self.assertEqual([], fs.add)
