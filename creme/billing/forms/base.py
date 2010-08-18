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

from django.forms import Form
from django.forms import DateField, CharField
from django.forms.widgets import Select
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import Relation
from creme_core.forms import CremeEntityForm, CremeEntityField, CremeDateField
from creme_core.forms.widgets import ListViewWidget

from persons.models.organisation import Organisation
from persons.forms.address import clean_address

from billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED


class BaseEditForm(CremeEntityForm):
    source = CremeEntityField(label=_(u"Organisation émettrice"),  model=Organisation, widget=ListViewWidget(attrs={'id':'id_source'}))
    target = CremeEntityField(label=_(u"Organisation réceptrice"), model=Organisation, widget=ListViewWidget(attrs={'id':'id_target'}))

    issuing_date    = CremeDateField(label=_(u"Date d'émission"))
    expiration_date = CremeDateField(label=_(u"Échéance"))

    billing_address  = CharField(label=_(u"Adresse de facturation"), help_text=_("Choisissez une organisation pour avoir son adresse de facturation"), widget=Select(attrs={'id':'id_billing_address'}))
    shipping_address = CharField(label=_(u"Adresse de livraison"),   help_text=_("Choisissez une organisation pour avoir son adresse de livraison"),   widget=Select(attrs={'id':'id_shipping_address'}))

    blocks = CremeEntityForm.blocks.new(
                ('orga_n_address', _(u'Société et adresses'), ['source', 'target', 'billing_address', 'shipping_address']),
            )

    def __init__(self, *args, **kwargs):
        super(BaseEditForm, self).__init__(*args, **kwargs)

        fields = self.fields
        instance = self.instance
        pk = instance.pk
        billing_addr  = fields['billing_address']
        shipping_addr = fields['shipping_address']

        if pk is not None: #edit mode
            get_relation = Relation.objects.get
            fields['source'].initial = get_relation(subject_entity__id=pk, type__id=REL_SUB_BILL_ISSUED).object_entity_id #value_list(object_entity_id) ???
            fields['target'].initial = get_relation(subject_entity__id=pk, type__id=REL_SUB_BILL_RECEIVED).object_entity_id

            #TODO: move this JS in widgets ???
            if instance.billing_address:
                billing_addr.initial  = instance.billing_address.id
            if instance.shipping_address:
                shipping_addr.initial = instance.shipping_address.id

        billing_addr.widget.attrs['onchange']  = "creme.utils.changeOtherNodes(%s,%s,%s);" % ("$(this).attr('id')","{'model':'Address','template':'persons/view_address.html'}",'creme.utils.renderEntity')
        shipping_addr.widget.attrs['onchange'] = "creme.utils.changeOtherNodes(%s,%s,%s);" % ("$(this).attr('id')","{'model':'Address','template':'persons/view_address.html'}",'creme.utils.renderEntity')

        organisation_ct_id = ContentType.objects.get_for_model(Organisation).id

        fields['target'].widget.attrs['onchange'] = \
            "creme.utils.changeOtherNodes(%s, %s, %s);" % \
                ("$(this).attr('id')",
                 "[{'id':'id_billing_address', 'ct_id':'%s', 'verbose_field': 'name', 'current': '%s'}, {'id':'id_shipping_address', 'ct_id':'%s','verbose_field':'name', 'current':'%s'}]" % (organisation_ct_id, billing_addr.initial, organisation_ct_id, shipping_addr.initial),
                 'creme.persons.retrieveAddress')

    def clean_billing_address(self):
        return clean_address(self.cleaned_data['billing_address'])

    def clean_shipping_address(self):
        return clean_address(self.cleaned_data['shipping_address'])

    def save(self):
        instance = super(BaseEditForm, self).save()

        cleaned_data  = self.cleaned_data
        create_relation = Relation.create

        Relation.objects.filter(subject_entity=instance, type__in=(REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED)).delete()
        create_relation(instance, REL_SUB_BILL_ISSUED,   cleaned_data['source'])
        create_relation(instance, REL_SUB_BILL_RECEIVED, cleaned_data['target'])

        return instance


class BaseCreateForm(BaseEditForm):
    def __init__(self, *args, **kwargs):
        super(BaseCreateForm, self).__init__(*args, **kwargs)

        try:
            self.fields['source'].initial = Organisation.get_all_managed_by_creme().values_list('id', flat=True)[0] #[:1][0] ??
        except IndexError, e:
            debug('Exception in %s.__init__: %s', self.__class__, e)

    def save(self):
        instance = super(BaseCreateForm, self).save()

        instance.generate_number()
        instance.save()
