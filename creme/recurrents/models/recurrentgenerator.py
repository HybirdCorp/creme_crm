# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.core.urlresolvers import reverse
from django.db.models import (CharField, TextField, ForeignKey, DateTimeField,
        BooleanField, CASCADE)
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeEntity
from creme.creme_core.models.fields import CTypeForeignKey, DatePeriodField


class AbstractRecurrentGenerator(CremeEntity):
    name             = CharField(_(u'Name of the generator'), max_length=100, blank=True)
    description      = TextField(_(u'Description'), blank=True)
    first_generation = DateTimeField(_(u'Date of the first generation'))
    last_generation  = DateTimeField(_(u'Date of the last generation'), null=True, editable=False)
    periodicity      = DatePeriodField(_(u'Periodicity of the generation'))
    ct               = CTypeForeignKey(verbose_name=_(u'Type of the recurrent resource'), editable=False)
    template         = ForeignKey(CremeEntity, verbose_name=_(u'Related model'),
                                  related_name='template_set', editable=False,
                                  on_delete=CASCADE,
                                 )
    is_working       = BooleanField(_(u'Active ?'), editable=False, default=True)  # TODO: useful ?

    creation_label = _(u'Create a generator')
    save_label     = _(u'Save the generator')

    class Meta:
        abstract = True
        app_label = 'recurrents'
        verbose_name = _(u'Recurrent generator')
        verbose_name_plural = _(u'Recurrent generators')
        ordering = ('name',)

    def __init__(self, *args, **kwargs):
        super(AbstractRecurrentGenerator, self).__init__(*args, **kwargs)
        self.__init_refreshing_cache()

    def __init_refreshing_cache(self):
        self._old_first_generation = self.first_generation
        self._old_periodicity = self.periodicity
        # TODO: is_working when it is used

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('recurrents__view_generator', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('recurrents__create_generator')

    def get_edit_absolute_url(self):
        return reverse('recurrents__edit_generator', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('recurrents__list_generators')

    def save(self, *args, **kwargs):
        from ..creme_jobs import recurrents_gendocs_type
        created = bool(not self.pk)
        super(AbstractRecurrentGenerator, self).save(*args, **kwargs)

        if created or self._old_first_generation != self.first_generation or \
           self._old_periodicity != self.periodicity:
            recurrents_gendocs_type.refresh_job()
            self.__init_refreshing_cache()


class RecurrentGenerator(AbstractRecurrentGenerator):
    class Meta(AbstractRecurrentGenerator.Meta):
        swappable = 'RECURRENTS_RGENERATOR_MODEL'
