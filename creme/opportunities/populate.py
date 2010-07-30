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

from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.models import RelationType, BlockConfigItem, ButtonMenuItem, SearchConfigItem, SearchField
from creme_core.utils import create_or_update_models_instance as create
from creme_core.utils.meta import get_verbose_field_name
from creme_core.management.commands.creme_populate import BasePopulator

from creme_config.models import CremeKVConfig

from persons.models import Contact, Organisation

from products.models import Product, Service

from billing.models import SalesOrder, Invoice, Quote

from opportunities.models import SalesPhase, Origin, Opportunity
from opportunities.buttons import linked_opportunity_button
from opportunities.constants import *


class Populator(BasePopulator):
    dependencies = ['creme.core', 'creme.config', 'creme.persons', 'creme.products', 'creme.billing']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_TARGETS_ORGA,      u'cible la société',                [Opportunity]),
                            (REL_OBJ_TARGETS_ORGA,      u"est ciblé par l'opportunité"))
        RelationType.create((REL_SUB_LINKED_PRODUCT,    u"est lié à l'opportunité",         [Product]),
                            (REL_OBJ_LINKED_PRODUCT,    u"concerne le produit",             [Opportunity]))
        RelationType.create((REL_SUB_LINKED_SERVICE,    u"est lié à l'opportunité",         [Service]),
                            (REL_OBJ_LINKED_SERVICE,    u"concerne le service",             [Opportunity]))
        RelationType.create((REL_SUB_LINKED_CONTACT,    u"intervient dans l'opportunité",   [Contact]),
                            (REL_OBJ_LINKED_CONTACT,    u"met en scène",                    [Opportunity]))
        RelationType.create((REL_SUB_LINKED_SALESORDER, u"est associé a l'opportunité",     [SalesOrder]),
                            (REL_OBJ_LINKED_SALESORDER, u"a généré le bon de commande",     [Opportunity]))
        RelationType.create((REL_SUB_LINKED_INVOICE,    u"a été généré pour l'opportunité", [Invoice]),
                            (REL_OBJ_LINKED_INVOICE,    u"a donné lieu à la facture",       [Opportunity]))
        RelationType.create((REL_SUB_LINKED_QUOTE,      u"a été généré pour l'opportunité", [Quote]),
                            (REL_OBJ_LINKED_QUOTE,      u"a donné lieu au devis",           [Opportunity]))
        RelationType.create((REL_SUB_RESPONSIBLE,       u"est chargé de l'affaire",         [Contact]),
                            (REL_OBJ_RESPONSIBLE,       u"a comme responsable d'affaire",   [Opportunity]))
        RelationType.create((REL_SUB_EMIT_ORGA,         u"a généré l'opportunité",          [Organisation]),
                            (REL_OBJ_EMIT_ORGA,         u"a été généré par",                [Opportunity]))


        create(CremeKVConfig, "LINE_IN_OPPORTUNITIES",  value="0")

        create(SalesPhase, 1, name=_(u"À venir"),        description="...")
        create(SalesPhase, 2, name=_(u"Abandonnée"),     description="...")
        create(SalesPhase, 3, name=_(u"Gagnée"),         description="...")
        create(SalesPhase, 4, name=_(u"Perdue"),         description="...")
        create(SalesPhase, 5, name=_(u"En négociation"), description="...")
        create(SalesPhase, 6, name=_(u"En cours"),       description="...")

        create(Origin, 1, name=_(u"Aucun"),            description="...")
        create(Origin, 2, name=_(u"Site Web"),         description="...")
        create(Origin, 3, name=_(u"Bouche à oreille"), description="...")
        create(Origin, 4, name=_(u"Salon"),            description="...")
        create(Origin, 5, name=_(u"Email direct"),     description="...")
        create(Origin, 6, name=_(u"Appel direct"),     description="...")
        create(Origin, 7, name=_(u"Employé"),          description="...")
        create(Origin, 8, name=_(u"Partenaire"),       description="...")
        create(Origin, 9, name=_(u"Autre"),            description="...")

        get_ct = ContentType.objects.get_for_model

        hf_id = create(HeaderFilter, 'opportunities-hf', name=u"Vue d'Opportunité", entity_type_id=get_ct(Opportunity).id, is_custom=False).id
        pref  = 'opportunities-hfi_'
        create(HeaderFilterItem, pref + 'name',    order=1, name='name',            title=u'Nom',            type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'ref',     order=2, name='reference',       title=u'Référence',      type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="reference__icontains")
        create(HeaderFilterItem, pref + 'phase',   order=3, name='sales_phase',     title=u'Phase de vente', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="sales_phase__name__icontains")
        create(HeaderFilterItem, pref + 'expdate', order=4, name='expiration_date', title=u'Échéance',       type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="expiration_date__range")

        create(ButtonMenuItem, 'opportunities-linked_opp_button', content_type_id=get_ct(Organisation).id, button_id=linked_opportunity_button.id_, order=30)

        model = Opportunity
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['name', 'made_sales', 'sales_phase__name', 'origin__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)
