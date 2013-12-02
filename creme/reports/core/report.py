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
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import ManyToManyField, ForeignKey, FieldDoesNotExist
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import CremeEntity, RelationType, CustomField
from creme.creme_core.utils.meta import (get_instance_field_info,
        get_model_field_info, get_related_field, get_verbose_field_name)

from ..constants import (RFT_FUNCTION, RFT_RELATION, RFT_FIELD, RFT_CUSTOM,
        RFT_CALCULATED, RFT_RELATED)
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

    class ValueError(Exception):
        pass

    def __init__(self, report_field, title, support_subreport=False):
        self._report_field = report_field
        self._title = title

        #build the 'self._get_value' atribute (see get_value() method)
        if support_subreport:
            if report_field.sub_report:
                get_value = self._get_value_extended_subreport if report_field.selected else \
                            self._get_value_flattened_subreport
            else:
                get_value = self._get_value_no_subreport
        else:
            get_value = self._get_value_single

        self._get_value = get_value

    def _generate_flattened_report(self, entities):
        report = self._report_field.sub_report
        get_verbose_name = partial(get_verbose_field_name, model=report.ct.model_class(), separator="-")

        #TODO: !!!WORK ONLY WITH HFI_FIELD columns !! (& maybe this work is already done by get_value())
        #TODO: view credentials (FK case)
        return u", ".join(" - ".join(u"%s: %s" % (get_verbose_name(field_name=column.name),
                                                  get_instance_field_info(entity, column.name)[1] or u''
                                                 ) for column in report.columns
                                    ) for entity in entities
                         )

    #TODO: user & scope ??
    def _get_related_instances(self, entity, user):
        raise NotImplementedError

    def _get_filtered_related_entities(self, entity, user):
        related_entities = EntityCredentials.filter(user, self._get_related_instances(entity, user))
        report = self._report_field.sub_report

        if report.filter is not None:
            related_entities = report.filter.filter(related_entities)

        return related_entities

    def _get_value_extended_subreport(self, entity, user, scope):
        """Used as _get_value() method by subclasses which manage
        sub-reports (extended sub-report case).
        """
        related_entities = self._get_filtered_related_entities(entity, user)
        gen_values = self._handle_report_values

        #"(None,)" : even if sub-scope if empty, with must generate empty columns for this line
        return [gen_values(e, user, related_entities) for e in related_entities or (None,)]

    def _get_value_flattened_subreport(self, entity, user, scope):
        """Used as _get_value() method by subclasses which manage
        sub-reports (flattened sub-report case).
        """
        return self._generate_flattened_report(self._get_filtered_related_entities(entity, user))

    def _get_value_no_subreport(self, entity, user, scope):
        """Used as _get_value() method by subclasses which manage
        sub-reports (no sub-report case).
        """
        qs = self._get_related_instances(entity, user)
        extract = self._related_model_value_extractor

        if issubclass(qs.model, CremeEntity):
            qs = EntityCredentials.filter(user, qs)

        return u', '.join(unicode(extract(instance)) for instance in qs)

    def _get_value_single(self, entity, user, scope):
        """Used as _get_value() method by subclasses which does not manage
        sub-reports.
        """
        return settings.HIDDEN_VALUE if not user.has_perm_to_view(entity) else \
               self._get_value_single_on_allowed(entity, user, scope)

    def _get_value_single_on_allowed(self, entity, user, scope):
        "Overload this in sub-class when you compute the hand value (entity is viewable)"
        return

    def _handle_report_values(self, entity, user, scope):
        "@param entity CremeEntity instance, or None"
        return [rfield.get_value(entity, user, scope) for rfield in self._report_field.sub_report.columns]

    def _related_model_value_extractor(self, instance):
        return instance

    def get_linkable_ctypes(self):
        """Return the ContentType that are compatique, in order to link a subreport.
        @return A sequence of ContentTypes instances, or None (that means "can not link").
                An empty sequence means "All kind of CremeEntities are linkable"
        """
        return None

    def get_value(self, entity, user, scope):
        """Extract the value from entity for a Report cell.
        @param entity CremeEntity instance.
        @param user User instance ; used to compute credentials.
        @param scope QuerySet where 'entity' it comming from ; used by aggregates.
        """
        value = None

        if entity is None: #eg: a FK column was NULL, or the instance did not pass a filter
            if self._report_field.selected: #selected=True => self._report_field.sub_report is not None
                value = [self._handle_report_values(None, user, scope)]
        else:
            value = self._get_value(entity, user, scope)

        return u'' if value is None else value

    @property
    def title(self):
        return self._title


