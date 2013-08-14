# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from functools import partial
from itertools import chain
import logging

#from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.db.models.fields.related import ManyToManyField, ForeignKey
from django.db.models.fields import CharField, PositiveIntegerField, PositiveSmallIntegerField, BooleanField
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeModel, CremeEntity, EntityFilter
from creme.creme_core.models.custom_field import CustomField, _TABLES
from creme.creme_core.models.fields import EntityCTypeForeignKey
from creme.creme_core.utils.meta import (get_instance_field_info, get_model_field_info,
                                   filter_entities_on_ct, get_fk_entity, get_m2m_entities, get_related_field, get_verbose_field_name)
from creme.creme_core.models.header_filter import HFI_FUNCTION, HFI_RELATION, HFI_FIELD, HFI_CUSTOM, HFI_CALCULATED, HFI_RELATED

from ..report_aggregation_registry import field_aggregation_registry


logger = logging.getLogger(__name__)


class DropLine(Exception):
    pass

#TODO: unit test
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


class Field(CremeModel):
    name     = CharField(_(u'Name of the column'), max_length=100).set_tags(viewable=False)
    title    = CharField(max_length=100).set_tags(viewable=False)
    order    = PositiveIntegerField().set_tags(viewable=False)
    type     = PositiveSmallIntegerField().set_tags(viewable=False) #==> {HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM, HFI_CALCULATED, HFI_RELATED}#Add in choices ?
    selected = BooleanField(default=False).set_tags(viewable=False) #use this field to expand
    report   = ForeignKey("Report", blank=True, null=True).set_tags(viewable=False) #Sub report

    class Meta:
        app_label = 'reports'
        verbose_name = _(u'Column of report')
        verbose_name_plural = _(u'Columns of report')
        ordering = ('order',)

    def __unicode__(self):
        return self.title

    @staticmethod
    def get_instance_from_hf_item(hf_item):
        """
            @returns : A Field instance (not saved !) built from an HeaderFilterItem instance
        """
        if hf_item.type == HFI_RELATION:
            return Field(name=hf_item.relation_predicat_id, title=hf_item.title, order=hf_item.order, type=hf_item.type)
        else:
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
            @return: A "hierarchical" dict in the format :
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
        field_dict = {'field': self, 'children': [], 'report': None}
        report = self.report

        if report:
            #fields = report.columns.order_by('order')
            fields = report.columns.all()
            field_dict['children'] = [field.get_children_fields_with_hierarchy() for field in fields]
            field_dict['report'] = report

        return field_dict

    #TODO: map of functions instead of if.. elif.. elif ... ???
    def get_value(self, entity=None, selected=None, query=None, user=None):
        column_type = self.type
        column_name = self.name
        report = self.report
        selected = selected or self.selected
        empty_value = u""
        HIDDEN_VALUE = settings.HIDDEN_VALUE
        check_user = user is not None and not user.is_superuser #Don't check for superuser #TODO: user.has_perm_to_view() do not emit query for super user -> bad optimization...

        if column_type == HFI_FIELD:
            #TODO: factorise "entity is None"
            if entity is None and report and selected:
                return FkClass([empty_value for c in report.columns.all()])#Only fk requires a multi-padding
            elif entity is None:
                return empty_value

            fields_through = [f['field'].__class__ for f in get_model_field_info(entity.__class__, column_name)]
            if ManyToManyField in fields_through:
                if report and selected:#The sub report generates new lines
                    res = []

                    #if report.filter is not None:
                        #m2m_entities = get_m2m_entities(entity, self.name, False, report.filter.get_q())
                    #else:
                        #m2m_entities = get_m2m_entities(entity, self.name, False)
                    m2m_entities = get_m2m_entities(entity, self.name, False,
                                                    q_filter=None if report.filter is None else report.filter.get_q() #TODO: get_q() can return doublons: is it a problem ??
                                                   )

                    for m2m_entity in m2m_entities:
                        sub_res = []
                        self._handle_report_values(sub_res, m2m_entity, user=user)
                        res.append(sub_res)

                    if not m2m_entities:
                        self._handle_report_values(res, user=user)
                        res = [res]

                    return res
                else:
                    return get_m2m_entities(entity, self.name, True, user=user)

            elif ForeignKey in fields_through and report and selected:
                fk_entity = get_fk_entity(entity, self.name, user=user)

                if (report.filter is not None and
                    fk_entity not in report.ct.model_class().objects.filter(report.filter.get_q())):
                        raise DropLine

                res = []
                self._handle_report_values(res, fk_entity, user=user)

                return FkClass(res)

            model_field, value = get_instance_field_info(entity, column_name)
