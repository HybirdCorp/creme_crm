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

from future_builtins import filter

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import CharField, TextField, ForeignKey, PositiveIntegerField, CASCADE
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeModel, FieldsConfig


class AbstractAddress(CremeModel):
    name       = CharField(_(u'Name'), max_length=100, blank=True)
    address    = TextField(_(u'Address'), blank=True)
    po_box     = CharField(_(u'PO box'), max_length=50, blank=True).set_tags(optional=True)
    zipcode    = CharField(_(u'Zip code'), max_length=100, blank=True).set_tags(optional=True)
    city       = CharField(_(u'City'), max_length=100, blank=True).set_tags(optional=True)
    department = CharField(_(u'Department'), max_length=100, blank=True).set_tags(optional=True)
    state      = CharField(_(u'State'), max_length=100, blank=True).set_tags(optional=True)
    country    = CharField(_(u'Country'), max_length=40, blank=True).set_tags(optional=True)

    # TODO: use a real ForeignKey to CremeEntity (+ remove signal handlers )
    content_type = ForeignKey(ContentType, related_name="object_set", editable=False, on_delete=CASCADE)\
                             .set_tags(viewable=False)
    object_id    = PositiveIntegerField(editable=False).set_tags(viewable=False)
    owner        = GenericForeignKey(ct_field="content_type", fk_field="object_id")

    STR_FIELD_NAMES = [
        ['address', 'zipcode', 'city', 'department'],
        ['po_box', 'state', 'country'],
    ]
    STR_SEPARATOR = u' '

    # class Meta:
    class Meta(CremeModel.Meta):
        abstract = True
        app_label = 'persons'
        verbose_name = _(u'Address')
        verbose_name_plural = _(u'Addresses')
        ordering = ('id',)

    def __unicode__(self):
        s = u''
        join = self.STR_SEPARATOR.join
        allowed_fnames = set(self.info_field_names())
        get_field_value = (lambda fname: None if fname not in allowed_fnames else
                                         getattr(self, fname))

        for field_names in self.STR_FIELD_NAMES:
            s = join(filter(None, (get_field_value(fn) for fn in field_names)))

            if s:
                break

        return s

    def get_edit_absolute_url(self):
        return reverse('persons__edit_address', args=(self.id,))

    def get_related_entity(self):  # For generic views
        return self.owner

    def __nonzero__(self):  # Used by forms to detect empty addresses
        return any(fvalue for fname, fvalue in self.info_fields)

    def clone(self, entity):
        """Returns a new cloned (saved) address for a (saved) entity"""
        return Address.objects.create(object_id=entity.id,
                                      content_type=ContentType.objects.get_for_model(entity),
                                      **dict(self.info_fields)
                                     )

    @classmethod
    def info_field_names(cls):
        is_field_hidden = FieldsConfig.get_4_model(cls).is_field_hidden
        excluded = {'id', 'content_type', 'object_id'}
        return tuple(f.name
                        for f in cls._meta.fields
                            if f.name not in excluded and not is_field_hidden(f)
                    )

    @property
    def info_fields(self):
        for fname in self.info_field_names():
            yield fname, getattr(self, fname)


class Address(AbstractAddress):
    class Meta(AbstractAddress.Meta):
        swappable = 'PERSONS_ADDRESS_MODEL'
