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
from django.db.models.fields import CharField, PositiveIntegerField, PositiveSmallIntegerField, IntegerField, BooleanField
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict as OrderedDict #use python2.6 OrderedDict later.....

from creme_core.models import CremeAbstractEntity, CremeEntity, Filter, CremeModel
from creme_core.models.custom_field import CustomField
from creme_core.utils.meta import (get_field_infos, get_model_field_infos,
                                   filter_entities_on_ct, get_fk_entity, get_m2m_entities)
from creme_core.models.header_filter import HFI_FUNCTION, HFI_RELATION, HFI_FIELD, HFI_CUSTOM


report_prefix_url   = '/reports2' #TODO : Remove me when remove reports app
report_template_dir = 'reports2' #TODO : Remove me when remove reports app

class Field(CremeModel):
    name      = CharField(_(u'Nom de la colonne'), max_length=100)
    title     = CharField(max_length=100)
    order     = PositiveIntegerField()
    type      = PositiveSmallIntegerField() #==> {HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM}#Add in choices ?
    selected  = BooleanField(default=False)
    report    = ForeignKey("Report2", blank=True, null=True)

    class Meta:
        app_label = 'reports2'
        verbose_name = _(u'Colone de rapport')
        verbose_name_plural  = _(u'Colonnes de rapport')
        ordering = ['order']

    def __unicode__(self):
        return self.title

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

            fields_through = [f['field'].__class__ for f in get_model_field_infos(entity.__class__, column_name)]
            if ManyToManyField in fields_through:
                return get_m2m_entities(entity, self)

            model_field, value = get_field_infos(entity, column_name)
            return unicode(value)#Maybe format map (i.e : datetime...)

        elif column_type == HFI_CUSTOM:
            try:
                cf = CustomField.objects.get(name=column_name, content_type=entity.entity_type)
            except CustomField.DoesNotExist:
                return ""
            return entity.get_custom_value(cf)

        elif column_type == HFI_RELATION:
            related_entities = entity.get_related_entities(column_name, True)

#            if self.report:
#                return filter_entities_on_ct(related_entities, ct)

            if self.selected:
                return related_entities
            return ', '.join(unicode(related_entity) for related_entity in related_entities)

        elif column_type == HFI_FUNCTION:
            try:
                return getattr(entity, column_name)()
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

        fields = Field.objects.filter(report__id=self.id)

        asc_reports = []

        for field in fields:
            asc_reports.extend(Report2.objects.filter(columns__id=field.id))

        for report in asc_reports:
            asc_reports.extend(report.get_ascendants_reports())

        return set(asc_reports)

    @staticmethod
    def get_sub_dict(columns, entity, report_entities):
        dict = OrderedDict
        
        entity_dict = dict({'entity' : entity, 'values': dict()})

        for c in columns:
            if c.report:
                if c.type == HFI_RELATION  and c.selected:
                    entity_dict['values'][c.name] = c.report.fetch(filter_entities_on_ct(entity.get_related_entities(c.name, True), c.report.ct))
                elif c.type == HFI_RELATION  and not c.selected:
                    entity_dict['values'][c.name] = ', '.join(unicode(s) for s in c.report.fetch(filter_entities_on_ct(entity.get_related_entities(c.name, True), c.report.ct)))
                else:
                    entity_dict['values'][c.name] = c.report.fetch(report_entities)
            else:
                entity_dict['values'][c.name] = c.get_value(entity)

        return entity_dict

    def fetch(self, scope=None):
        res   = []
        ct    = self.ct
        model = ct.model_class()
        model_manager = model.objects
        columns = self.columns.all()

        dict = OrderedDict

        _cf_manager = CustomField.objects.filter(content_type=ct)

        #Have to apply report filter on scope here ?
        if scope is not None:
            entities = scope
        else:
            if self.filter is not None:
                entities = model_manager.filter(self.filter.get_q())
            else:
                entities = model_manager.all()

        for entity in entities:
            entity_dict = dict({'entity': entity, 'values': dict()})
            entity_get_custom_value = entity.get_custom_value

            for column in columns:

                column_name   = column.name
                column_report = column.report
                column_type   = column.type
                column_selected = column.selected

                entity_dict['values'][column_name] = ""

                if column_type == HFI_FIELD:

                    field_infos = get_model_field_infos(model, column_name)
                    fields_through = [f['field'].__class__ for f in field_infos]

                    if column_selected and column_report:
                        
                        column_report_columns = column_report.columns.all()

                        if ForeignKey in fields_through:
                            fk_entity = get_fk_entity(entity, column)
                            entity_dict['values'][column_name] = Report2.get_sub_dict(column_report_columns, fk_entity, [fk_entity])

                            d = dict({'entity': fk_entity, 'values': {}})
                            
                            for c in column_report_columns:
                                if c.report and c.selected:
                                    d['values'][c.name] = c.report.fetch([fk_entity])
                                else:
                                    d['values'][c.name] = c.get_value(fk_entity)
                                                                 
                        elif ManyToManyField in fields_through:
                            m2m_entities = get_m2m_entities(entity, column)
                            entity_dict['values'][column_name] = [Report2.get_sub_dict(column_report_columns, m2m_entity, None) for m2m_entity in m2m_entities]
                        else:
                            entity_dict['values'][column_name] = Report2.get_sub_dict(column_report_columns, entity, None)
                    else:
                        if ManyToManyField in fields_through:
                            entity_dict['values'][column_name] = get_m2m_entities(entity, column, True)
                        else:
                            model_field, value = get_field_infos(entity, column_name)
                            entity_dict['values'][column_name] = unicode(value)#Maybe format map (i.e : datetime...)

                elif column_type == HFI_CUSTOM:
                    try:
                        cf = _cf_manager.get(name=column_name)
                    except CustomField.DoesNotExist:
                        continue
                    entity_dict['values'][column_name] = entity_get_custom_value(cf)

                elif column_type == HFI_RELATION:

                    relation_entities = entity.get_related_entities(column_name, True)
                    
                    if column_selected and column_report:
                        relation_entities = filter_entities_on_ct(relation_entities, column_report.ct)

