################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from __future__ import annotations

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core import models as core_models

_ALL_KEY = 'all'


class MarketSegmentManager(models.Manager):
    def get_by_portable_key(self, key) -> MarketSegment:
        return (
            self.get(property_type=None)
            if key == _ALL_KEY else
            self.get(property_type__uuid=key)
        )


class MarketSegment(core_models.CremeModel):
    name = models.CharField(_('Name'), max_length=100)  # TODO: unique ?
    # TODO: OneToOneField?
    property_type = models.ForeignKey(
        core_models.CremePropertyType, null=True, editable=False, on_delete=models.CASCADE,
    ).set_tags(viewable=False)

    objects = MarketSegmentManager()

    creation_label = _('Create a market segment')
    save_label     = _('Save the market segment')

    class Meta:
        app_label = 'commercial'
        verbose_name = _('Market segment')
        verbose_name_plural = _('Market segments')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_edit_absolute_url(self):
        return reverse('commercial__edit_segment', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('commercial__list_segments')

    @staticmethod
    def generate_property_text(segment_name):
        return gettext('is in the segment «{}»').format(segment_name)

    def portable_key(self) -> str:
        ptype = self.property_type

        return _ALL_KEY if ptype is None else str(self.property_type.uuid)

    def save(self, *args, **kwargs):
        if self.property_type is None:
            qs = MarketSegment.objects.filter(property_type=None)

            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValueError(
                    'Only one MarketSegment with property_type=NULL is allowed.'
                )

        super().save(*args, **kwargs)
