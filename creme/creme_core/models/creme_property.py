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

from django.db.models import CharField, ForeignKey, PositiveIntegerField, ManyToManyField
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey

from creme_core.models import CremeModel


class CremePropertyType(CremeModel):
    id             = CharField(primary_key=True, max_length=100)
    text           = CharField(max_length=200, unique=True)
    subject_ctypes = ManyToManyField(ContentType, blank=True, null=True, related_name='subject_ctypes_creme_property_set')

    def __unicode__(self):
        return self.text

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Type de propriété')
        verbose_name_plural = _(u'Types de propriété')

    def delete(self):
        self.property_i18n_set.all().delete()
        super(CremePropertyType, self).delete()


class CremePropertyText_i18n(CremeModel):
    property_type = ForeignKey(CremePropertyType, related_name='property_i18n_set')
    language_code = CharField(max_length=5)
    i18n_text     = CharField(max_length=100)

    class Meta:
        app_label = 'creme_core'


class CremeProperty(CremeModel):
    type         = ForeignKey(CremePropertyType)
    subject_ct   = ForeignKey(ContentType, related_name="objects_properties_set")
    subject_id   = PositiveIntegerField()
    creme_entity = GenericForeignKey(ct_field="subject_ct", fk_field="subject_id")

    def __init__ (self, *args, **kwargs):
        super(CremeProperty, self).__init__(*args, **kwargs)
        self.Save_In_Init = kwargs.get('Save_In_Init', False) #TODO: useful to stock it in an attribute ???

        if not self.pk and self.Save_In_Init:
            self.save ()

    def __unicode__(self):
        return force_unicode(u"%s a la propriété: %s" % (self.creme_entity, self.type))

    def save(self):
        self.Save_In_Init = not bool(self.pk)

        super(CremeProperty, self).save()

        if self.Save_In_Init:
            self.creme_entity.properties.add(self)

    @staticmethod
    def get_for_type(type=None):
        if not type:
            return []
        return CremeProperty.objects.filter(type=type)

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Propriété')
        verbose_name_plural = _(u'Propriétés')


def create_property_type(str_pk, text, subject_ctypes=(), generate_pk=False):
    """
    @param subject_ctypes Sequence of CremeEntity classes/ContentType objects.
    @param generate_pk If True, str_pk is used as prefix to generate pk.
    """
    if not generate_pk:
        from creme_core.utils import create_or_update_models_instance as create
        property_type = create(CremePropertyType, str_pk, text=text)
    else:
        from creme_core.utils.id_generator import generate_string_id_and_save
        property_type = CremePropertyType(text=text)
        generate_string_id_and_save(CremePropertyType, [property_type], str_pk)

    property_type.property_i18n_set.all().delete()
    CremePropertyText_i18n.objects.create(property_type_id=property_type.id, language_code='FRA', i18n_text=text)

    get_ct = ContentType.objects.get_for_model
    property_type.subject_ctypes = [(model if isinstance(model, ContentType) else get_ct(model)) for model in subject_ctypes]

    return property_type





