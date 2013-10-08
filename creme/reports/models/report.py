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
from django.contrib.auth.models import User
from django.db.models import (CharField, PositiveIntegerField, 
        PositiveSmallIntegerField, BooleanField, ManyToManyField, ForeignKey)
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import CremeModel, CremeEntity, RelationType, EntityFilter
from creme.creme_core.models.custom_field import CustomField, _TABLES
from creme.creme_core.models.fields import EntityCTypeForeignKey
from creme.creme_core.utils.meta import (get_instance_field_info, get_model_field_info,
        get_fk_entity, get_m2m_entities, get_related_field, get_verbose_field_name) #filter_entities_on_ct #TODO: unused in creme
from creme.creme_core.models.header_filter import (HFI_FUNCTION, HFI_RELATION,
        HFI_FIELD, HFI_CUSTOM, HFI_CALCULATED, HFI_RELATED)

from ..report_aggregation_registry import field_aggregation_registry


logger = logging.getLogger(__name__)


class Field(CremeModel):
    name       = CharField(_(u'Name of the column'), max_length=100).set_tags(viewable=False)
    title      = CharField(max_length=100).set_tags(viewable=False)
    order      = PositiveIntegerField().set_tags(viewable=False)
    type       = PositiveSmallIntegerField().set_tags(viewable=False) #==> {HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM, HFI_CALCULATED, HFI_RELATED}#Add in choices ?
    selected   = BooleanField(default=False).set_tags(viewable=False) #use this field to expand
    sub_report = ForeignKey("Report", blank=True, null=True).set_tags(viewable=False) #Sub report

    class Meta:
        app_label = 'reports'
        verbose_name = _(u'Column of report')
        verbose_name_plural = _(u'Columns of report')
        ordering = ('order',)

    def __unicode__(self):
        return self.title

    #def __repr__(self):
        #return '<Field id=%s name=%s title=%s order=%s type=%s selected=%s report_id=%s>' % (
                    #self.id, self.name, self.title, self.order, self.type, self.selected, self.report_id,
                #)

    def __eq__(self, other):
        return (self.id == other.id and
                self.name == other.name and
                self.title == other.title and
                self.order == other.order and
                self.type == other.type and
                self.selected == other.selected and
                self.sub_report_id == other.sub_report_id)

    #@staticmethod
    #def get_instance_from_hf_item(hf_item):
        #"""
            #@returns : A Field instance built from an HeaderFilterItem instance
        #"""
        #if hf_item.type == HFI_RELATION:
            #return Field(name=hf_item.relation_predicat_id, title=hf_item.title, order=hf_item.order, type=hf_item.type)
        #else:
            #return Field(name=hf_item.name, title=hf_item.title, order=hf_item.order, type=hf_item.type)

    def get_children_fields_flat(self):
        cols = []
        get = self.get_children_fields_with_hierarchy().get
        children = get('children')
        field    = get('field')

        if children and get('report') is not None and field.selected:
            for sub_col in children:
                cols.extend(sub_col['field'].get_children_fields_flat())
        else:
            cols.append(field)

        return cols

    def get_children_fields_with_hierarchy(self):
        """Get a tree that contains the field hierarchy.
        @return: A "hierarchical" dict in the format :
            {'children': [{'children': [], 'field': <Field: Last Name>, 'report': None},
                          {'children': [],
                           'field': <Field: Function - Title>,
                           'report': None},
                          {'children': [{'children': [],
                                         'field': <Field: Civility - ID>,
                                         'report': None},
                                        {'children': [],
                                         'field': <Field: Shipping Address - object id>,
                                         'report': None},
                                        {'children': [],
                                         'field': <Field: Is a user - mot de passe>,
                                         'report': None},
                                        {'children': [],
                                         'field': <Field: cf3>,
                                         'report': None},
                                        {'children': [{'children': [],
                                                       'field': <Field: First name>,
                                                       'report': None},
                                                      {'children': [],
                                                       'field': <Field: is related to / is related to>,
                                                       'report': None}],
                                         'field': <Field: is related to / is related to>,
                                         'report': <Report: Report 4>}],
                           'field': <Field: is related to / is related to>,
                           'report': <Report: Report 3>}],
             'field': <Field: self>,
             'report': <Report: self.report>}
        """
        field_dict = {'field': self, 'children': [], 'report': None} #TODO: true class instead ??
        report = self.sub_report

        if report:
            field_dict['children'] = [field.get_children_fields_with_hierarchy() for field in report.fields]
            field_dict['report'] = report

        return field_dict

    def _get_customfield(self, cf_id):
        cf = getattr(self, 'custom_field_cache', None)

        if cf is None: #'None' means CustomField has not been retrieved yet
            cf = False #'False' means CustomField is unfoundable

            try:
                cf = CustomField.objects.get(id=cf_id)
            except CustomField.DoesNotExist:
                #TODO: remove the Field ??
                logger.debug('CustomField "%s" does not exist any more', cf_id)

            self.custom_field_cache = cf

        return cf

    #TODO: remove if.. elif.. elif ... See ReportGraphHand
    #TODO: 'selected' arg unused ?? (force sub_reported to unselect ?)
    def get_value(self, entity, user, scope, selected=None):
        """Return the value of the cell for this entity.
        @param entity CremeEntity instance, or None.
        @param user User instance, used to check credentials.
        @scope QuerySet of CremeEntities (used to make correct aggregate).
        @return An unicode or a list (that correspond to an expanded column).
        """
        column_type = self.type
        column_name = self.name
        report = self.sub_report
        selected = selected or self.selected
        empty_value = u""

        if entity is None:
            if report and selected:
                return [self._handle_report_values(None, user, scope)]

        elif column_type == HFI_FIELD:
            #TODO; this job is also done by 'get_fk_entity()' (which is only use here) => a refactoring would be cool
            fields_through = [f['field'].__class__ for f in get_model_field_info(entity.__class__, column_name)]

            if ManyToManyField in fields_through: #TODO: factorise with HFI_RELATION
                if report:
                    m2m_entities = get_m2m_entities(entity, column_name, False,
                                                    q_filter=None if report.filter is None else report.filter.get_q() #TODO: get_q() can return doublons: is it a problem ??
                                                   )
                    m2m_entities = EntityCredentials.filter(user, m2m_entities) #TODO: test

                    if selected: #The sub report generates new lines
                        gen_values = self._handle_report_values
                        return [gen_values(e, user, m2m_entities) for e in m2m_entities or (None,)]
                    else:
                        get_verbose_name = partial(get_verbose_field_name, model=report.ct.model_class(), separator="-")

                        return u", ".join(" - ".join(u"%s: %s" % (get_verbose_name(field_name=sub_column.name),
                                                                  get_instance_field_info(sub_entity, sub_column.name)[1] or empty_value #no_value
                                                                 ) for sub_column in report.fields
                                                    ) for sub_entity in m2m_entities
                                         ) or empty_value

                return get_m2m_entities(entity, column_name, True, user=user)

            elif ForeignKey in fields_through: #TODO: factorise with HFI_RELATION ???
                if report:
                    fk_entity = get_fk_entity(entity, column_name, user=user)

                    if report.filter is not None and \
                       not report.ct.model_class().objects.filter(pk=fk_entity.id).filter(report.filter.get_q()).exists(): #TODO: cache (part of queryset)
                        fk_entity = None

                    if selected:
                        return [self._handle_report_values(fk_entity, user, scope)]
                    else:
                        if fk_entity is None: #TODO: test
                            return empty_value

                        return " - ".join(u"%s: %s" % (get_verbose_field_name(field_name=sub_column.name, model=report.ct.model_class(), separator="-"),
                                                       get_instance_field_info(fk_entity, sub_column.name)[1] or empty_value #no_value
                                                      ) for sub_column in report.fields
                                         )

                return unicode(get_fk_entity(entity, column_name, user=user, get_value=True) or empty_value)

            if not user.has_perm_to_view(entity):
                value = settings.HIDDEN_VALUE
            else:
                model_field, value = get_instance_field_info(entity, column_name)
                value = unicode(value or empty_value) #Maybe format map (i.e : datetime...)

            return value

        elif column_type == HFI_CUSTOM:
            cf = self._get_customfield(column_name)

            if cf:
                return entity.get_custom_value(cf) if user.has_perm_to_view(entity) else settings.HIDDEN_VALUE

        elif column_type == HFI_RELATION:
            rtype = getattr(self, 'rtype_cache', None)

            if rtype is None: #'None' means RelationType has not been retrieved yet
                rtype = False #'False' means RelationType is unfoundable

                try:
                    rtype = RelationType.objects.get(symmetric_type=column_name)
                except RelationType.DoesNotExist: #TODO: test
                    #TODO: remove the Field ?? Notify the user
                    logger.warn('Field.get_value(): RelationType "%s" does not exist any more', column_name)

                self.rtype_cache = rtype

            if report:
                sub_model = report.ct.model_class()
                related_entities = EntityCredentials.filter(user, sub_model.objects.filter(relations__type=rtype,
                                                                                           relations__object_entity=entity.id,
                                                                                          )
                                                           )

                if report.filter is not None:
                    related_entities = report.filter.filter(related_entities)

                if selected:
                    gen_values = self._handle_report_values
                    #if sub-scope if empty, with must generate empty columns for this line
                    return [gen_values(e, user, related_entities) for e in related_entities or (None,)]
                else:
                    get_verbose_name = partial(get_verbose_field_name, model=sub_model, separator="-")
                    #no_value = _(u"N/A") TODO: ??

                    #TODO: !!!WORK ONLY WITH HFI_FIELD columns !! (& maybe this work is already done by get_value())
                    return u", ".join(" - ".join(u"%s: %s" % (get_verbose_name(field_name=sub_column.name),
                                                              get_instance_field_info(sub_entity, sub_column.name)[1] or empty_value #no_value
                                                             ) for sub_column in report.fields
                                                ) for sub_entity in related_entities
                                     ) or empty_value

            if rtype:
                #TODO: filter queryset instead ??
                has_perm = user.has_perm_to_view

                return u', '.join(unicode(e) for e in entity.get_related_entities(column_name, True) if has_perm(e)) or empty_value

        elif column_type == HFI_FUNCTION:
            if not user.has_perm_to_view(entity):
                return settings.HIDDEN_VALUE

            funfield = entity.function_fields.get(column_name) #TODO: in a cache ??

            #TODO: delete column when funfield is invalid ??
            return funfield(entity).for_csv() if funfield else ugettext("Problem with function field")

        elif column_type == HFI_CALCULATED:
            #TODO: factorise with form code (_get_calculated_title)
            field_name, sep, aggregate = column_name.rpartition('__')
            aggregation = field_aggregation_registry.get(aggregate)

            if aggregation is not None: #TODO: notify that an error happened ??
                #TODO: cache result
                if field_name.startswith('cf__'):
                    prefix, cf_type, cf_id = field_name.split('__') #TODO: the type is not useful anymore (datamigration...)
                    cfield = self._get_customfield(cf_id)

                    if cfield:
                        return scope.aggregate(custom_agg=aggregation.func('%s__value' % cfield.get_value_class().get_related_name())) \
                                    .get('custom_agg') or 0
                else: #regular field
                    return scope.aggregate(aggregation.func(field_name)).get(column_name) or 0

        elif column_type == HFI_RELATED: #TODO: factorise with HFI_RELATION
            related_entities = EntityCredentials.filter(
                                    user,
                                    getattr(entity, get_related_field(entity.__class__, column_name).get_accessor_name())
                                            .filter(is_deleted=False)
                                )

            if report:
                if report.filter is not None: #TODO: test
                    related_entities = report.filter.filter(related_entities)

                if selected:
                    gen_values = self._handle_report_values
                    return [gen_values(e, user, related_entities) for e in related_entities or (None,)]
                else:
                    get_verbose_name = partial(get_verbose_field_name, model=related_entities.model, separator="-")

                    return u", ".join(" - ".join(u"%s: %s" % (get_verbose_name(field_name=sub_column.name),
                                                              get_instance_field_info(sub_entity, sub_column.name)[1] or empty_value
                                                             ) for sub_column in report.fields
                                                ) for sub_entity in related_entities
                                     ) or empty_value

            return u', '.join(unicode(e) for e in related_entities)

        return empty_value

    def _handle_report_values(self, entity, user, scope):
        "@param entity CremeEntity instance, or None"
        return [rfield.get_value(entity, user, scope) for rfield in self.sub_report.fields]


