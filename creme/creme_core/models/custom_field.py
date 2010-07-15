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

from collections import defaultdict

from django.db.models import ForeignKey, CharField, PositiveSmallIntegerField, IntegerField, DecimalField, DateTimeField, BooleanField
from django import forms
from django.utils.translation import ugettext, ugettext_lazy as _
from django.utils.datastructures import SortedDict as OrderedDict #use python2.6 OrderedDict later.....
from django.contrib.contenttypes.models import ContentType

from base import CremeModel
from entity import CremeEntity


__all__ = ('CustomField', 'CustomFieldValue', 'CustomFieldString', 'CustomFieldInteger',
           'CustomFieldFloat', 'CustomFieldDateTime', 'CustomFieldBoolean',  'CustomFieldEnumValue')


class CustomField(CremeModel):
    INT   = 1
    FLOAT = 2
    BOOL  = 3
    STR   = 10
    DATE  = 20
    ENUM  = 100

    name          = CharField(_(u'Nom du champ'), max_length=100)
    content_type  = ForeignKey(ContentType, verbose_name=_(u'Resource associée'))
    field_type    = PositiveSmallIntegerField(_(u'Type du champ')) #see INT, FLOAT etc...
    #default_value = CharField(_(u'Valeur par defaut'), max_length=100, blank=True, null=True)
    #extra_args    = CharField(max_length=500, blank=True, null=True)
    #required      = BooleanField(defaut=False) ????

    class Meta:
       app_label = 'creme_core'
       verbose_name = _(u'Champ personnalisé')
       verbose_name_plural = _(u'Champs personnalisés')
       ordering = ('id',)

    def __unicode__(self):
        return self.name

    def delete(self):
        for value_class in _TABLES.itervalues():
            value_class.objects.filter(custom_field=self).delete()
        self.customfieldenumvalue_set.all().delete() #Beware: don't call the CustomFieldEnumValue.delete() to avoid loop
        super(CustomField, self).delete()

    def type_verbose_name(self):
        return _TABLES[self.field_type].verbose_name

    @staticmethod
    def get_custom_fields_n_values(entity):
        cfields = CustomField.objects.filter(content_type=entity.entity_type)
        cvalues = {} #key: custom_field.id  value: corresponding CustomFieldValue object
        cfields_groups = defaultdict(list)

        for cfield in cfields:
            cfields_groups[cfield.field_type].append(cfield.id)

        for field_type, cf_id_list in cfields_groups.iteritems():
            for cfv in _TABLES[field_type].objects.filter(custom_field__in=cf_id_list, entity=entity.id):
                cvalues[cfv.custom_field_id] = cfv

        return [(cfield, cvalues.get(cfield.id, '')) for cfield in cfields]

    def get_value_class(self):
        return _TABLES[self.field_type]

    def get_formfield(self, custom_value):
        field =  self.get_value_class().form_field(label=self.name, required=False)

        if self.field_type == CustomField.ENUM: #TODO: move into a CustomFieldEnum method ???
            choices = [('', '-------')]
            choices += CustomFieldEnumValue.objects.filter(custom_field=self).values_list('id', 'value')
            field.choices = choices

            if custom_value:
                field.initial = custom_value.value_id
        elif custom_value:
            field.initial = custom_value.value

        return field


class CustomFieldValue(CremeModel):
    custom_field = ForeignKey(CustomField)
    entity       = ForeignKey(CremeEntity)

    class Meta:
        abstract = True

    def __unicode__(self):
        return unicode(self.value)

    def set_value(self, value):
        if self.value != value:
            self.value = value
            return True

        return False

    @staticmethod
    def get_pretty_value(custom_field_id, entity_id):
        """Return unicode object containing the human readable value of a custom field for an entity
        It manages CustomField which type is ENUM.
        """
        output = u''

        cf = CustomField.objects.get(pk=custom_field_id) #TODO: don't retrieve each time !!!!!
        cf_values = cf.get_value_class().objects.filter(custom_field=custom_field_id, entity=entity_id)

        if cf_values:
            output = unicode(cf_values[0])

        return output

    @classmethod
    def get_related_name(cls):
        return cls.__name__.lower()

    @staticmethod
    def delete_all(entity):
        cf_types = set(CustomField.objects.filter(content_type=entity.entity_type_id)\
                                          .values_list('field_type', flat=True))

        for cf_type in cf_types:
            for cvalue in _TABLES[cf_type].objects.filter(entity=entity):
                cvalue.delete()


class CustomFieldString(CustomFieldValue):
    value = CharField(max_length=100)

    verbose_name = _(u'Chaîne de caractères')
    form_field   = forms.CharField

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return self.value


class CustomFieldInteger(CustomFieldValue):
    value = IntegerField()

    verbose_name = _(u'Nombre entier')
    form_field   = forms.IntegerField

    class Meta:
        app_label = 'creme_core'


class CustomFieldFloat(CustomFieldValue):
    value = DecimalField(max_digits=4, decimal_places=2)

    verbose_name = _(u'Nombre à virgule')
    form_field   = forms.DecimalField

    class Meta:
        app_label = 'creme_core'


class CustomFieldDateTime(CustomFieldValue):
    value = DateTimeField()

    verbose_name = _(u'Date')
    form_field   = forms.DateTimeField #TODO: better widget

    class Meta:
        app_label = 'creme_core'


class CustomFieldBoolean(CustomFieldValue):
    value = BooleanField()

    verbose_name = _(u'Booléen (2 valeurs: Oui/Non)')
    form_field   = forms.BooleanField

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return ugettext(u'Oui') if self.value else ugettext(u'Non')


class CustomFieldEnumValue(CremeModel):
    custom_field = ForeignKey(CustomField, related_name='customfieldenumvalue_set')
    value        = CharField(max_length=100)

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return self.value

    def delete(self):
        CustomFieldEnum.objects.filter(custom_field=self.custom_field_id, value=str(self.id)).delete()
        super(CustomFieldEnumValue, self).delete()


class CustomFieldEnum(CustomFieldValue):
    value = ForeignKey(CustomFieldEnumValue)

    verbose_name = _(u'Liste de choix')
    form_field   = forms.ChoiceField

    class Meta:
        app_label = 'creme_core'

    def set_value(self, value):
        value = int(value)
        if self.value_id != value:
            self.value_id = value
            return True

        return False


_TABLES = OrderedDict([
    (CustomField.INT,    CustomFieldInteger),
    (CustomField.FLOAT,  CustomFieldFloat),
    (CustomField.BOOL,   CustomFieldBoolean),
    (CustomField.STR,    CustomFieldString),
    (CustomField.DATE,   CustomFieldDateTime),
    (CustomField.ENUM,   CustomFieldEnum),
])
