# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.db.models import Model, CharField
from django.db.utils import IntegrityError


class MutexLockedException(Exception): #TODO: inner class
    def __init__(self, *args, **kwargs):
        super(MutexLockedException, self).__init__('Mutex is already locked')


class MutexNotLockedException(Exception):
    def __init__(self, *args, **kwargs):
        super(MutexNotLockedException, self).__init__('The mutex is not locked')


class Mutex(Model):
    id = CharField(max_length=100, primary_key=True)

    class Meta:
        app_label = 'creme_core'

    def is_locked(self):
        return bool(self.id and not self._state.adding)

    def lock(self):
        if self.is_locked():
            raise MutexLockedException()

        try:
            self.save()
        except IntegrityError:
            raise MutexLockedException('Mutex is already locked')

        #return self

    def release(self):
        if not self.is_locked():
            raise MutexNotLockedException()

        self.delete()

    @staticmethod
    def get_n_lock(id_):
        mutex = Mutex(id=id_)
        mutex.lock()
        return mutex

    @staticmethod
    def graceful_release(id_):
        Mutex.objects.filter(id=id_).delete()

    def save(self, *args, **kwargs):
        super(Mutex, self).save(force_insert=True, *args, **kwargs)


def mutexify(func, lock_name):
    def _aux(*args, **kwargs):
        try:
            lock = Mutex.get_n_lock(lock_name)
        except MutexLockedException:
            print 'A process is already running'
        else:
            func(*args, **kwargs)
        finally:
            Mutex.graceful_release(lock_name)
