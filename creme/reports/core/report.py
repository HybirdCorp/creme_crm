# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013  Hybird
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
import logging

from django.conf import settings
from django.db.models import ManyToManyField, ForeignKey
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import RelationType, CustomField
from creme.creme_core.utils.meta import (get_instance_field_info, get_model_field_info,
        get_fk_entity, get_m2m_entities, get_related_field, get_verbose_field_name)
from creme.creme_core.models.header_filter import (HFI_FUNCTION, HFI_RELATION,
        HFI_FIELD, HFI_CUSTOM, HFI_CALCULATED, HFI_RELATED)

from ..report_aggregation_registry import field_aggregation_registry


logger = logging.getLogger(__name__)


class ReportHandRegistry(object):
    __slots__ = ('_hands', )

    def __init__(self):
        self._hands = {}

    def __call__(self, hand_id):
        assert hand_id not in self._hands, 'ID collision'

        def _aux(cls):
            self._hands[hand_id] = cls
            cls.hand_id = hand_id
            return cls

        return _aux

    def __getitem__(self, i):
        return self._hands[i]

    def __iter__(self):
        return iter(self._hands)

    def get(self, i):
        return self._hands.get(i)


REPORT_HANDS_MAP = ReportHandRegistry()


class ReportHand(object):
    "Class that computes values of a report column"
    verbose_name = 'OVERLOADME'

    def __init__(self, report_field):
        self._report_field = report_field

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

    def _handle_report_values(self, entity, user, scope):
        "@param entity CremeEntity instance, or None"
        return [rfield.get_value(entity, user, scope) for rfield in self._report_field.sub_report.fields]

    def _get_value(self, entity, user, scope):
        raise NotImplementedError

    def get_value(self, entity, user, scope):
        value = None

        if entity is None :
            if self._report_field.selected: #selected=True => self._report_field.sub_report is not None
                value = [self._handle_report_values(None, user, scope)]
        else:
            value = self._get_value(entity, user, scope)

        return u'' if value is None else value 


#TODO: split for M2M etc... (__new__ ??)
@REPORT_HANDS_MAP(HFI_FIELD)
class RHRegularField(ReportHand):
    verbose_name = _(u'Regular field')

    def _get_value(self, entity, user, scope):
        column_name = self._report_field.name
        report = self._report_field.sub_report

        #TODO; this job is also done by 'get_fk_entity()' (which is only use here) => a refactoring would be cool
        fields_through = [f['field'].__class__ for f in get_model_field_info(entity.__class__, column_name)]

        if ManyToManyField in fields_through: #TODO: factorise with RHRelation
            if report:
                m2m_entities = get_m2m_entities(entity, column_name, False,
                                                q_filter=None if report.filter is None else report.filter.get_q() #TODO: get_q() can return doublons: is it a problem ??
                                               )
                m2m_entities = EntityCredentials.filter(user, m2m_entities) #TODO: test

                if self._report_field.selected: #The sub report generates new lines
                    gen_values = self._handle_report_values
                    return [gen_values(e, user, m2m_entities) for e in m2m_entities or (None,)]
                else:
                    get_verbose_name = partial(get_verbose_field_name, model=report.ct.model_class(), separator="-")

                    return u", ".join(" - ".join(u"%s: %s" % (get_verbose_name(field_name=sub_column.name),
                                                                get_instance_field_info(sub_entity, sub_column.name)[1] or u'' #empty_value
                                                                ) for sub_column in report.fields
                                                ) for sub_entity in m2m_entities
                                        ) #or empty_value

            return get_m2m_entities(entity, column_name, True, user=user)

        elif ForeignKey in fields_through: #TODO: factorise with RHRelation
            if report:
                fk_entity = get_fk_entity(entity, column_name, user=user)

                if report.filter is not None and \
                    not report.ct.model_class().objects.filter(pk=fk_entity.id).filter(report.filter.get_q()).exists(): #TODO: cache (part of queryset)
                    fk_entity = None

                if self._report_field.selected:
                    return [self._handle_report_values(fk_entity, user, scope)]
                else:
                    if fk_entity is None: #TODO: test
                        #return empty_value
                        return

                    return " - ".join(u"%s: %s" % (get_verbose_field_name(field_name=sub_column.name, model=report.ct.model_class(), separator="-"),
                                                   get_instance_field_info(fk_entity, sub_column.name)[1] or u'' #empty_value
                                                  ) for sub_column in report.fields
                                        )

            return unicode(get_fk_entity(entity, column_name, user=user, get_value=True) or u'') #empty_value

        if not user.has_perm_to_view(entity):
            value = settings.HIDDEN_VALUE
        else:
            model_field, value = get_instance_field_info(entity, column_name)
            value = unicode(value or u'') #Maybe format map (i.e : datetime...)

        return value


