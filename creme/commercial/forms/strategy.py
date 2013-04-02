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

from django.utils.translation import ugettext_lazy as _
from django.forms import CharField

from creme.creme_core.models import CremePropertyType
from creme.creme_core.forms import CremeForm, CremeModelForm, CremeEntityForm, FieldBlockManager, MultiCremeEntityField

from creme.persons.models import Organisation

from creme.commercial.models import Strategy, MarketSegment, MarketSegmentDescription, CommercialAsset, MarketSegmentCharm


class StrategyForm(CremeEntityForm):
    class Meta(CremeEntityForm.Meta):
        model = Strategy


class _AuxForm(CremeModelForm):
    class Meta:
        exclude = ('strategy',)

    def __init__(self, entity, *args, **kwargs):
        super(_AuxForm, self).__init__(*args, **kwargs)
        self._strategy = entity

    def save(self, *args, **kwargs):
        self.instance.strategy = self._strategy
        return super(_AuxForm, self).save(*args, **kwargs)


class SegmentLinkForm(_AuxForm):
    class Meta(_AuxForm.Meta):
        model = MarketSegmentDescription

    def __init__(self, entity, *args, **kwargs):
        super(SegmentLinkForm, self).__init__(entity, *args, **kwargs)

        segment_field = self.fields['segment']
        segment_field.queryset = MarketSegment.objects.exclude(marketsegmentdescription__strategy=entity)
        segment_field.empty_label = None


class AssetForm(_AuxForm):
    class Meta(_AuxForm.Meta):
        model = CommercialAsset


class CharmForm(_AuxForm):
    class Meta(_AuxForm.Meta):
        model = MarketSegmentCharm


class _SegmentForm(_AuxForm):
    name = CharField(label=_(u"Name"), max_length=100)

    blocks = FieldBlockManager(('general', _(u'General information'), ['name', 'product', 'place', 'price', 'promotion']))

    class Meta:
        model = MarketSegmentDescription
        exclude = _AuxForm.Meta.exclude + ('segment',)


class SegmentEditForm(_SegmentForm):
    def __init__(self, *args, **kwargs):
        super(SegmentEditForm, self).__init__(*args, **kwargs)
        self.fields['name'].initial = self.instance.segment.name

    def save(self):
        seginfo = super(SegmentEditForm, self).save()
        name = self.cleaned_data['name']

        segment = seginfo.segment
        segment.name = name
        segment.save()

        ptype = segment.property_type
        ptype.text = MarketSegment.generate_property_text(name)
        ptype.save()

        return seginfo


class SegmentCreateForm(_SegmentForm):
    def save(self):
        segment_desc = self.instance
        name = self.cleaned_data['name']

        #TODO: factorise with market_segment.MarketSegmentForm ???
        # is_custom=False ==> CremePropertyType won't be deletable
        ptype = CremePropertyType.create('commercial-segment',
                                         MarketSegment.generate_property_text(name),
                                         generate_pk=True, is_custom=False
                                        )

        segment_desc.segment = MarketSegment.objects.create(name=name, property_type=ptype)
        super(SegmentCreateForm, self).save()

        return segment_desc


class AddOrganisationForm(CremeForm):
    organisations = MultiCremeEntityField(label=_(u"Organisations"), model=Organisation)

    def __init__(self, entity, *args, **kwargs):
        super(AddOrganisationForm, self).__init__(*args, **kwargs)
        self._strategy = entity

    def save(self):
        eval_orgas = self._strategy.evaluated_orgas

        for orga in self.cleaned_data['organisations']:
            eval_orgas.add(orga)
