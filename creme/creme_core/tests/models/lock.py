 # -*- coding: utf-8 -*-

try:
    from creme.creme_core.models.lock import Mutex, MutexLockedException, MutexNotLockedException
    from ..base import CremeTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('MutexTestCase',)


class MutexTestCase(CremeTestCase):
    def _get_ids(self):
        return list(Mutex.objects.order_by('id').values_list('id', flat=True))

    def test_mutex01(self):
        mutex = Mutex(id='mutex-01')
        mutex.lock()

        self.get_object_or_fail(Mutex, pk=mutex.id)

        mutex.release()
        self.assertEqual(0, Mutex.objects.count())

    def test_mutex02(self):
        "Double lock (on same instance) causes an error"
        mutex = Mutex(id='mutex-01')
        mutex.lock()
        self.assertRaises(MutexLockedException, mutex.lock)

    def test_mutex03(self):
        "Release an unlocked Mutex causes an error"
        mutex = Mutex(id='mutex-01')
        self.assertRaises(MutexNotLockedException, mutex.release)

    def test_mutex04(self):
        "Double lock causes an error (lock method)"
        name1 = 'mutex-01'
        name2 = 'other_mutex'

        mutex1 = Mutex(name1)
        mutex2 = Mutex(name1)

        mutex1.lock()
        self.assertRaises(MutexLockedException, mutex2.lock)
        self.assertEqual(1, Mutex.objects.count())

        with self.assertNoException():
            mutex3 = Mutex(name2)
            mutex3.lock()

        self.assertEqual([name1, name2], self._get_ids())

        mutex1.release()
        self.assertEqual([name2], self._get_ids())

    def test_mutex05(self):
        "Double lock causes an error (get_n_lock static method)"
        name = 'mutex-stuff'
        mutex = Mutex.get_n_lock(name)
        self.assertEqual(1, Mutex.objects.count())
        self.assertRaises(MutexLockedException, Mutex.get_n_lock, name)

        mutex.release()
        self.assertEqual(0, Mutex.objects.count())
