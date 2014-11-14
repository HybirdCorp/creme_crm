# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

import logging

from django.db.models import ForeignKey
from django.db.transaction import commit_on_success
from django.forms import Field, Widget, Select, CheckboxInput
from django.forms.models import fields_for_model, model_to_dict
from django.forms.util import flatatt
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils.translation import ugettext as _

from ..models import CremeEntity, CustomField, CustomFieldValue
from ..signals import pre_merge_related
from ..gui.merge import merge_form_registry
from .base import CremeForm, _CUSTOM_NAME


logger = logging.getLogger(__name__)


class EntitiesHeaderWidget(Widget):
    def render(self, name, value, attrs=None):
        value_1, value_2, value_m = value or ('', '', '')

        return mark_safe(u'<ul %(attrs)s>'
                             ' <li class="li_merge_entity_header1">%(header_1)s</li>'
                             ' <li class="li_merge_result_header">%(header_merged)s</li>'
                             ' <li class="li_merge_entity_header2">%(header_2)s</li>'
                          '</ul>' % {
                            'attrs':         flatatt(self.build_attrs(attrs, name=name, **{'class': 'merge_entity_field ui-layout hbox'})),
                            'header_1':      escape(value_1),
                            'header_merged': escape(value_m),
                            'header_2':      escape(value_2),
                          }
                        )


class MergeWidget(Widget):
    def __init__(self, original_widget, *args, **kwargs):
        super(MergeWidget, self).__init__(*args, **kwargs)
        self._original_widget = original_widget

    def render(self, name, value, attrs=None, choices=()):
        value_1, value_2, value_m = value or ('', '', '')
        widget = self._original_widget
        render = widget.render
        #TODO: improve Wigdets with a 'read_only' param -> each type choose the right html attribute
        ro_attr = 'disabled' if isinstance(widget, (Select, CheckboxInput)) else 'readOnly'

        return mark_safe(u'<ul %(attrs)s>'
                              '<li class="li_merge_entity1">%(input_1)s</li>'
                              '<li class="li_merge_result">%(input_merged)s</li>'
                              '<li class="li_merge_entity2">%(input_2)s</li>'
                          '</ul>' % {
                            'attrs':        flatatt(self.build_attrs(attrs, name=name, **{'class': 'merge_entity_field ui-layout hbox'})),
                            'input_1':      render('%s_1' % name,      value_1, attrs={ro_attr: True, 'class': 'merge_entity1'}),
                            'input_merged': render('%s_merged' % name, value_m, attrs={'class': 'merge_result'}),
                            'input_2':      render('%s_2' % name,      value_2, attrs={ro_attr: True, 'class': 'merge_entity2'}),
                          }
                        )

    def value_from_datadict(self, data, files, name):
        value_from_datadict = self._original_widget.value_from_datadict
        return (value_from_datadict(data, files, '%s_1' % name),
                value_from_datadict(data, files, '%s_2' % name),
                value_from_datadict(data, files, '%s_merged' % name),
               )


class MergeField(Field):
    def __init__(self, modelform_field, model_field, *args, **kwargs):
        super(MergeField, self).__init__(self, widget=MergeWidget(modelform_field.widget), *args, **kwargs)

        self.required = modelform_field.required
        self._original_field = modelform_field
        self._restricted_queryset = None

        #TODO: ManyToManyField ??
        if isinstance(model_field, ForeignKey) and issubclass(model_field.rel.to, CremeEntity):
            qs = modelform_field.queryset
            self._restricted_queryset = qs
            modelform_field.queryset = qs.none()

    def clean(self, value):
        return self._original_field.clean(value[2])

    def set_merge_initial(self, initial):
        self.initial = initial
        qs = self._restricted_queryset

        if qs is not None:
            field = self._original_field
            field.queryset = qs.filter(pk__in=initial)

            if None not in initial:
                field.empty_label = None