@REPORT_HANDS_MAP(RFT_FIELD)
class RHRegularField(ReportHand):
    verbose_name = _(u'Regular field')

    def __new__(cls, report_field):
        try:
            field_info = get_model_field_info(report_field.model, report_field.name, silent=False)
        except FieldDoesNotExist:
            raise ReportHand.ValueError('Invalid field: "%s"' % report_field.name)

        if len(field_info) > 1 and isinstance(field_info[1]['field'], (ForeignKey, ManyToManyField)): #TODO: test ForeignKey
            raise ReportHand.ValueError('Invalid field: "%s"' % report_field.name)

        first_part = field_info[0]['field']

        if isinstance(first_part, ForeignKey):
            return ReportHand.__new__(RHForeignKey)

        if isinstance(first_part, ManyToManyField):
            return ReportHand.__new__(RHManyToManyField)

        return super(RHRegularField, cls).__new__(cls)

    def __init__(self, report_field, support_subreport=False):
        super(RHRegularField, self).__init__(report_field,
                                             title=get_verbose_field_name(report_field.model, report_field.name),
                                             support_subreport=support_subreport,
                                            )

    def _get_value_single_on_allowed(self, entity, user, scope):
        model_field, value = get_instance_field_info(entity, self._report_field.name)

        return unicode(value or u'') #Maybe format map (i.e : datetime...)


class RHForeignKey(RHRegularField):
    def __init__(self, report_field):
        super(RHForeignKey, self).__init__(report_field, support_subreport=True)
        field_info = get_model_field_info(report_field.model, report_field.name) #TODO: factorise with __new__
        fk_info = field_info[0]
        self._fk_attr_name = fk_info['field'].get_attname()
        fk_model = fk_info['model']
        self._linked2entity = issubclass(fk_model, CremeEntity)
        qs = fk_model.objects.all()
        sub_report = report_field.sub_report

        if sub_report:
            if sub_report.filter:
                qs = sub_report.filter.filter(qs)
        else:
            #small optimization: only used by _get_value_no_subreport()
            #self._attr_name = field_info[1]['field'].name
            if len(field_info) > 1: #TODO: len() > 2
                attr_name = field_info[1]['field'].name
                self._value_extractor = lambda fk_instance: getattr(fk_instance, attr_name, None)
            else:
                self._value_extractor = unicode

        self._qs = qs

    #NB: cannot rename to _get_related_instances() because fordibben entities are filtered instead of outputting '??'
    def _get_fk_instance(self, entity):
        try:
            entity = self._qs.get(pk=getattr(entity, self._fk_attr_name))
        except ObjectDoesNotExist:
            entity = None

        return entity

    def _get_value_flattened_subreport(self, entity, user, scope):
        fk_entity = self._get_fk_instance(entity)

        if fk_entity is not None: #TODO: test
            return self._generate_flattened_report((fk_entity,)) #TODO: view credentials !!

    def _get_value_extended_subreport(self, entity, user, scope):
        return [self._handle_report_values(self._get_fk_instance(entity), user, scope)]

    def _get_value_no_subreport(self, entity, user, scope):
        fk_instance = self._get_fk_instance(entity)

        if fk_instance is not None:
            if self._linked2entity and not user.has_perm_to_view(fk_instance):
                return settings.HIDDEN_VALUE

            #return getattr(fk_instance, self._attr_name, None)
            return self._value_extractor(fk_instance)

    def get_linkable_ctypes(self):
        return (ContentType.objects.get_for_model(self._qs.model),) if self._linked2entity else None


class RHManyToManyField(RHRegularField):
    def __init__(self, report_field):
        super(RHManyToManyField, self).__init__(report_field, support_subreport=True)
        #self._m2m_attr_name, sep, self._attr_name = report_field.name.partition('__')
        self._m2m_attr_name, sep, attr_name = report_field.name.partition('__')

        #TODO: move "or u''" in base class ??
        self._related_model_value_extractor = (lambda instance: getattr(instance, attr_name, None) or u'') if attr_name else \
                                              unicode

    def _get_related_instances(self, entity, user):
        return getattr(entity, self._m2m_attr_name).all()

    #def _related_model_value_extractor(self, instance):
        #return getattr(instance, self._attr_name, None) or u'' #todo: move "or u''" in base class ??

    def get_linkable_ctypes(self):
        m2m_model = self._report_field.model._meta.get_field(self._m2m_attr_name).rel.to

        return (ContentType.objects.get_for_model(m2m_model),) if issubclass(m2m_model, CremeEntity) else None


@REPORT_HANDS_MAP(RFT_CUSTOM)
class RHCustomField(ReportHand):
    verbose_name = _(u'Custom field')

    def __init__(self, report_field):
        try:
            self._cfield = cf = CustomField.objects.get(id=report_field.name)
        except CustomField.DoesNotExist:
            raise ReportHand.ValueError('Invalid custom field: "%s"' % report_field.name)

        super(RHCustomField, self).__init__(report_field, title=cf.name)

    def _get_value_single_on_allowed(self, entity, user, scope):
        return entity.get_custom_value(self._cfield)