@REPORT_HANDS_MAP(HFI_CUSTOM)
class RHCustomField(ReportHand):
    verbose_name = _(u'Custom field')

    def _get_value(self, entity, user, scope):
        cf = self._get_customfield(self._report_field.name)

        if cf:
            return entity.get_custom_value(cf) if user.has_perm_to_view(entity) else settings.HIDDEN_VALUE


@REPORT_HANDS_MAP(HFI_RELATION)
class RHRelation(ReportHand):
    verbose_name = _(u'Relationship')

    def _get_value(self, entity, user, scope):
        column_name = self._report_field.name
        report = self._report_field.sub_report

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

            if self._report_field.selected:
                gen_values = self._handle_report_values
                #if sub-scope if empty, with must generate empty columns for this line
                return [gen_values(e, user, related_entities) for e in related_entities or (None,)]
            else:
                get_verbose_name = partial(get_verbose_field_name, model=sub_model, separator="-")

                #TODO: !!!WORK ONLY WITH HFI_FIELD columns !! (& maybe this work is already done by get_value())
                return u", ".join(" - ".join(u"%s: %s" % (get_verbose_name(field_name=sub_column.name),
                                                          get_instance_field_info(sub_entity, sub_column.name)[1] or u''
                                                         ) for sub_column in report.fields
                                            ) for sub_entity in related_entities
                                 )

        if rtype:
            #TODO: filter queryset instead ??
            has_perm = user.has_perm_to_view

            return u', '.join(unicode(e) for e in entity.get_related_entities(column_name, True) if has_perm(e)) #or empty_value


@REPORT_HANDS_MAP(HFI_FUNCTION)
class RHFunctionField(ReportHand):
    verbose_name = _(u'Function field') #TODO: homogenous with HeaderFilter ??

    def _get_value(self, entity, user, scope):
        if not user.has_perm_to_view(entity):
            return settings.HIDDEN_VALUE

        funfield = entity.function_fields.get(self._report_field.name) #TODO: in a cache ??

        #TODO: delete column when funfield is invalid ??
        return funfield(entity).for_csv() if funfield else ugettext("Problem with function field")


@REPORT_HANDS_MAP(HFI_CALCULATED)
class RHCalculated(ReportHand):
    verbose_name = _(u'Calculated value')

    def _get_value(self, entity, user, scope):
        column_name = self._report_field.name

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


@REPORT_HANDS_MAP(HFI_RELATED)
class RHRelated(ReportHand):
    verbose_name = _(u'Related field')

    def _get_value(self, entity, user, scope): #TODO: factorise with RHRelation
        report = self._report_field.sub_report
        related_entities = EntityCredentials.filter(
                                user,
                                getattr(entity, get_related_field(entity.__class__, self._report_field.name).get_accessor_name())
                                        .filter(is_deleted=False)
                            )

        if report:
            if report.filter is not None: #TODO: test
                related_entities = report.filter.filter(related_entities)

            if self._report_field.selected:
                gen_values = self._handle_report_values
                return [gen_values(e, user, related_entities) for e in related_entities or (None,)]
            else:
                get_verbose_name = partial(get_verbose_field_name, model=related_entities.model, separator="-")

                return u", ".join(" - ".join(u"%s: %s" % (get_verbose_name(field_name=sub_column.name),
                                                          get_instance_field_info(sub_entity, sub_column.name)[1] or u''
                                                         ) for sub_column in report.fields
                                            ) for sub_entity in related_entities
                                 )

        return u', '.join(unicode(e) for e in related_entities)


class ExpandableLine(object):
    """Store a line of report values that can be expanded in several lines if
    there are selected sub-reports.
    """
    def __init__(self, values):
        self._cvalues = values

    def _visit(self, lines, current_line):
        values = []
        values_to_build = None

        for col_value in self._cvalues:
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
                ExpandableLine(future_node)._visit(lines, list(current_line))
        else:
            lines.append(current_line)

    def get_lines(self):
        lines = []
        self._visit(lines, [])

        return lines
