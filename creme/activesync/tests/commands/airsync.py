# -*- coding: utf-8 -*-

try:
    from os.path import join, dirname, abspath

    #from activesync.commands.airsync import AirSync
    from activesync.tests.commands.base import BaseASTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


#TODO: tests!!
class AirSyncASTestCase(BaseASTestCase):
    def setUp(self):
        super(AirSyncASTestCase, self).setUp()
        self.test_files_path = join(dirname(abspath(__file__)), '..', 'data', 'commands', 'airsync')
        self.test_files = []
        self.test_files_paths = [join(self.test_files_path, f) for f in self.test_files]

#    def test_airsync01(self):
#        as_ = AirSync(*self.params)
#        as_.send(headers={'test_files': ";".join(self.test_files_paths) })
