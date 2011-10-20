# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity
from creme_core.utils import get_from_POST_or_404

from billing.models import SalesOrder, Invoice, TemplateBase


_CLASS_MAP = {'sales_order': SalesOrder, 'invoice': Invoice}


@login_required
@permission_required('billing')
def convert(request, document_id):
    src = get_object_or_404(CremeEntity, pk=document_id).get_real_entity()
    user = request.user

    src.can_view_or_die(user)

    dest_class = _CLASS_MAP.get(get_from_POST_or_404(request.POST, 'type'))
    if not dest_class:
        raise Http404('Error: "type" argument must be in : %s' % ', '.join(_CLASS_MAP.iterkeys()))

    user.has_perm_to_create_or_die(dest_class)

    if isinstance(src, TemplateBase): #TODO: unitest
        dest = TemplateBase()
        dest.build(src, ContentType.objects.get_for_model(dest_class))
        dest.name = _(u'%(src)s (converted into template of <%(dest)s>)') % {'src': src.name, 'dest': dest_class._meta.verbose_name}
        dest.save()
        # Generator of template src now works with converted template
        generator = src.get_generator()
        generator.template = dest #TODO: old Template is 'lost' ? (no deleted but no linkable to a generator anymore)
        generator.save()
    else:
        dest = dest_class()
        dest.build(src)
        dest.name = _(u'%(src)s (converted into  %(dest)s)') % {'src': src.name, 'dest': dest._meta.verbose_name}
        dest.generate_number()
        dest.save()

    return HttpResponseRedirect(dest.get_absolute_url())
