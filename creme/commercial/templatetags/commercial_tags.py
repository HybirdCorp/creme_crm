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

# import warnings

from django.template import Library
# from django.utils.html import escape

from creme.creme_core.gui.quick_forms import quickforms_registry


register = Library()


# TODO: move to creme_core
@register.filter
def has_quickform(ctype):
    return quickforms_registry.get_form(ctype.model_class()) is not None


# @register.simple_tag
# def get_segments_for_category(strategy, orga, category):
#     warnings.warn('{% get_segments_for_category %} is deprecated ; use {% commercial_segments_for_category %} instead.',
#                   DeprecationWarning
#                  )
#
#     return u'<ul>%s</ul>' % (u'\n'.join(u'<li><h3>%s</h3></li>' % escape(segment)
#                                             for segment in strategy.get_segments_for_category(orga, category)
#                                        )
#                             )


@register.assignment_tag
def commercial_segments_for_category(strategy, orga, category):
    return strategy.get_segments_for_category(orga, category)


# @register.inclusion_tag('commercial/templatetags/widget_score.html', takes_context=True)
# def widget_asset_score(context, segment_desc, asset):
#     warnings.warn('{% widget_asset_score %} is deprecated ; use {% commercial_widget_asset_score %} instead.',
#                   DeprecationWarning
#                  )
#
#     strategy = context['strategy']
#     orga     = context['orga']
#
#     context['score'] = strategy.get_asset_score(orga, asset, segment_desc)
#     context['model_name'] = 'asset'
#     context['view_name'] = 'commercial__set_asset_score'
#     context['model'] = asset
#     context['has_perm'] = context['user'].has_perm_to_change(strategy)
#
#     return context


@register.inclusion_tag('commercial/templatetags/widget-score.html', takes_context=True)
def commercial_widget_asset_score(context, segment_desc, asset):
    strategy = context['strategy']
    orga     = context['orga']

    context['score'] = strategy.get_asset_score(orga, asset, segment_desc)
    context['view_name'] = 'commercial__set_asset_score'
    context['scored_instance'] = asset
    context['has_perm'] = context['user'].has_perm_to_change(strategy)

    return context


# @register.inclusion_tag('commercial/templatetags/widget_score.html', takes_context=True)
# def widget_charm_score(context, segment, charm):
#     warnings.warn('{% widget_charm_score %} is deprecated ; use {% commercial_widget_charm_score %} instead.',
#                   DeprecationWarning
#                  )
#
#     strategy = context['strategy']
#     orga     = context['orga']
#
#     context['score'] = strategy.get_charm_score(orga, charm, segment)
#     context['model_name'] = 'charm'
#     context['view_name'] = 'commercial__set_charm_score'
#     context['model'] = charm
#     context['has_perm'] = context['user'].has_perm_to_change(strategy)
#
#     return context


@register.inclusion_tag('commercial/templatetags/widget-score.html', takes_context=True)
def commercial_widget_charm_score(context, segment, charm):
    strategy = context['strategy']
    orga     = context['orga']

    context['score'] = strategy.get_charm_score(orga, charm, segment)
    context['view_name'] = 'commercial__set_charm_score'
    context['scored_instance'] = charm
    context['has_perm'] = context['user'].has_perm_to_change(strategy)

    return context


# @register.inclusion_tag('commercial/templatetags/widget_category.html', takes_context=True)
# def widget_segment_category(context, segment):
#     warnings.warn('{% widget_segment_category %} is deprecated.', DeprecationWarning)
#
#     strategy = context['strategy']
#     orga     = context['orga']
#
#     context['category'] = strategy.get_segment_category(orga, segment)
#     context['has_perm'] = context['user'].has_perm_to_change(strategy)
#
#     return context
