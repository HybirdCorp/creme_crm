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

from logging import debug

from django.db.models import Model, CharField, ForeignKey, ManyToManyField, PositiveIntegerField
from django.db.models.aggregates import Avg, Max, Min, Sum
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_str
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, Filter, CremeModel


class AggregateFuncRegistry(object):
    def __init__(self):
        self._aggregate_func = {}

    def register_aggregate_func(self, name, func):
        self._aggregate_func[name] = func

    def get_aggregate_func(self, name):
        #if self._aggregate_func.has_key(name):
            #return self._aggregate_func[name]
        #else :
            #raise NotRegistered("There no registered function with this key :%s" % name)
        return self._aggregate_func[name]

_func_registry = AggregateFuncRegistry()
_func_registry.register_aggregate_func('Sum', Sum)
_func_registry.register_aggregate_func('Min', Min)
_func_registry.register_aggregate_func('Max', Max)
_func_registry.register_aggregate_func('Avg', Avg)


class Type(CremeModel):
    name = CharField(_(u'Type'), max_length=100, blank=False, null=False)

    class Meta:
        app_label = 'reports'


class Field(CremeModel):
    name = CharField(_(u'Nom du champ'), max_length=100, blank=False, null=False)
    ct   = ForeignKey(ContentType, verbose_name=_(u'Ressource'))

    class Meta:
        app_label = 'reports'


class Operation(CremeModel):
    name             = CharField(_(u"Nom de l'opération"), max_length=100, blank=False, null=False)
    operator         = CharField(_(u'Opérateur'), max_length=100, blank=False, null=False)
    operator_pattern = CharField(_(u'Opérateur pattern'), max_length=100, blank=False, null=False)
    # A terme on pourra choisir quels types de donnees doit etre utiliser pour une operation
    accepted_types   = ManyToManyField(Type, related_name="type_set")

    class Meta:
        app_label = 'reports'


class Report(CremeEntity):
    name   = CharField(_(u'Nom du rapport'), max_length=100, blank=False, null=False)
    ct     = ForeignKey(ContentType, verbose_name=_(u'Ressource'))
    fields = ManyToManyField(Field, through='Mtm_rp_fl')
    filter = ForeignKey(Filter, verbose_name=_(u'Filtre'), blank=True, null=True)

    class Meta:
        app_label = 'reports'
        verbose_name = _(u'Rapport')
        verbose_name_plural  = _(u'Rapports')

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/reports/report/%s" % self.id

    def get_edit_absolute_url(self):
        return "/reports/report/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/reports/reports"

    def get_delete_absolute_url(self):
        return "/reports/report/delete/%s" % self.id

    def get_entity_actions(self):
        return super(Report, self).get_entity_actions() + \
                u""" | <a href="/reports/report/%(id)s/csv">Télécharger CSV</a>
                     | <a href="/reports/report/%(id)s/odt">Télécharger ODT</a>""" % {'id': self.id}

    def getFields(self):
        #TODO: use QuerySet.value_list() instead of list comprehension ??????
        return [item.field for item in Mtm_rp_fl.objects.filter(report=self).order_by("order")]

    def addField(self, field, odr):
        Mtm_rp_fl.objects.create(report=self, field=field, order=odr)

    def delField(self, field):
        Mtm_rp_fl.objects.get(report=self, field=field).delete()

    def getFieldsOperations(self):
        return FieldsOperations.objects.filter(report=self)

    def generateCSV(self):
        import csv
        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename="rapport.csv"'

        writer = csv.writer(response, delimiter=";")

        tab_fields = [field.name for field in self.getFields()]

        writer.writerow([self.name])
        writer.writerow(tab_fields)

        model_class = self.ct.model_class()

        if self.filter:
            entities = model_class.objects.filter(self.filter.get_q())
        else:
            entities = model_class.objects.all()

        #TODO: use QuerySet.value_list() instead ??????
        for item in entities:
            line = []
            for field in tab_fields:
                line.append(smart_str(getattr(item, field)))
            writer.writerow(line)

        for foperation in FieldsOperations.objects.filter(report=self):
            try:
                func = _func_registry.get_aggregate_func(foperation.operation.operator)
                field_name = foperation.field.name
                writer.writerow(['%s %s' % (foperation.operation.name,field_name), model_class.objects.aggregate(func(field_name))[foperation.operation.operator_pattern % field_name]])
            except KeyError: #NotRegistered, 
                continue

        debug(response)

        return response

    def generateODT(self):
        from relatorio.templates.opendocument import Template
        from relatorio.templates.pdf import Template as PdfTemplate
        import settings
        #http://framework.openoffice.org/documentation/mimetypes/mimetypes.html
        model_class = self.ct.model_class()
        if self.filter:
            self.entities = model_class.objects.filter(self.filter.get_q())
        else:
            self.entities = model_class.objects.all()

        self.operations = []
        for foperation in FieldsOperations.objects.filter(report=self):
            try:
                func = _func_registry.get_aggregate_func(foperation.operation.operator)
                field_name = foperation.field.name
                self.operations.append({
                        'name':   '%s %s' % (foperation.operation.name, field_name),
                        'value' : model_class.objects.aggregate(func(field_name))[foperation.operation.operator_pattern % field_name]
                    })
            #except (NotRegistered, KeyError), e:
            except KeyError, e:
                debug('Exception in Report.generateODT(): %s', e)

        #debug('FieldsOperations.objects.filter(report=self) : %s', FieldsOperations.objects.filter(report=self))
        debug('self.operations : %s', self.operations)

        basic = Template(source=None, filepath=settings.MANDATORY_TEMPLATE + 'reports/templates/report.odt')
        basic_generated = basic.generate(o=self).render()
        response = HttpResponse(basic_generated.getvalue(), mimetype='application/vnd.oasis.opendocument.text')
#        response = HttpResponse(basic_generated.getvalue(), mimetype='application/pdf')
#        response['Content-Disposition'] = 'attachment; filename=\"%s.pdf\"' % self.name.replace(' ','')
        response['Content-Disposition'] = 'attachment; filename="%s.odt"' % self.name.replace(' ','')
        return response


class Mtm_rp_fl(Model):
    report = ForeignKey(Report)
    field  = ForeignKey(Field)
    order  = PositiveIntegerField(blank=True, null=True)

    class Meta:
        app_label = 'reports'


class FieldsOperations(CremeModel):
    report    = ForeignKey(Report, verbose_name=_(u'Rapport'))
    field     = ForeignKey(Field, verbose_name=_(u'Field'))
    operation = ForeignKey(Operation, verbose_name=_(u'Operation'))

    class Meta:
        app_label = 'reports'