#            return unicode(value or empty_value)#Maybe format map (i.e : datetime...)

            if value and check_user:
                return unicode(value) if user.has_perm_to_view(entity) else HIDDEN_VALUE

            return unicode(value or empty_value)

        elif column_type == HFI_CUSTOM:
            value = empty_value

            if entity is not None:
                cf = getattr(self, 'custom_field_cache', None)

                if cf is None: #'None' means CustomField has not been retrieved yet
                    cf = False #'False' means CustomField is unfoundable

                    try:
                        cf = CustomField.objects.get(id=column_name, content_type=entity.entity_type)
                    except ValueError: #TODO: remove when DataMigration is done
                        try:
                            cf = CustomField.objects.filter(name=column_name, content_type=entity.entity_type)[0]
                        except IndexError:
                            pass
                    except CustomField.DoesNotExist:
                        #TODO: remove the Field ??
                        logger.debug('Field.get_value(): CustomField "%s" does not exist any more', column_name)

                    self.custom_field_cache = cf

                if not cf:
                    value = empty_value
                else:
                    value = entity.get_custom_value(cf)

                    if value and check_user and not user.has_perm_to_view(entity):
                        value = HIDDEN_VALUE

            return value

        elif column_type == HFI_RELATION:
            related_entities = entity.get_related_entities(column_name, True) if entity is not None else []

            #TODO: factorise "if report"
            if report and selected:#TODO: Apply self.report filter AND/OR filter_entities_on_ct(related_entities, ct) ?
#                scope = related_entities
                scope = filter_entities_on_ct(related_entities, report.ct)

                if report.filter is not None:
                    #scope = report.ct.model_class().objects.filter(pk__in=[e.id for e in scope])
                    #scope = scope.filter(report.filter.get_q())
                    scope = report.filter.filter(report.ct.model_class().objects.filter(pk__in=[e.id for e in scope]))

                res = []
                for rel_entity in scope:
                    rel_entity_res = []
                    self._handle_report_values(rel_entity_res, rel_entity, user=user)
                    res.append(rel_entity_res)

                if not scope:#We have to keep columns' consistance and pad with blank values
                    self._handle_report_values(res, user=user)
                    res = [res]

                return res

            elif report and not selected:
                scope = filter_entities_on_ct(related_entities, report.ct)
                sub_model = report.ct.model_class()

                if report.filter is not None:
                    scope = report.filter.filter(sub_model.objects.filter(pk__in=[e.id for e in scope]))

                sub_columns = report.columns.all()

                _get_verbose_field_name = partial(get_verbose_field_name, model=sub_model, separator="-")
                no_value = _(u"N/A")

                return u", ".join([" - ".join(u"%s: %s" % (_get_verbose_field_name(field_name=sub_column.name), get_instance_field_info(sub_entity, sub_column.name)[1] or no_value)
                                                            for sub_column in sub_columns
                                             )
                                      for sub_entity in scope
                                  ]) or empty_value

            if selected:
#                return related_entities
                if check_user:
                    return [[related_entity.allowed_unicode(user)] for related_entity in related_entities]
                return [[unicode(related_entity)] for related_entity in related_entities]

            if check_user:
                return u", ".join(related_entity.allowed_unicode(user) for related_entity in related_entities) or empty_value
            return u", ".join(unicode(related_entity) for related_entity in related_entities) or empty_value

        elif column_type == HFI_FUNCTION:
            if check_user and not user.has_perm_to_view(entity):
                return HIDDEN_VALUE

            funfield = entity.function_fields.get(column_name) #TODO: in a cache ??

            return funfield(entity).for_csv() if funfield else "Problem with function field"

        elif column_type == HFI_CALCULATED:
            #No credential check
            field_name, sep, aggregate = column_name.rpartition('__')
            aggregation = field_aggregation_registry.get(aggregate)

            cfs_info = field_name.split('__')

            if aggregation is not None:
                if cfs_info[0] == 'cf':
                    cf_id   = cfs_info[2]
                    cf_type = cfs_info[1]
                    cfs = _TABLES[int(cf_type)].objects.filter(custom_field__id=cf_id, entity__id__in=query.values_list('id', flat=True))
                    return cfs.aggregate(aggregation.func('value')).get('value__%s' % aggregate)
                elif query is not None:
                    return query.aggregate(aggregation.func(field_name)).get(column_name)
                elif entity is not None:
                    return entity.__class__._default_manager.all().aggregate(aggregation.func(field_name)).get(column_name)

        elif column_type == HFI_RELATED:
            if entity is None and report and selected:
                return FkClass([empty_value for c in report.columns.all()])#Only fk requires a multi-padding
            if entity is None:
                return empty_value

            related_field    = get_related_field(entity.__class__, column_name)
            accessor_name    = related_field.get_accessor_name()
            related_entities = getattr(entity, accessor_name).all()

            if report and selected:
                res = []

                for related_entity in related_entities:
                    sub_res = []
                    self._handle_report_values(sub_res, related_entity, user=user)
                    res.append(sub_res)

                if not related_entities:
                    self._handle_report_values(res, user=user)
                    res = [res]

                return res

            if selected:
                if check_user:
                    return [[related_entity.allowed_unicode(user)] for related_entity in related_entities]
                return [[unicode(related_entity)] for related_entity in related_entities]

            if check_user:
                return ', '.join([related_entity.allowed_unicode(user) for related_entity in related_entities])
            return ', '.join([unicode(related_entity) for related_entity in related_entities])

        return empty_value

    #TODO: why not this method return directly a _new_ list ??
    def _handle_report_values(self, container, entity=None, user=None):
        for c in self.report.columns.all():
            sub_val = c.get_value(entity, user=user)
            if isinstance(sub_val, FkClass):
                container.extend(sub_val)
            else:
                container.append(sub_val)