@REPORT_HANDS_MAP(RFT_RELATION)
class RHRelation(ReportHand):
    verbose_name = _(u'Relationship')

    def __init__(self, report_field):
        rtype_id = report_field.name

        try:
            self._rtype = rtype = RelationType.objects.get(id=rtype_id)
        except RelationType.DoesNotExist:
            raise ReportHand.ValueError('Invalid relation type: "%s"' % rtype_id)

        if report_field.sub_report:
            self._related_model = report_field.sub_report.ct.model_class()

        super(RHRelation, self).__init__(report_field, title=unicode(rtype.predicate), support_subreport=True)

    def _get_related_instances(self, entity, user):
        return self._related_model.objects.filter(relations__type=self._rtype.symmetric_type,
                                                  relations__object_entity=entity.id,
                                                 )

    #TODO: add a feature in base class to retrieved efficently real entities ??
    #TODO: extract algorithm that retrieve efficently real entity from CremeEntity.get_related_entities()
    def _get_value_no_subreport(self, entity, user, scope):
        has_perm = user.has_perm_to_view
        return u', '.join(unicode(e) for e in entity.get_related_entities(self._rtype.id, True) if has_perm(e))

    def get_linkable_ctypes(self):
        return self._rtype.object_ctypes.all()


@REPORT_HANDS_MAP(RFT_FUNCTION)
class RHFunctionField(ReportHand):
    verbose_name = _(u'Function field') #TODO: homogenous with HeaderFilter ??

    def __init__(self, report_field):
        funcfield = report_field.model.function_fields.get(report_field.name)
        if not funcfield:
            raise ReportHand.ValueError('Invalid function field: "%s"' % report_field.name)

        self._funcfield = funcfield

        super(RHFunctionField, self).__init__(report_field, title=unicode(funcfield.verbose_name))

    def _get_value_single_on_allowed(self, entity, user, scope):
        return self._funcfield(entity).for_csv()


#TODO: separate RFT_REGULAR_CALCULATED & RFT_CUSTOM_CALCULATED cases
@REPORT_HANDS_MAP(RFT_CALCULATED)
class RHCalculated(ReportHand):
    verbose_name = _(u'Calculated value')

    def __init__(self, report_field):
        #TODO: factorise with form code (_get_calculated_title)
        field_name, sep, aggregation_id = report_field.name.rpartition('__')
        aggregation = field_aggregation_registry.get(aggregation_id)

        if aggregation is None:
            raise ReportHand.ValueError('Invalid aggregation: "%s"' % aggregation_id)

        if field_name.startswith('cf__'): #custom field
            try:
                prefix, cf_type, cf_id = field_name.split('__') #TODO: the type is not useful anymore (datamigration...)
                cfield = CustomField.objects.get(id=cf_id)
            except (ValueError, CustomField.DoesNotExist):
                raise ReportHand.ValueError('Invalid custom field aggregation: "%s"' % field_name)

            if cfield.field_type not in field_aggregation_registry.authorized_customfields:
                raise ReportHand.ValueError('This type of custom field can not be aggregated: "%s"' % field_name)

            self._aggregation_q = aggregation.func('%s__value' % cfield.get_value_class().get_related_name())
            verbose_name = cfield.name
        else: #regular field
            try:
                field = report_field.model._meta.get_field(field_name)
            except FieldDoesNotExist:
                raise ReportHand.ValueError('Unknown field: "%s"' % field_name)

            if not isinstance(field, field_aggregation_registry.authorized_fields):
                raise ReportHand.ValueError('This type of field can not be aggregated: "%s"' % field_name)

            self._aggregation_q = aggregation.func(field_name)
            verbose_name = field.verbose_name

        super(RHCalculated, self).__init__(report_field, title=u'%s - %s' % (aggregation.title, verbose_name))

    def _get_value_single(self, entity, user, scope):
        return scope.aggregate(rh_calculated_agg=self._aggregation_q).get('rh_calculated_agg') or 0


@REPORT_HANDS_MAP(RFT_RELATED)
class RHRelated(ReportHand):
    verbose_name = _(u'Related field')

    def __init__(self, report_field):
        related_field = get_related_field(report_field.model, report_field.name)

        if not related_field:
            raise ReportHand.ValueError('Invalid related field: "%s"' % report_field.name)

        self._related_field = related_field
        self._attr_name = related_field.get_accessor_name()

        super(RHRelated, self).__init__(report_field,
                                        title=unicode(related_field.model._meta.verbose_name),
                                        support_subreport=True,
                                       )

    def _get_related_instances(self, entity, user):
        return getattr(entity, self._attr_name).filter(is_deleted=False)

    def get_linkable_ctypes(self):
        return (ContentType.objects.get_for_model(self._related_field.model),)


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