#                        entity_dict['values'][column_name] = [{'entity' : relation_entity,
#                                                               'values': dict((c.name, c.report.fetch(filter_entities_on_ct(relation_entity.get_related_entities(c.name, True), column_report.ct) ) ) if c.report else (c.name, c.get_value(relation_entity)) for c in column_report.columns.all())
#                                                              } for relation_entity in relation_entities]

                        entity_dict['values'][column_name] = []

                        for relation_entity in relation_entities:
                            d = dict({'entity' : relation_entity, 'values':{}})
                            for c in column_report.columns.all():
                                if c.report:
                                    if c.type == HFI_RELATION and c.selected:
                                        d['values'][c.name] = c.report.fetch(filter_entities_on_ct(relation_entity.get_related_entities(c.name, True), c.report.ct) )
                                    elif c.type == HFI_RELATION and not c.selected:
                                        d['values'][c.name] = ", ".join(unicode(s) for s in c.report.fetch(filter_entities_on_ct(relation_entity.get_related_entities(c.name, True), c.report.ct) ))
                                    else:
                                        d['values'][c.name] = c.report.fetch()
                                else:
                                    d['values'][c.name] = c.get_value(relation_entity)
                            entity_dict['values'][column_name].append(d)

                    else:
                        if not column_selected:
                            entity_dict['values'][column_name] = ', '.join(unicode(relation_entity) for relation_entity in relation_entities)
                        else:
                            entity_dict['values'][column_name] = relation_entities

                elif column_type == HFI_FUNCTION:
                    entity_dict['values'][column_name] = getattr(entity, column_name)()

            res.append(entity_dict)
        return res

    def fetch_all_lines(self):
        tree = self.fetch()

        lines = []

        class ReportTree(object):
            def __init__(self, tree):
                self.entity = tree['entity']
                self.values = tree['values']

            @staticmethod
            def build_sub_line(lines, value, current_line, set_keys=False):
                idx = current_line.index(None)


            def visit(self, lines, current_line, set_keys=False):

                have_to_build = False
                value_to_build = None

                for i, (column, value) in enumerate(self.values.iteritems()):
                    if issubclass(value.__class__, dict):
                        ReportTree(value).visit(lines, current_line, set_keys=set_keys)

                    elif isinstance(value, (list, tuple)):
                        current_line.append(None)
                        have_to_build = True
                        value_to_build = value

                    else:
                        val = {column:value} if set_keys else value
                        current_line.append(val)

                if have_to_build:
                    for v in value_to_build:
                        ReportTree.build_sub_line(lines, v, list(current_line), set_keys=False)
                else:
                    lines.append(current_line)


            def get_lines(self):
                lines = []
                self.visit(lines, [], set_keys=True)
                return lines

            def __repr__(self):
                return "self.entity : %s, self.values : %s" % (self.entity, self.values)

        for node in tree:
            lines.extend(ReportTree(node).get_lines())

        return lines