class Report(CremeEntity):
    name    = CharField(_(u'Name of the report'), max_length=100)
    #ct      = ForeignKey(ContentType, verbose_name=_(u"Entity type"))
    ct      = EntityCTypeForeignKey(verbose_name=_(u'Entity type'))
    columns = ManyToManyField(Field, verbose_name=_(u"Displayed columns"), 
                              related_name='report_columns_set', editable=False,
                             ) #TODO: use a One2Many instead....
    filter  = ForeignKey(EntityFilter, verbose_name=_(u'Filter'), blank=True, null=True)

    creation_label = _('Add a report')

    class Meta:
        app_label = 'reports'
        verbose_name = _(u'Report')
        verbose_name_plural = _(u'Reports')
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/reports/report/%s" % self.id

    def get_edit_absolute_url(self):
        return "/reports/report/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/reports/reports"

    def get_ascendants_reports(self):
        fields = Field.objects.filter(report__id=self.id) #TODO: use related name ?
        asc_reports = []

        for field in fields:
            asc_reports.extend(Report.objects.filter(columns__id=field.id))

        for report in asc_reports:
            asc_reports.extend(report.get_ascendants_reports())

        return set(asc_reports)

    def fetch(self, limit_to=None, extra_q=None, user=None):
        lines   = []
        model = self.ct.model_class() #TODO: used once
        #model_manager = model.objects
        columns = self.get_children_fields_with_hierarchy()

        ##if self.filter is not None:
            ##entities = model_manager.filter(self.filter.get_q())
        ##else:
            ##entities = model_manager.all()
        #entities = model_manager.all()
        entities = model.objects.filter(is_deleted=False)

        if self.filter is not None:
            entities = self.filter.filter(entities)

        if extra_q is not None:
            entities = entities.filter(extra_q)

        entities_with_limit = entities[:limit_to]
        #if user is not None:
            #model.populate_credentials(entities_with_limit, user)

        lines_append = lines.append

        for entity in entities_with_limit:
            entity_line = []
            entity_line_append = entity_line.append

            try:
                for column in columns:
                    field = column.get('field')
                    entity_line_append(field.get_value(entity, query=entities, user=user))#TODO: %s/entities/entities_with_limit ?? => Not mysql 5.1 compliant

                lines_append(entity_line)
            except DropLine:
                pass

        return lines

    def fetch_all_lines(self, limit_to=None, extra_q=None, user=None):
        tree = self.fetch(limit_to=limit_to, extra_q=extra_q, user=user)
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
                    idx = none_idx = current_line.index(None)

                    values.reverse()
                    for value in values:
                        current_line.insert(idx, value)
                        none_idx += 1
                    current_line.pop(none_idx)
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
        return chain.from_iterable(c.get_children_fields_flat() for c in self.columns.all())
#        children = []
#
#        for c in self.columns.all():
#            children.extend(c.get_children_fields_flat())
#
#        return children

    def _post_save_clone(self, source):
        for graph in source.reportgraph_set.all():
            new_graph = graph.clone()
            new_graph.report = self
            new_graph.save()

    @staticmethod
    def get_related_fields_choices(model):
        allowed_related_fields = model.allowed_related #TODO: can we just use the regular introspection (+ field tags ?) instead
        related_fields = chain(model._meta.get_all_related_objects(), model._meta.get_all_related_many_to_many_objects())

        return [(related_field.var_name, unicode(related_field.model._meta.verbose_name))
                    for related_field in related_fields
                        if related_field.var_name in allowed_related_fields
               ]
