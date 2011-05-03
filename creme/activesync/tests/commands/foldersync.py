# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from os.path import join, dirname, abspath
from activesync.commands.foldersync import FolderSync

from activesync.tests.commands.base import BaseASTestCase

class FolderSyncASTestCase(BaseASTestCase):
    def setUp(self):
        super(FolderSyncASTestCase, self).setUp()
        self.test_files_path = join(dirname(abspath(__file__)), '..', 'data', 'commands', 'foldersync')
        self.test_files = ['response_for_synckey0.xml', 'response_for_nochanges.xml']
        self.test_files_paths = [join(self.test_files_path, f) for f in self.test_files]

    def test_foldersync01(self):
        fs = FolderSync(*self.params)
        fs.send(0, sync_key=0, headers={'test_files': ";".join(self.test_files_paths) })
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