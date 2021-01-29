# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeEntity
from creme.creme_core.models.fields import CTypeForeignKey, DatePeriodField


class AbstractRecurrentGenerator(CremeEntity):
    name = models.CharField(_('Name of the generator'), max_length=100, blank=True)

    first_generation = models.DateTimeField(_('Date of the first generation'))
    last_generation = models.DateTimeField(
        _('Date of the last generation'), null=True, editable=False,
    )
    periodicity = DatePeriodField(_('Periodicity of the generation'))

    ct = CTypeForeignKey(verbose_name=_('Type of the recurrent resource'), editable=False)
    template = models.ForeignKey(
        CremeEntity,
        verbose_name=_('Related model'),
        related_name='template_set', editable=False, on_delete=models.CASCADE,
    )

    is_working = models.BooleanField(_('Active ?'), editable=False, default=True)  # TODO: useful ?

    creation_label = _('Create a generator')
    save_label     = _('Save the generator')

    class Meta:
        abstract = True
        # manager_inheritance_from_future = True
        app_label = 'recurrents'
        verbose_name = _('Recurrent generator')
        verbose_name_plural = _('Recurrent generators')
        ordering = ('name',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__init_refreshing_cache()

    def __init_refreshing_cache(self):
        self._old_first_generation = self.first_generation
        self._old_periodicity = self.periodicity
        # TODO: is_working when it is used

    def __str__(self):
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
        super().save(*args, **kwargs)

        if (
            created
            or self._old_first_generation != self.first_generation
            or self._old_periodicity != self.periodicity
        ):
            recurrents_gendocs_type.refresh_job()
            self.__init_refreshing_cache()


class RecurrentGenerator(AbstractRecurrentGenerator):
    class Meta(AbstractRecurrentGenerator.Meta):
        swappable = 'RECURRENTS_RGENERATOR_MODEL'
