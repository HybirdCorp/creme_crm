################################################################################
#
# Copyright (c) 2009-2025 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

from contextlib import ContextDecorator

from django.db import models
from django.db.transaction import atomic
from django.db.utils import IntegrityError


class MutexLockedException(Exception):  # TODO: inner class ?
    def __init__(self, *args, **kwargs):
        super().__init__('Mutex is already locked')


class MutexNotLockedException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__('The mutex is not locked')


class Mutex(models.Model):
    id = models.CharField(max_length=100, primary_key=True)

    class Meta:
        app_label = 'creme_core'

    def is_locked(self) -> bool:
        return bool(self.id and not self._state.adding)

    def lock(self) -> None:
        if self.is_locked():
            raise MutexLockedException()

        try:
            with atomic():
                self.save()
        except IntegrityError as e:
            raise MutexLockedException('Mutex is already locked') from e

        # return self ?

    def release(self) -> None:
        if not self.is_locked():
            raise MutexNotLockedException()

        self.delete()

    @classmethod
    def get_n_lock(cls, id_: str):
        mutex = cls(id=id_)
        mutex.lock()
        return mutex

    @classmethod
    def graceful_release(cls, id_: str) -> None:
        cls.objects.filter(id=id_).delete()

    def save(self, *args, **kwargs):
        super().save(force_insert=True, *args, **kwargs)


class MutexAutoLock(ContextDecorator):
    lock_name: str
    locked: bool
    mutex_class: type[Mutex]

    def __init__(self, lock_name: str, mutex_class=Mutex):
        self.lock_name = lock_name
        self.locked = False
        self.mutex_class = mutex_class

    def __enter__(self):
        self.mutex_class.get_n_lock(self.lock_name)
        self.locked = True

    def __exit__(self, exc_type, exc_value, traceback):
        if self.locked:
            self.mutex_class.graceful_release(self.lock_name)
