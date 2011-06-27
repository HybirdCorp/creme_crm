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

from django.db.models import Model, CharField, IntegerField

class MutexLockedException(Exception):
    pass

class MutexNotLockedException(Exception):
    pass

class Mutex(Model):
    id  = CharField(max_length=100, primary_key=True)

    class Meta:
        app_label = 'creme_core'

    def is_locked(self):
        return bool(self.id and not self._state.adding)

    def lock(self):
        if self.is_locked():
            raise MutexLockedException(u"Mutex is already locked")
        self.save()
        return self

    def release(self):
        if not self.is_locked():
            raise MutexNotLockedException(u"The mutex is not locked")
        self.delete()

    @staticmethod
    def get_n_lock(id_):
        if Mutex.objects.filter(id=id_).exists():
            raise MutexLockedException(u"Mutex is already locked")
        return Mutex(id=id_).lock()

    @staticmethod
    def graceful_release(id_):
        Mutex.objects.filter(id=id_).delete()

def mutexify(func, lock_name):
    def _aux(*args, **kwargs):
        try:
            lock = Mutex.get_n_lock(lock_name)

        except MutexLockedException, e:
            print 'A process is already running'

        else:
            func(*args, **kwargs)
        finally:
            Mutex.graceful_release(lock_name)

