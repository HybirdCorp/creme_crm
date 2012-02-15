# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from logging import error

from django.forms import Field, Widget, Select
from django.forms.models import fields_for_model, model_to_dict
from django.forms.util import flatatt
from django.utils.safestring import mark_safe

from creme_core.forms import CremeForm
from creme_core.signals import pre_merge_related
from creme_core.gui.merge import merge_form_registry


class MergeWidget(Widget):
    def __init__(self, original_widget, *args, **kwargs):
        super(MergeWidget, self).__init__(*args, **kwargs)
        self._original_widget = original_widget

    def render(self, name, value, attrs=None, choices=()):
        value_1, value_2, value_m = value or ('', '', '')
        widget = self._original_widget
        render = widget.render
        #TODO: improve Wigdets with a 'read_only' param -> each type choose the right html attribute
        ro_attr = 'disabled' if isinstance(widget, Select) else 'readOnly'

        return mark_safe(u'<ul %(attrs)s>'
                              '<li>%(input_1)s</li>'
                              '<li>%(input_merged)s</li>'
                              '<li>%(input_2)s</li>'
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
    def __init__(self, modelform_field, *args, **kwargs):
        super(MergeField, self).__init__(self, widget=MergeWidget(modelform_field.widget), *args, **kwargs)

        self.required = modelform_field.required
        self._original_field = modelform_field

    def clean(self, value):
        return self._original_field.clean(value[2])


class MergeEntitiesBaseForm(CremeForm):
    class CanNotMergeError(Exception):
        pass

    def __init__(self, entity1, entity2, *args, **kwargs):
        super(MergeEntitiesBaseForm, self).__init__(*args, **kwargs)
        self.entity1 = entity1
        self.entity2 = entity2

        build_initial = self._build_initial_dict
        entity1_initial = build_initial(entity1)
        entity2_initial = build_initial(entity2)

        #the youngest entity is prefered
        initial_index = 0 if entity1.modified <= entity2.modified else 1

        for name, field in self.fields.iteritems():
            initial = [entity1_initial[name], entity2_initial[name]]
            #we try to initialize with prefered onr, but we use the other if it is empty.
            initial.append(initial[initial_index] or initial[1 - initial_index])

            field.initial = initial

    def _build_initial_dict(self, entity):
        return model_to_dict(entity)

    def _post_entity1_update(self, entity1, entity2, cleaned_data):
        pass

    def clean(self):
        cdata = self.cleaned_data

        if not self._errors:
            entity1 = self.entity1

            for name, value in self.fields.iteritems():
                setattr(entity1, name, cdata[name])

            entity1.full_clean()

        return cdata

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
            error('Error when merging 2 entities : the old one "%s"(id=%s) cannot be deleted: %s',
                  entity2, entity2.id, e
                 )


def mergefield_factory(modelfield):
    formfield = modelfield.formfield()

    if not formfield: #happens for crementity_ptr (OneToOneField)
        return None

    return MergeField(formfield, label=modelfield.verbose_name)

def form_factory(model):
    #TODO: use a cache ??
    mergeform_factory = merge_form_registry.get(model)
    base_form_class = MergeEntitiesBaseForm if mergeform_factory is None else \
                      mergeform_factory()

    return type('Merge%sForm' % model.__name__, (base_form_class,),
                fields_for_model(model, formfield_callback=mergefield_factory)
               )
