from django.db.transaction import atomic

from creme.creme_core.models.lock import (
    Mutex,
    MutexAutoLock,
    MutexLockedException,
    MutexNotLockedException,
)

from ..base import CremeTransactionTestCase


class MutexTestCase(CremeTransactionTestCase):
    def tearDown(self):
        super().tearDown()
        Mutex.graceful_release('dummy_lock')

    @staticmethod
    def _get_ids():
        return [*Mutex.objects.order_by('id').values_list('id', flat=True)]

    def test_mutex_lock(self):
        mutex = Mutex(id='mutex-01')
        mutex.lock()

        self.get_object_or_fail(Mutex, pk=mutex.id)

        mutex.release()
        self.assertFalse(Mutex.objects.all())

    def test_mutex_lock_twice_same_instance(self):
        "Double lock (on same instance) causes an error"
        mutex = Mutex(id='mutex-01')
        mutex.lock()
        self.assertRaises(MutexLockedException, mutex.lock)

        mutex.graceful_release('mutex-01')

    def test_mutex_unlock_not_locked(self):
        "Release an unlocked Mutex causes an error"
        mutex = Mutex(id='mutex-01')
        self.assertRaises(MutexNotLockedException, mutex.release)

        mutex.graceful_release('mutex-01')

    def test_mutex_lock_twice_same_name(self):
        "Double lock causes an error (lock method)"
        name1 = 'mutex-01'
        name2 = 'other_mutex'

        mutex1 = Mutex(name1)
        mutex2 = Mutex(name1)

        mutex1.lock()

        with atomic():
            self.assertRaises(MutexLockedException, mutex2.lock)

        self.assertEqual(1, Mutex.objects.count())

        with self.assertNoException():
            mutex3 = Mutex(name2)
            mutex3.lock()

        self.assertEqual([name1, name2], self._get_ids())

        mutex1.release()
        self.assertEqual([name2], self._get_ids())

    def test_mutex_lock_twice_static_method(self):
        "Double lock causes an error (get_n_lock static method)"
        name = 'mutex-stuff'
        mutex = Mutex.get_n_lock(name)
        self.assertEqual(1, Mutex.objects.count())

        with atomic():
            self.assertRaises(MutexLockedException, Mutex.get_n_lock, name)

        mutex.release()
        self.assertEqual(0, Mutex.objects.count())

    @MutexAutoLock('dummy_lock')
    def locked_func(self, a):
        return a

    @MutexAutoLock('dummy_lock')
    def invalid_locked_func(self, a):
        raise Exception(f'invalid result {a}')

    def test_MutexAutoLock_decorator(self):
        self.assertEqual(self.locked_func(12), 12)
        self.assertEqual(0, Mutex.objects.filter(id='dummy_lock').count())

    def test_MutexAutoLock_decorator_already_locked(self):
        self.assertEqual(self.locked_func(12), 12)
        self.assertEqual(0, Mutex.objects.filter(id='dummy_lock').count())

        Mutex.get_n_lock('dummy_lock')
        self.assertEqual(1, Mutex.objects.filter(id='dummy_lock').count())

        with self.assertRaises(MutexLockedException):
            self.locked_func(5)

        self.assertEqual(1, Mutex.objects.filter(id='dummy_lock').count())

    def test_MutexAutoLock_decorator_unlock_on_fail(self):
        with self.assertRaises(Exception) as context:
            self.invalid_locked_func(5)

        self.assertEqual('invalid result 5', str(context.exception))
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

        self.assertEqual('invalid result !', str(context.exception))
        self.assertEqual(0, Mutex.objects.filter(id='dummy_lock').count())
