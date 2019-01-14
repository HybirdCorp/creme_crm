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
#
# from django.contrib.contenttypes.models import ContentType
# from django.core.exceptions import PermissionDenied
# from django.db.models import Q
# from django.shortcuts import render
# from django.urls import reverse
# from django.utils.translation import ugettext as _
#
# from creme.creme_core.auth.decorators import login_required
# from creme.creme_core.gui.bricks import brick_registry
# from creme.creme_core.models import BrickHomeLocation
#
#
# @login_required
# def app_portal(request, app_name, template, models, stats, config_url=None, extra_template_dict=None):
#     warnings.warn('creme_core.views.generic.portal.app_portal() is deprecated.', DeprecationWarning)
#
#     has_perm = request.user.has_perm
#
#     if not has_perm(app_name):
#         raise PermissionDenied(_(u'You are not allowed to access to the app: {}').format(app_name))
#
#     get_ct = ContentType.objects.get_for_model
#
#     try:
#         ct_ids = [get_ct(model).id for model in models]
#     except TypeError:  # 'models' is a not a sequence -> CremeEntity
#         ct_ids = [get_ct(models).id]
#
#     locs = BrickHomeLocation.objects.filter(Q(app_name='') | Q(app_name=app_name)) \
#                                     .order_by('order')
#
#     # We fallback to the default config is there is no config for this app.
#     brick_ids = [loc.brick_id for loc in locs if loc.app_name] or [loc.brick_id for loc in locs]
#
#     template_dict = {'app_name':          app_name,
#                      'ct_ids':            ct_ids,
#                      'stats':             stats,
#                      'config_url':        config_url,
#                      'can_admin':         has_perm('{}.can_admin'.format(app_name)),
#                      'bricks':            list(brick_registry.get_bricks([id_ for id_ in brick_ids if id_])),
#                      'bricks_reload_url': reverse('creme_core__reload_portal_bricks') + '?' +
#                                           '&'.join('ct_id=%d' % ct_id for ct_id in ct_ids),
#                     }
#
#     if extra_template_dict is not None:
#         template_dict.update(extra_template_dict)
#
#     return render(request, template, template_dict)
