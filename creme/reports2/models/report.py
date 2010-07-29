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

from django.contrib.contenttypes.models import ContentType
from django.db.models.fields.related import ManyToManyField, ForeignKey
from django.db.models.fields import CharField, PositiveIntegerField, PositiveSmallIntegerField, IntegerField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity, Filter, CremeModel
from creme_core.models.custom_field import CustomField
from creme_core.utils.meta import get_field_infos
from creme_core.models.header_filter import HFI_FUNCTION, HFI_RELATION, HFI_FIELD, HFI_CUSTOM

report_prefix_url   = '/reports2' #TODO : Remove me when remove reports app
report_template_dir = 'reports2' #TODO : Remove me when remove reports app

class Field(CremeModel):
    name      = CharField(_(u'Nom de la colonne'), max_length=100)
    title     = CharField(max_length=100)
    order     = PositiveIntegerField()
    type      = PositiveSmallIntegerField() #==> {HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM}#Add in choices ?
    report_id = IntegerField(blank=True, null=True)

    _report = None

    class Meta:
        app_label = 'reports2'
        verbose_name = _(u'Colone de rapport')
        verbose_name_plural  = _(u'Colonnes de rapport')
        ordering = ['order']

    def __unicode__(self):
        return self.title

    def _get_report(self):
        if self._report is not None:
            return self._report

        if self.report_id:
            return Report2.objects.get(pk=self.report_id)#Let the exception be throwed?

    def _set_report(self, report):
        self._report = report
        self.report_id = report.id if report else None

    report = property(_get_report, _set_report)


    @staticmethod
    def get_instance_from_hf_item(hf_item):
        """
            @Returns : A Field instance (not saved !) built from an HeaderFilterItem instance
        """
        return Field(name=hf_item.name, title=hf_item.title, order=hf_item.order, type=hf_item.type)

    def get_children_fields_flat(self):
        """
            @Returns: A list containing all children fields of self but self excluded
        """
        if self.report is None:
            return []

        sub_fields = []

        for field in self.report.columns.all().order_by('order'):
            if field.report:
                sub_fields.extend(field.get_children_fields_flat())
            else:
                sub_fields.append(field)

        return sub_fields
        
    def get_children_fields_with_hierarchy(self):
        """
            @Returns: A "hierarchical" dict in the format :
            {'children': [{'children': [], 'field': <Field: Prénom>, 'report': None},
                          {'children': [],
                           'field': <Field: Fonction - Intitulé>,
                           'report': None},
                          {'children': [{'children': [],
                                         'field': <Field: Civilité - ID>,
                                         'report': None},
                                        {'children': [],
                                         'field': <Field: Adresse de livraison - object id>,
                                         'report': None},
                                        {'children': [],
                                         'field': <Field: Est un utilisateur - mot de passe>,
                                         'report': None},
                                        {'children': [],
                                         'field': <Field: cf3>,
                                         'report': None},
                                        {'children': [{'children': [],
                                                       'field': <Field: Prénom>,
                                                       'report': None},
                                                      {'children': [],
                                                       'field': <Field: est en relation avec / est en relation avec>,
                                                       'report': None}],
                                         'field': <Field: est en relation avec / est en relation avec>,
                                         'report': <Report2: Rapport 4>}],
                           'field': <Field: est en relation avec / est en relation avec>,
                           'report': <Report2: Rapport 3>}],
             'field': <Field: self>,
             'report': <Report2: self.report>}
        """
        field_dict = {'field' : self, 'children' : [], 'report' : None}
        report = self.report
        if report:
            fields = report.columns.all().order_by('order')
            field_dict['children'] = [field.get_children_fields_with_hierarchy() for field in fields]
            field_dict['report'] = report
            
        return field_dict

    def get_value(self, entity):
        column_type = self.type
        column_name = self.name

        if column_type == HFI_FIELD:
            model_field, value = get_field_infos(entity, column_name)
            return value

        elif column_type == HFI_CUSTOM:
            try:
                cf = CustomField.objects.get(name=column_name, content_type=entity.entity_type)
            except CustomField.DoesNotExist:
                return ""
            return entity.get_custom_value(cf)

        elif column_type == HFI_RELATION:
            return entity.get_related_entities(column_name, True)

        elif column_type == HFI_FUNCTION:
            try:
                return getattr(entity, column.name)()
            except AttributeError:
                pass
            
        return ""

class Report2(CremeEntity):
    name    = CharField(_(u'Nom du rapport'), max_length=100)
    ct      = ForeignKey(ContentType, verbose_name=_(u"Type d'entité"))
    columns = ManyToManyField(Field, verbose_name=_(u"Colonnes affichées"))
    filter  = ForeignKey(Filter, verbose_name=_(u'Filtre'), blank=True, null=True)

    class Meta:
        app_label = 'reports2'
        verbose_name = _(u'Rapport')
        verbose_name_plural  = _(u'Rapports')
        ordering = ['name']

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "%s/report/%s" % (report_prefix_url, self.id)

    def get_edit_absolute_url(self):
        return "%s/report/edit/%s" % (report_prefix_url, self.id)

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "%s/reports" % report_prefix_url

    def get_delete_absolute_url(self):
        return "%s/report/delete/%s" % (report_prefix_url, self.id)

    def get_ascendants_reports(self):

        fields = Field.objects.filter(report_id=self.id)

        asc_reports = []

        for field in fields:
            asc_reports.extend(Report2.objects.filter(columns__id=field.id))

        for report in asc_reports:
            asc_reports.extend(report.get_ascendants_reports())

        return set(asc_reports)

    def fetch(self):
        res   = []
        ct    = self.ct
        model = ct.model_class()
        model_manager = model.objects
        columns = self.columns.all()

        for entity in model_manager.all():#Pagination ?!

            entity_dict = {'entity' : entity, 'values': {}}

            for column in columns:
                column_name = column.name

                entity_dict['values'][column_name] = ""

                fields = column.get_children_fields_with_hierarchy()

                if fields['children']:
                    pass#TODO: Implements me
                else:
                    entity_dict['values'][column_name] = column.get_value(entity)
            res.append(entity_dict)
        return res

#    def fetch(self):
#        res   = []
#        ct    = self.ct
#        model = ct.model_class()
#        model_manager = model.objects
#        columns = self.columns.all()
#
##        _cf_manager = CustomField.objects.filter(content_type=ct)
#
#        for entity in model_manager.all():#Pagination ?!
#
#            entity_dict = {'entity' : entity, 'values': {}}
##            entity_get_custom_value = entity.get_custom_value
#
#            for column in columns:
#                column_name = column.name
#
#                entity_dict['values'][column_name] = ""
#
#                fields = column.get_children_fields_with_hierarchy()
#
#                if fields['children']:
#                    pass
#                else:
#                    entity_dict['values'][column_name] = column.get_value(entity)
##                    column_type = column.type
##
##                    if column_type == HFI_FIELD:
##                        model_field, value = get_field_infos(entity, column_name)
##                        entity_dict['values'][column_name] = value
##
##                    elif column_type == HFI_CUSTOM:
##                        try:
##                            cf = _cf_manager.get(name=column_name)
##                        except CustomField.DoesNotExist:
##                            continue
##                        entity_dict['values'][column_name] = entity_get_custom_value(cf)
##
##                    elif column_type == HFI_RELATION:
##                        entity_dict['values'][column_name] = entity.get_related_entities(column_name, True)
##
##                    elif column_type == HFI_FUNCTION:
##                        entity_dict['values'][column_name] = getattr(entity, column.name)()
#            res.append(entity_dict)
#        return res
                        