class MergeEntitiesBaseForm(CremeForm):
    entities_labels = Field(label="", required=False, widget=EntitiesHeaderWidget)

    class CanNotMergeError(Exception):
        pass

    def __init__(self, entity1, entity2, *args, **kwargs):
        super(MergeEntitiesBaseForm, self).__init__(*args, **kwargs)
        self.entity1 = entity1
        self.entity2 = entity2

        fields = self.fields

        build_initial = self._build_initial_dict
        entity1_initial = build_initial(entity1)
        entity2_initial = build_initial(entity2)

        #the older entity is prefered
        initial_index = 0 if entity1.modified <= entity2.modified else 1

        for name, field in fields.iteritems():
            if name == 'entities_labels':
                field.initial = (unicode(entity1), unicode(entity2), _('Merged entity'))
            else:
                initial = [entity1_initial[name], entity2_initial[name]]
                #we try to initialize with prefered one, but we use the other if it is empty.
                initial.append(initial[initial_index] or initial[1 - initial_index])
                field.set_merge_initial(initial)

        # custom fields --------------------------------------------------------
        #TODO: factorise (CremeEntityForm ? get_custom_fields_n_values ? ...)
        cfields = CustomField.objects.filter(content_type=entity1.entity_type)
        CremeEntity.populate_custom_values([entity1, entity2], cfields)
        self._customs = customs = [(cfield,
                                    entity1.get_custom_value(cfield),
                                    entity2.get_custom_value(cfield),
                                   ) for cfield in cfields
                                  ]

        for i, (cfield, cvalue1, cvalue2) in enumerate(customs):
            formfield1 = cfield.get_formfield(cvalue1)
            fields[_CUSTOM_NAME % i] = merge_field = MergeField(formfield1,
                                                                model_field=None,
                                                                label=cfield.name,
                                                               )

            initial = [formfield1.initial,
                       cfield.get_formfield(cvalue2).initial,
                      ]
            initial.append(initial[initial_index] or initial[1 - initial_index])
            merge_field.set_merge_initial(initial)

    def _build_initial_dict(self, entity):
        return model_to_dict(entity)

    def _post_entity1_update(self, entity1, entity2, cleaned_data):
        for i, (custom_field, cvalue1, cvalue2) in enumerate(self._customs):
            value = cleaned_data[_CUSTOM_NAME % i] #TODO: factorize with __init__() ?
            CustomFieldValue.save_values_for_entities(custom_field, [entity1], value)

            if cvalue2 is not None:
                cvalue2.delete()

    def clean(self):
        cdata = super(MergeEntitiesBaseForm, self).clean()

        if not self._errors:
            entity1 = self.entity1

            for name, value in self.fields.iteritems():
                setattr(entity1, name, cdata[name])

            entity1.full_clean()

        return cdata

    @commit_on_success
    def save(self, *args, **kwargs):
        super(MergeEntitiesBaseForm, self).save(*args, **kwargs)

        entity1 = self.entity1
        entity2 = self.entity2

        entity1.save()
        self._post_entity1_update(entity1, entity2, self.cleaned_data)
        pre_merge_related.send_robust(sender=entity1, other_entity=entity2)

        for rel_objects in entity2._meta.get_all_related_objects():
            field_name = rel_objects.field.name

            for rel_object in getattr(entity2, rel_objects.get_accessor_name()).all():
                setattr(rel_object, field_name, entity1)
                rel_object.save()

        try:
            entity2.delete()
        except Exception as e:
            logger.error('Error when merging 2 entities : the old one "%s"(id=%s) cannot be deleted: %s',
                         entity2, entity2.id, e
                        )


def mergefield_factory(modelfield):
    formfield = modelfield.formfield()

    if not formfield: #happens for crementity_ptr (OneToOneField)
        return None

    return MergeField(formfield, modelfield, label=modelfield.verbose_name)

def form_factory(model):
    #TODO: use a cache ??
    mergeform_factory = merge_form_registry.get(model)
    base_form_class = MergeEntitiesBaseForm if mergeform_factory is None else \
                      mergeform_factory()

    return type('Merge%sForm' % model.__name__, (base_form_class,),
                fields_for_model(model, formfield_callback=mergefield_factory)
               )
