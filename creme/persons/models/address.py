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

from collections.abc import Iterator
from typing import Any

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

import creme.creme_core.models.fields as core_fields
from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.models import CremeEntity, CremeModel, FieldsConfig


class ZipCodeField(core_fields.SemanticCharField):
    pass


class CityField(core_fields.SemanticCharField):
    pass


class DepartmentField(core_fields.SemanticCharField):
    pass


class CountryField(core_fields.SemanticCharField):
    pass


# TODO: other SemanticCharField?
class AbstractAddress(CremeModel):
    name = models.CharField(_('Name'), max_length=100, blank=True)

    # Not viewable by users, For administrators currently.
    created = core_fields.CreationDateTimeField().set_tags(viewable=False)
    modified = core_fields.ModificationDateTimeField().set_tags(viewable=False)

    address = models.TextField(_('Address'), blank=True)
    po_box = models.CharField(
        _('PO box'), max_length=50, blank=True,
    ).set_tags(optional=True)
    zipcode = ZipCodeField(
        _('Zip code'), max_length=100, blank=True,
    ).set_tags(optional=True)
    city = CityField(
        _('City'), max_length=100, blank=True,
    ).set_tags(optional=True)
    department = DepartmentField(
        _('Department'), max_length=100, blank=True,
    ).set_tags(optional=True)
    state = models.CharField(
        _('State'), max_length=100, blank=True,
    ).set_tags(optional=True)
    country = CountryField(
        _('Country'), max_length=40, blank=True,
    ).set_tags(optional=True)

    content_type = core_fields.EntityCTypeForeignKey(
        related_name='+', editable=False,
    ).set_tags(viewable=False)
    object = models.ForeignKey(
        CremeEntity, related_name='persons_addresses',
        editable=False, on_delete=models.CASCADE,
    ).set_tags(viewable=False)
    owner = core_fields.RealEntityForeignKey(ct_field='content_type', fk_field='object')

    # Can be used by third party code to store the data they want,
    # without having to modify the code.
    extra_data = models.JSONField(editable=False, default=dict).set_tags(viewable=False)

    creation_label = _('Create an address')
    save_label     = _('Save the address')

    STR_FIELD_NAMES: list[list[str]] = [
        ['address', 'zipcode', 'city', 'department'],
        ['po_box', 'state', 'country'],
    ]
    STR_SEPARATOR = ' '

    class Meta(CremeModel.Meta):
        abstract = True
        app_label = 'persons'
        verbose_name = _('Address')
        verbose_name_plural = _('Addresses')
        ordering = ('id',)

    def __str__(self):
        s = ''
        join = self.STR_SEPARATOR.join
        allowed_fnames = {*self.info_field_names()}

        def field_value(fname):
            return getattr(self, fname) if fname in allowed_fnames else None

        for field_names in self.STR_FIELD_NAMES:
            s = join(filter(None, (field_value(fn) for fn in field_names)))

            if s:
                break

        return s

    def get_edit_absolute_url(self):
        return reverse('persons__edit_address', args=(self.id,))

    def get_related_entity(self):  # For generic views
        return self.owner

    def __bool__(self):  # Used by forms to detect empty addresses
        return any(fvalue for fname, fvalue in self.info_fields)

    def clone(self, entity):
        """Returns a new cloned (saved) address for a (saved) entity."""
        return type(self).objects.create(owner=entity, **dict(self.info_fields))

    @classmethod
    def info_field_names(cls) -> tuple[str, ...]:
        is_field_hidden = FieldsConfig.objects.get_for_model(cls).is_field_hidden
        return tuple(
            f.name
            for f in cls._meta.fields
            if f.get_tag(FieldTag.VIEWABLE) and not is_field_hidden(f)
        )

    @property
    def info_fields(self) -> Iterator[tuple[str, Any]]:
        for fname in self.info_field_names():
            yield fname, getattr(self, fname)


class Address(AbstractAddress):
    class Meta(AbstractAddress.Meta):
        swappable = 'PERSONS_ADDRESS_MODEL'
