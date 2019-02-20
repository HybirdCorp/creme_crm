# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

import warnings

from django.template import Library

# from creme.creme_core.gui.quick_forms import quickforms_registry


register = Library()


@register.filter
def has_quickform(ctype):
    warnings.warn('The template filter "|has_quickform" from the lib '
                  '"commercial_tags" is deprecated ; use "|ctype_has_quickform" '
                  'from the lib "creme_ctype" instead.',
                  DeprecationWarning
                 )

    # return quickforms_registry.get_form(ctype.model_class()) is not None
    from creme.creme_core.templatetags.creme_ctype import ctype_has_quickform
    return ctype_has_quickform(ctype)


@register.simple_tag
def commercial_segments_for_category(strategy, orga, category):  # TODO: keyword arguments only ?
    return strategy.get_segments_for_category(orga, category)


@register.inclusion_tag('commercial/templatetags/widget-score.html', takes_context=True)
def commercial_widget_asset_score(context, segment_desc, asset):  # TODO: keyword arguments only ?
    strategy = context['strategy']
    orga     = context['orga']

    context['score'] = strategy.get_asset_score(orga, asset, segment_desc)
    context['view_name'] = 'commercial__set_asset_score'
    context['scored_instance'] = asset
    context['has_perm'] = context['user'].has_perm_to_change(strategy)

    return context


@register.inclusion_tag('commercial/templatetags/widget-score.html', takes_context=True)
def commercial_widget_charm_score(context, segment, charm):  # TODO: keyword arguments only ?
    strategy = context['strategy']
    orga     = context['orga']

    context['score'] = strategy.get_charm_score(orga, charm, segment)
    context['view_name'] = 'commercial__set_charm_score'
    context['scored_instance'] = charm
    context['has_perm'] = context['user'].has_perm_to_change(strategy)

    return context