class Report(CremeEntity):
    name    = CharField(_(u'Name of the report'), max_length=100)
    #ct      = ForeignKey(ContentType, verbose_name=_(u"Entity type"))
    ct      = EntityCTypeForeignKey(verbose_name=_(u'Entity type'))
    columns = ManyToManyField(Field, verbose_name=_(u"Displayed columns"), 
                              related_name='report_columns_set', editable=False,
                             ) #TODO: use a One2Many instead....
    filter  = ForeignKey(EntityFilter, verbose_name=_(u'Filter'), blank=True, null=True)

    creation_label = _('Add a report')
    _report_fields_cache = None

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

    @property
    def fields(self):
        fields = self._report_fields_cache

        if fields is None:
            self._report_fields_cache = fields = self.columns.all()

        return fields

    def get_ascendants_reports(self):
        fields = Field.objects.filter(sub_report=self.id)
        asc_reports = []

        for field in fields:
            asc_reports.extend(Report.objects.filter(columns__id=field.id))

        for report in asc_reports:
            asc_reports.extend(report.get_ascendants_reports())

        return set(asc_reports)

    def _fetch(self, limit_to=None, extra_q=None, user=None):
        user = user or User(is_superuser=True)
        entities = EntityCredentials.filter(user, self.ct.model_class().objects.filter(is_deleted=False))

        if self.filter is not None:
            entities = self.filter.filter(entities)

        if extra_q is not None:
            entities = entities.filter(extra_q)

        columns = self.get_children_fields_with_hierarchy()

        return ([column.get('field').get_value(entity, scope=entities, user=user)
                    for column in columns
                ] for entity in entities[:limit_to]
               )

    #TODO: transform into generator (--> StreamResponse)
    def fetch_all_lines(self, limit_to=None, extra_q=None, user=None):
        class ReportTree(object):
            def __init__(self, tree):
                self.tree = tree

            def _visit(self, lines, current_line):
                values = []
                values_to_build = None

                for col_value in self.tree:
                    if isinstance(col_value, list):
                        values.append(None)
                        values_to_build = col_value
                    else:
                        values.append(col_value)

                if None in current_line:
                    idx = current_line.index(None)
                    current_line[idx:idx + 1] = values
                else:
                    current_line.extend(values)

                if values_to_build is not None:
                    for future_node in values_to_build:
                        ReportTree(future_node)._visit(lines, list(current_line))
                else:
                    lines.append(current_line)

            def get_lines(self):
                lines = []
                self._visit(lines, [])
                return lines

            def __repr__(self):
                return "self.tree : %s" % (self.tree, )


        lines = []

        for node in self._fetch(limit_to=limit_to, extra_q=extra_q, user=user):
            lines.extend(ReportTree(node).get_lines())

            if limit_to is not None and len(lines) >= limit_to:#Bof
                break #TODO: test

        return lines

    def get_children_fields_with_hierarchy(self):
        return [f.get_children_fields_with_hierarchy() for f in self.fields]

    def get_children_fields_flat(self):
        return chain.from_iterable(f.get_children_fields_flat() for f in self.fields)

    def _post_save_clone(self, source): #TODO: test
        for graph in source.reportgraph_set.all():
            new_graph = graph.clone()
            new_graph.report = self
            new_graph.save()

    #TODO: add a similar HeaderFilterItem type in creme_core (& so move this code in core)
    @staticmethod
    def get_related_fields_choices(model):
        allowed_related_fields = model.allowed_related #TODO: can we just use the regular introspection (+ field tags ?) instead
        meta = model._meta
        related_fields = chain(meta.get_all_related_objects(),
                               meta.get_all_related_many_to_many_objects()
                              )

        return [(related_field.var_name, unicode(related_field.model._meta.verbose_name))
                    for related_field in related_fields
                        if related_field.var_name in allowed_related_fields
               ]
