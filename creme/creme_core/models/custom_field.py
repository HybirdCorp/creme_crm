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

from django.db.models import ForeignKey, CharField, PositiveSmallIntegerField, IntegerField, DecimalField, DateTimeField, BooleanField, ManyToManyField
from django import forms
from django.utils.translation import ugettext, ugettext_lazy as _
from django.utils.datastructures import SortedDict as OrderedDict #use python2.6 OrderedDict later.....
from django.contrib.contenttypes.models import ContentType

from base import CremeModel
from entity import CremeEntity


__all__ = ('CustomField', 'CustomFieldValue',
           'CustomFieldInteger', 'CustomFieldFloat', 'CustomFieldBoolean',
           'CustomFieldString', 'CustomFieldDateTime',
           'CustomFieldEnumValue', 'CustomFieldEnum', 'CustomFieldMultiEnum')


class CustomField(CremeModel):
    INT         = 1
    FLOAT       = 2
    BOOL        = 3
    STR         = 10
    DATE        = 20
    ENUM        = 100
    MULTI_ENUM  = 101

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
        return self.get_value_class().get_formfield(self, custom_value)

    def get_pretty_value(self, entity_id):
        """Return unicode object containing the human readable value of this custom field for an entity
        It manages CustomField which type is ENUM.
        """
        #TODO: select_related() for enum ???
        cf_values = self.get_value_class().objects.filter(custom_field=self.id, entity=entity_id)

        return unicode(cf_values[0]) if cf_values else u''

    @staticmethod
    def get_custom_values_map(custom_fields):
        """
        @return { Entity -> { CustomField's id -> CustomValue } }
        """
        cfield_map = defaultdict(list)
        for cfield in custom_fields:
            cfield_map[cfield.field_type].append(cfield)

        cvalues_map = defaultdict(lambda: defaultdict(list))

        for field_type, cfields_list in cfield_map.iteritems():
            for cvalue in _TABLES[field_type]._get_4_cfields(cfields_list):
                cvalues_map[cvalue.entity_id][cvalue.custom_field_id] = cvalue

        return cvalues_map


class CustomFieldValue(CremeModel):
    custom_field = ForeignKey(CustomField)
    entity       = ForeignKey(CremeEntity)
    #value       = FoobarField()  --> implement in inherited classes

    form_field = forms.Field #overload meeee

    class Meta:
        abstract = True

    def __unicode__(self):
        return unicode(self.value)

    @classmethod
    def _get_4_cfields(cls, cfields):
        """Retrieve all custom values for a list of custom fields with the same type.
        Trick: overload me to optimise the query (eg: use a select_related())
        """
        return cls.objects.filter(custom_field__in=cfields)

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

    @staticmethod
    def _build_formfield(custom_field, formfield):
        pass

    def _set_formfield_value(self, field):
        field.initial = self.value

    @classmethod
    def get_formfield(cls, custom_field, custom_value):
        field = cls.form_field(label=custom_field.name, required=False)
        cls._build_formfield(custom_field, field)

        if custom_value:
            custom_value._set_formfield_value(field)

        return field

    def set_value_n_save(self, value):
        if self.value != value:
            self.value = value
            self.save()


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

    @classmethod
    def _get_4_cfields(cls, cfields):
        return cls.objects.filter(custom_field__in=cfields).select_related('value')

    @staticmethod
    def _build_formfield(custom_field, formfield):
        choices = [('', '-------')]
        choices += CustomFieldEnumValue.objects.filter(custom_field=custom_field).values_list('id', 'value')
        formfield.choices = choices

    def _set_formfield_value(self, field):
        field.initial = self.value_id

    def set_value_n_save(self, value):
        value = int(value)
        if self.value_id != value:
            self.value_id = value
            self.save()


class CustomFieldMultiEnum(CustomFieldValue):
    value = ManyToManyField(CustomFieldEnumValue)

    verbose_name = _(u'Liste de choix (multi sélection)')
    form_field   = forms.MultipleChoiceField

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        #output = ['<ul>']
        #output.extend(u'<li>%s</li>' % val for val in self.value.all())
        #output.append('</ul>')
        #return u''.join(output)
        return u' / '.join(unicode(val) for val in self.value.all())

    @classmethod
    def _get_4_cfields(cls, cfields):
        #return cls.objects.filter(custom_field__in=cfields).select_related('value')
        return cls.objects.filter(custom_field__in=cfields) #select_related('value') useless no ?

    @staticmethod
    def _build_formfield(custom_field, formfield):
        formfield.choices = CustomFieldEnumValue.objects.filter(custom_field=custom_field).values_list('id', 'value')

    def _set_formfield_value(self, field):
        field.initial = self.value.all().values_list('id', flat=True)

    def set_value_n_save(self, value):
        if not self.pk:
            self.save() #M2M field need a pk

        self.value = value


_TABLES = OrderedDict([
    (CustomField.INT,        CustomFieldInteger),
    (CustomField.FLOAT,      CustomFieldFloat),
    (CustomField.BOOL,       CustomFieldBoolean),
    (CustomField.STR,        CustomFieldString),
    (CustomField.DATE,       CustomFieldDateTime),
    (CustomField.ENUM,       CustomFieldEnum),
    (CustomField.MULTI_ENUM, CustomFieldMultiEnum),
])
