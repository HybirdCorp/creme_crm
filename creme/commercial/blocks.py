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

from django.utils.translation import ugettext_lazy as _

from creme_core.gui.block import Block, list4url

from commercial.models import CommercialApproach


class ApproachesBlock(Block):
    id_           = Block.generate_id('commercial', 'approaches')
    order_by      = 'title'
    verbose_name  = _(u'Démarches commerciales')
    template_name = 'commercial/templatetags/block_approaches.html'

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, CommercialApproach.get_approaches(pk),
                                                            update_url='/commercial/approaches/reload/%s/' % pk))

    def portal_display(self, context, ct_ids):
        #TODO: CommercialApproach.get_for_ct() ????
        return self._render(self.get_block_template_context(context,
                                                            CommercialApproach.objects.filter(entity_content_type__id__in=ct_ids, ok_or_in_futur=False),
                                                            update_url='/commercial/approaches/reload/portal/%s/' % list4url(ct_ids)))

    def home_display(self, context):
        return self._render(self.get_block_template_context(context, CommercialApproach.get_approaches(),
                                                            update_url='/commercial/approaches/reload/home/'))

approaches_block = ApproachesBlock()
