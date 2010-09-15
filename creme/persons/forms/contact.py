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

from django.forms import CharField, ModelChoiceField
from django.forms.widgets import TextInput
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, RelationType, Relation
from creme_core.forms import CremeEntityForm, CremeEntityField, CremeDateTimeField
from creme_core.forms.widgets import Label

from media_managers.models import Image
from media_managers.forms.widgets import ImageM2MWidget

from persons.models import Organisation, Contact, Address


#TODO: la gestion des adresses est a revoir ; pourrait on utiliser 2 formulaire
#      sur le model Address dont on insererait le contenu ???

#class ContactCreateForm(CremeEntityForm):
class ContactForm(CremeEntityForm):
    birthday = CremeDateTimeField(label=_('Birthday'), required=False)
    image    = CremeEntityField(label=_('Image'), required=False, model=Image, widget=ImageM2MWidget())

    blocks = CremeEntityForm.blocks.new(
                ('coordinates',      _(u'Coordinates'),      ['skype', 'landline', 'mobile', 'email', 'url_site']),
                ('billing_address',  _(u'Billing address'),  ['name_billing', 'address_billing', 'po_box_billing',
                                                              'city_billing', 'state_billing', 'zipcode_billing', 'country_billing']),
                ('shipping_address', _(u'Shipping address'), ['name_shipping', 'address_shipping', 'po_box_shipping',
                                                              'city_shipping', 'state_shipping', 'zipcode_shipping', 'country_shipping'])
            )

    class Meta:
        model = Contact
        exclude = CremeEntityForm.Meta.exclude + ('billing_adress', 'shipping_adress', 'language', 'is_user')

    def __init__(self, *args, **kwargs):
        super(ContactForm, self).__init__(*args, **kwargs)
        Address.inject_fields(self, '_billing')
        Address.inject_fields(self, '_shipping')

        instance = self.instance
        if not instance is None:
            initial = self.initial

            billing_adress = instance.billing_adress
            if not billing_adress is None :
                initial['name_billing']    = billing_adress.name
                initial['address_billing'] = billing_adress.address
                initial['po_box_billing']  = billing_adress.po_box
                initial['city_billing']    = billing_adress.city
                initial['state_billing']   = billing_adress.state
                initial['zipcode_billing'] = billing_adress.zipcode
                initial['country_billing'] = billing_adress.country

            shipping_adress = instance.shipping_adress
            if not shipping_adress is None :
                initial['name_shipping']    = shipping_adress.name
                initial['address_shipping'] = shipping_adress.address
                initial['po_box_shipping']  = shipping_adress.po_box
                initial['city_shipping']    = shipping_adress.city
                initial['state_shipping']   = shipping_adress.state
                initial['zipcode_shipping'] = shipping_adress.zipcode
                initial['country_shipping'] = shipping_adress.country

    def save(self):
        instance = super(ContactForm, self).save()
        cleaned_data = self.cleaned_data

        billing_adress = instance.billing_adress or Address()

        billing_adress.name    = cleaned_data['name_billing']
        billing_adress.address = cleaned_data['address_billing']
        billing_adress.po_box  = cleaned_data['po_box_billing']
        billing_adress.city    = cleaned_data['city_billing']
        billing_adress.state   = cleaned_data['state_billing']
        billing_adress.zipcode = cleaned_data['zipcode_billing']
        billing_adress.country = cleaned_data['country_billing']

        if instance.billing_adress is not None or \
           any(cleaned_data[key] for key in ('name_billing', 'address_billing', 'po_box_billing',
                                             'city_billing', 'state_billing', 'zipcode_billing', 'country_billing')):
            billing_adress.owner = instance
            billing_adress.save()

        shipping_adress = instance.shipping_adress or Address()

        shipping_adress.name    = cleaned_data['name_shipping']
        shipping_adress.address = cleaned_data['address_shipping']
        shipping_adress.po_box  = cleaned_data['po_box_shipping']
        shipping_adress.city    = cleaned_data['city_shipping']
        shipping_adress.state   = cleaned_data['state_shipping']
        shipping_adress.zipcode = cleaned_data['zipcode_shipping']
        shipping_adress.country = cleaned_data['country_shipping']

        if instance.shipping_adress is not None or \
           any(cleaned_data[key] for key in ('name_shipping', 'address_shipping', 'po_box_shipping',
                                             'city_shipping', 'state_shipping', 'zipcode_shipping', 'country_shipping')):
            shipping_adress.owner = instance
            shipping_adress.save()

        instance.billing_adress = billing_adress
        instance.shipping_adress = shipping_adress
        instance.save() #saved twice because of bidirectionnal pk (TODO: change ??)

        return instance


class ContactWithRelationForm(ContactForm):
    orga_overview = CharField(label=_(u'Concerned organisation'), widget=Label, initial=_('No one'))

    def __init__(self, *args, **kwargs):
        super(ContactWithRelationForm, self).__init__(*args, **kwargs)

        self.linked_orga = self.initial.get('linked_orga')

        if not self.linked_orga:
            return

        self.fields['orga_overview'].initial = self.linked_orga

        self.relation_type = self.initial.get('relation_type')

        if self.relation_type:
            relation_field = CharField(label=ugettext(u'Relation type'),
                                        widget=TextInput(attrs={'readonly': 'readonly'}),
                                        initial=self.relation_type)
        else:
            get_ct = ContentType.objects.get_for_model
            relation_field = ModelChoiceField(label=ugettext(u"Status in the organisation"),
                                              queryset=RelationType.objects.filter(subject_ctypes=get_ct(Contact),
                                                                                   object_ctypes=get_ct(Organisation)))
        self.fields['relation'] = relation_field

    def save(self):
        instance = super(ContactWithRelationForm, self).save()

        if self.linked_orga:
            relation_type = self.relation_type or self.cleaned_data.get('relation')
            Relation.create(instance, relation_type.id, self.linked_orga)

        return instance
