# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

#from logging import debug

from django.forms import CharField, ModelChoiceField
from django.forms.widgets import TextInput
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, Relation
from creme_core.forms import CremeEntityField, CremeDateTimeField
from creme_core.forms.widgets import Label

from creme_config.forms.fields import CreatorModelChoiceField

from media_managers.models import Image
from media_managers.forms.widgets import ImageM2MWidget

from persons.models import Organisation, Contact
from persons.models.other_models import Position, Sector, Civility

from persons.forms.base import _BasePersonForm


class ContactForm(_BasePersonForm):
    birthday = CremeDateTimeField(label=_('Birthday'), required=False)
    image    = CremeEntityField(label=_('Image'), required=False, model=Image, widget=ImageM2MWidget())
#    position = ModelChoiceField(label=_('Position'), 
#                                queryset=Position.objects.all(), 
#                                required=False, 
#                                widget=ActionButtonList(delegate=DynamicSelect(options=lambda:((position.pk, unicode(position)) for position in Position.objects.all())))
#                                            .add_action('create', _(u'Add'), url='/creme_config/persons/position/add_widget/'))

    civility = CreatorModelChoiceField(label=_('Civility'), queryset=Civility.objects.all(), required=False, initial=None)
    position = CreatorModelChoiceField(label=_('Position'), queryset=Position.objects.all(), required=False, initial=None)
    sector = CreatorModelChoiceField(label=_('Sector'), queryset=Sector.objects.all(), required=False, initial=None)

    blocks = _BasePersonForm.blocks.new(('coordinates', _(u'Coordinates'), ['skype', 'phone', 'mobile', 'fax', 'email', 'url_site']))

    #class Meta:
    class Meta(_BasePersonForm.Meta):
        model = Contact
        #exclude = _BasePersonForm.Meta.exclude + ('language',)
    
    def __init__(self, *args, **kwargs):
        super(ContactForm, self).__init__(*args, **kwargs)
        self.fields['position'].user = self.user
        self.fields['civility'].user = self.user
        self.fields['sector'].user = self.user


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
                                       initial=self.relation_type
                                      )
        else:
            get_ct = ContentType.objects.get_for_model
            relation_field = ModelChoiceField(label=ugettext(u"Status in the organisation"),
                                              queryset=RelationType.objects.filter(subject_ctypes=get_ct(Contact),
                                                                                   object_ctypes=get_ct(Organisation))
                                             )
        self.fields['relation'] = relation_field

    def save(self):
        instance = super(ContactWithRelationForm, self).save()

        if self.linked_orga:
            Relation.objects.create(subject_entity=instance,
                                    type=self.relation_type or self.cleaned_data.get('relation'),
                                    object_entity=self.linked_orga,
                                    user=instance.user,
                                   )

        return instance
