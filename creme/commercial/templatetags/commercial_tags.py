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

from django.template import Library

from commercial.models import CommercialAssetScore


register = Library()

@register.simple_tag #TODO: inclusion_tag => takes_context ??????
def get_segments_for_category(strategy, orga, category):
    return u'<ul>%s</ul>' % (u'\n'.join(u'<li><h3>%s</h3></li>' % segment for segment in strategy.get_segments_for_category(orga, category)))

@register.inclusion_tag('commercial/templatetags/widget_score.html', takes_context=True)
def widget_asset_score(context, segment, asset):
    strategy = context['strategy']
    orga     = context['orga']

    context['score'] = strategy.get_asset_score(orga, asset, segment)
    context['model_name'] = 'asset'
    context['model'] = asset

    return context

@register.inclusion_tag('commercial/templatetags/widget_score.html', takes_context=True)
def widget_charm_score(context, segment, charm):
    strategy = context['strategy']
    orga     = context['orga']

    context['score'] = strategy.get_charm_score(orga, charm, segment)
    context['model_name'] = 'charm'
    context['model'] = charm

    return context

@register.inclusion_tag('commercial/templatetags/widget_category.html', takes_context=True)
def widget_segment_category(context, segment):
    strategy = context['strategy']
    orga     = context['orga']

    context['category'] = strategy.get_segment_category(orga, segment)

    return context
