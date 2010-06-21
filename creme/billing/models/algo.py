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


from django.db.models import Model, CharField, ForeignKey, IntegerField
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeModel, CremeProperty
from creme_core.constants import PROP_IS_MANAGED_BY_CREME

from persons.models import Organisation


class ConfigBillingAlgo(CremeModel):
    organisation = ForeignKey (Organisation, verbose_name=_(u'Société'))
    name_algo    = CharField(_(u'Nom de l"algo'), max_length=400)
    ct           = ForeignKey(ContentType)

    class Meta:
        app_label = 'billing'


class SimpleBillingAlgo (Model):
    organisation = ForeignKey (Organisation, verbose_name=_(u'Société'))
    last_number  = IntegerField ()
    prefix       = CharField(_(u'Prefixe de la facture'), max_length=400)
    ct           = ForeignKey(ContentType)

    class Meta:
        app_label = 'billing'



def simple_conf_billing_for_org_managed_by_creme(sender, instance, created, **kwargs):
    if not created:
        return

    from quote import Quote
    from sales_order import SalesOrder
    from invoice import Invoice

    get_ct = ContentType.objects.get_for_model

    if instance.type_id == PROP_IS_MANAGED_BY_CREME and instance.creme_entity.entity_type == get_ct(Organisation):
        org = instance.creme_entity.get_real_entity()

        if not ConfigBillingAlgo.objects.filter(organisation=org):
            for model, prefix in [(Quote, "DE"), (Invoice, "FA"), (SalesOrder, "BC")]: #TODO: prefixes in config....
                ct = get_ct(model)
                ConfigBillingAlgo(organisation=org, name_algo="SIMPLE_ALGO", ct=ct).save() #TODO: SIMPLE_ALGO -> SimpleBillingAlgo attr ??
                SimpleBillingAlgo(organisation=org, last_number=0, prefix=prefix, ct=ct).save()


post_save.connect(simple_conf_billing_for_org_managed_by_creme, sender=CremeProperty)
