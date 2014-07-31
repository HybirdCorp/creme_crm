# -*- coding: utf-8 -*-

try:
    from django.db.transaction import commit_on_success

    from ..base import CremeTransactionTestCase #CremeTestCase
    from creme.creme_core.models.lock import Mutex, MutexLockedException, MutexNotLockedException, mutex_autolock, MutexAutoLock
    from creme.creme_core.utils import safe_unicode_error
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('MutexTestCase',)


#class MutexTestCase(CremeTestCase):
class MutexTestCase(CremeTransactionTestCase):
    def tearDown(self):
        Mutex.graceful_release('dummy_lock')

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

        with commit_on_success():
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

        with commit_on_success():
            self.assertRaises(MutexLockedException, Mutex.get_n_lock, name)

        mutex.release()
        self.assertEqual(0, Mutex.objects.count())

    @mutex_autolock('dummy_lock')
    def locked_func(self, a):
        return a

    @mutex_autolock('dummy_lock')
    def invalid_locked_func(self, a):
        raise Exception('invalid result %s' % a)

    def test_mutex_autolock(self):
        self.assertEqual(self.locked_func(12), 12)
        self.assertEqual(0, Mutex.objects.filter(id='dummy_lock').count())

    def test_mutex_autolock_already_locked(self):
        self.assertEqual(self.locked_func(12), 12)
        self.assertEqual(0, Mutex.objects.filter(id='dummy_lock').count())

        Mutex.get_n_lock('dummy_lock')
        self.assertEqual(1, Mutex.objects.filter(id='dummy_lock').count())

        with self.assertRaises(MutexLockedException):
            self.locked_func(5)

        self.assertEqual(1, Mutex.objects.filter(id='dummy_lock').count())

    def test_mutex_autolock_unlock_on_fail(self):
        with self.assertRaises(Exception) as context:
            self.invalid_locked_func(5)

        self.assertEquals(u'invalid result %s' % 5, safe_unicode_error(context.exception))

        self.assertEqual(0, Mutex.objects.filter(id='dummy_lock').count())

    def test_MutexAutoLock(self):
        self.assertEqual(0, Mutex.objects.filter(id='dummy_lock').count())

        with MutexAutoLock('dummy_lock'):
            self.assertEqual(1, Mutex.objects.filter(id='dummy_lock').count())

        self.assertEqual(0, Mutex.objects.filter(id='dummy_lock').count())

    def test_MutexAutoLock_already_locked(self):
        Mutex.get_n_lock('dummy_lock')
        self.assertEqual(1, Mutex.objects.filter(id='dummy_lock').count())

        with self.assertRaises(MutexLockedException):
            with MutexAutoLock('dummy_lock'):
                self.fail('cannot be here with lock enabled')

        self.assertEqual(1, Mutex.objects.filter(id='dummy_lock').count())

    def test_MutexAutoLock_recursive_lock(self):
        self.assertEqual(0, Mutex.objects.filter(id='dummy_lock').count())

        with self.assertRaises(MutexLockedException):
            with MutexAutoLock('dummy_lock'):
                self.assertEqual(1, Mutex.objects.filter(id='dummy_lock').count())

                with MutexAutoLock('dummy_lock'):
                    self.fail('cannot be here with lock enabled')

                self.assertEqual(1, Mutex.objects.filter(id='dummy_lock').count())

        self.assertEqual(0, Mutex.objects.filter(id='dummy_lock').count())

    def test_MutexAutoLock_unlock_on_fail(self):
        self.assertEqual(0, Mutex.objects.filter(id='dummy_lock').count())

        with self.assertRaises(Exception) as context:
            with MutexAutoLock('dummy_lock'):
                self.assertEqual(1, Mutex.objects.filter(id='dummy_lock').count())
                raise Exception('invalid result !')

        self.assertEquals(u'invalid result !', safe_unicode_error(context.exception))
        self.assertEqual(0, Mutex.objects.filter(id='dummy_lock').count())
