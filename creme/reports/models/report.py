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
from django.db.models.fields import CharField, PositiveIntegerField, PositiveSmallIntegerField, BooleanField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity, Filter, CremeModel
from creme_core.models.custom_field import CustomField
from creme_core.utils.meta import (get_field_infos, get_model_field_infos,
                                   filter_entities_on_ct, get_fk_entity, get_m2m_entities)
from creme_core.models.header_filter import HFI_FUNCTION, HFI_RELATION, HFI_FIELD, HFI_CUSTOM

report_prefix_url   = '/reports'
report_template_dir = 'reports'

class DropLine(Exception):
    pass

class FkClass(object):
    """A simple container to handle values for a foreign key which requires particular
        treatment in fetch & fetch_all_lines functions
    """
    __slot__ = ['values']

    def __init__(self, values):
        self.values = values

    def __repr__(self):
        return u"<FkClassObject : %s>" % self.values

    def __iter__(self):
        return iter(self.values)
#        for val in self.values:
#            yield val

class Field(CremeModel):
    name      = CharField(_(u'Nom de la colonne'), max_length=100)
    title     = CharField(max_length=100)
    order     = PositiveIntegerField()
    type      = PositiveSmallIntegerField() #==> {HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM}#Add in choices ?
    selected  = BooleanField(default=False)
    report    = ForeignKey("Report", blank=True, null=True)

    class Meta:
        app_label = 'reports'
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
        cols = []
        col = self.get_children_fields_with_hierarchy()
        children, report, field = col.get('children'), col.get('report'), col.get('field')

        if children and report is not None and field.selected:
            for sub_col in children:
                cols.extend(sub_col['field'].get_children_fields_flat())
        else:
            cols.append(field)
        return cols


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
                                         'report': <Report: Rapport 4>}],
                           'field': <Field: est en relation avec / est en relation avec>,
                           'report': <Report: Rapport 3>}],
             'field': <Field: self>,
             'report': <Report: self.report>}
        """
        field_dict = {'field' : self, 'children' : [], 'report' : None}
        report = self.report
        if report:
            fields = report.columns.all().order_by('order')
            field_dict['children'] = [field.get_children_fields_with_hierarchy() for field in fields]
            field_dict['report'] = report
            
        return field_dict

    def get_value(self, entity=None, selected=None):
        column_type = self.type
        column_name = self.name
        report = self.report
        selected = selected or self.selected
        empty_value = u""

        if column_type == HFI_FIELD:
            if entity is None and report and selected:
                return FkClass([empty_value for c in report.columns.all()])#Only fk requires a multi-padding
            elif entity is None:
                return empty_value

            fields_through = [f['field'].__class__ for f in get_model_field_infos(entity.__class__, column_name)]
            if ManyToManyField in fields_through:
                if report and selected:
                    res = []

                    if report.filter is not None:
                        m2m_entities = get_m2m_entities(entity, self.name, False, report.filter.get_q())
                    else:
                        m2m_entities = get_m2m_entities(entity, self.name, False)

                    for m2m_entity in m2m_entities:
                        sub_res = []
                        self._handle_report_values(sub_res, m2m_entity)
                        res.append(sub_res)

                    if not m2m_entities:
                        self._handle_report_values(res)
                        res = [res]

                    return res
                else:
                    return get_m2m_entities(entity, self.name, True)

            elif ForeignKey in fields_through and report and selected:
                fk_entity = get_fk_entity(entity, self.name)

                if (report.filter is not None and
                    fk_entity not in report.ct.model_class().objects.filter(report.filter.get_q())):
                        raise DropLine

                res = []
                self._handle_report_values(res, fk_entity)

                return FkClass(res)

            model_field, value = get_field_infos(entity, column_name)
            return unicode(value or empty_value)#Maybe format map (i.e : datetime...)
        
        elif column_type == HFI_CUSTOM:
            if entity is None:
                return empty_value

            try:
                cf = CustomField.objects.get(name=column_name, content_type=entity.entity_type)
            except CustomField.DoesNotExist:
                return empty_value
            return entity.get_custom_value(cf)

        elif column_type == HFI_RELATION:
            related_entities = entity.get_related_entities(column_name, True) if entity is not None else []

            if report and selected:#TODO: Apply self.report filter AND/OR filter_entities_on_ct(related_entities, ct) ?
#                scope = related_entities
                scope = filter_entities_on_ct(related_entities, report.ct)

                if report.filter is not None:
                    scope = report.ct.model_class().objects.filter(pk__in=[e.id for e in scope])
                    scope = scope.filter(report.filter.get_q())

                res = []
                for rel_entity in scope:
                    rel_entity_res = []
                    self._handle_report_values(rel_entity_res, rel_entity)
                    res.append(rel_entity_res)

                if not scope:#We have to keep columns' consistance and pad with blank values
                    self._handle_report_values(res)
                    res = [res]

                return res

            if selected:
#                return related_entities
                return [[unicode(related_entity)] for related_entity in related_entities]

            return u", ".join(unicode(related_entity) for related_entity in related_entities) or empty_value

        elif column_type == HFI_FUNCTION:
            try:
                return getattr(entity, column_name)()
            except AttributeError:
                pass

        return empty_value

    def _handle_report_values(self, container, entity=None):
        for c in self.report.columns.all():
            sub_val = c.get_value(entity)
            if isinstance(sub_val, FkClass):
                container.extend(sub_val)
            else:
                container.append(sub_val)


class Report(CremeEntity):
    name    = CharField(_(u'Nom du rapport'), max_length=100)
    ct      = ForeignKey(ContentType, verbose_name=_(u"Type d'entité"))
    columns = ManyToManyField(Field, verbose_name=_(u"Colonnes affichées"), related_name='report_columns_set')
    filter  = ForeignKey(Filter, verbose_name=_(u'Filtre'), blank=True, null=True)

    class Meta:
        app_label = 'reports'
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
            asc_reports.extend(Report.objects.filter(columns__id=field.id))

        for report in asc_reports:
            asc_reports.extend(report.get_ascendants_reports())

        return set(asc_reports)

    def fetch(self, limit_to=None):
        lines   = []
        ct    = self.ct
        model = ct.model_class()
        model_manager = model.objects
        columns = self.get_children_fields_with_hierarchy()

        if self.filter is not None:
            entities = model_manager.filter(self.filter.get_q())
        else:
            entities = model_manager.all()

        for entity in entities[:limit_to]:
            entity_line = []

            try:
                for column in columns:
                    report, field, children = column.get('report'), column.get('field'), column.get('children')
                    entity_line.append(field.get_value(entity))

                lines.append(entity_line)
            except DropLine:
                pass
            
        return lines

    def fetch_all_lines(self, limit_to=None):
        tree = self.fetch(limit_to=limit_to)

        lines = []

        class ReportTree(object):
            def __init__(self, tree):
                self.tree = tree

                self.has_to_build = False
                self.values_to_build = []

            def process_fk(self):
                new_tree = []
                for col_value in self.tree:
                    if isinstance(col_value, FkClass):
                        new_tree.extend(col_value.values)
                    else:
                        new_tree.append(col_value)
                        
                self.tree = new_tree

            def set_simple_values(self, current_line):
                values = []

                for col_value in self.tree:
                    if not col_value:
                        values.append(u"")
                        
                    elif isinstance(col_value, (list, tuple)):
                        values.append(None)
                        self.has_to_build = True
                        self.values_to_build = col_value
                        
                    else:
                        values.append(col_value)

                if None in current_line:
                    idx = current_line.index(None)
                    values.reverse()
                    for value in values:
                        current_line.insert(idx, value)
                    current_line.remove(None)
                else:
                    current_line.extend(values)

            def set_iter_values(self, lines, current_line):
                for future_node in self.values_to_build:
                    node = ReportTree(future_node)
                    duplicate_line = list(current_line)
                    node.visit(lines, duplicate_line)

            def visit(self, lines, current_line):
                self.process_fk()
                self.set_simple_values(current_line)

                if self.has_to_build:
                    self.set_iter_values(lines, current_line)
                else:
                    lines.append(current_line)

            def get_lines(self):
                lines = []
                self.visit(lines, [])
                return lines

            def __repr__(self):
                return "self.tree : %s" % (self.tree, )

        for node in tree:
            lines.extend(ReportTree(node).get_lines())
            
            if limit_to is not None and len(lines) >= limit_to:#Bof
                break

        return lines

    def get_children_fields_with_hierarchy(self):
        return [c.get_children_fields_with_hierarchy() for c in self.columns.all()]

    def get_children_fields_flat(self):
        children = []
        for c in self.columns.all():
            children.extend(c.get_children_fields_flat())
        return children