 # -*- coding: utf-8 -*-

try:
    from creme_core.models.lock import Mutex, MutexLockedException, MutexNotLockedException
    from creme_core.tests.views.base import ViewsTestCase
except Exception as e:
    print 'Error:', e

__all__ = ('MutexTestCase',)


class MutexTestCase(ViewsTestCase):
    def test_mutex01(self):
        mutex = Mutex(id='mutex-01')
        mutex.lock()

        self.assertEqual(1, Mutex.objects.count())

        try:
            mutex = Mutex.objects.get(pk=mutex.id)
        except Mutex.DoesNotExist, e:
            self.fail(e)

        mutex.release()
        self.assertEqual(0, Mutex.objects.count())

    def test_mutex02(self): #Double lock
        mutex = Mutex(id='mutex-01')
        mutex.lock()
        self.assertRaises(MutexLockedException, mutex.lock)

    def test_mutex03(self): #Release on unlocked Mutex
        mutex = Mutex(id='mutex-01')
        self.assertRaises(MutexNotLockedException, mutex.release)

    def test_mutex04(self):
        mutex = Mutex.get_n_lock('mutex-01')
        self.assertEqual(1, Mutex.objects.count())
        self.assertRaises(MutexLockedException, Mutex.get_n_lock, 'mutex-01')

        mutex.release()
        self.assertEqual(0, Mutex.objects.count())
