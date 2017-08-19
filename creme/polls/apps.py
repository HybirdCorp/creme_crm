# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2017  Hybird
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

from creme.creme_core.apps import CremeAppConfig


class PollsConfig(CremeAppConfig):
    name = 'creme.polls'
    verbose_name = _(u'Polls')
    dependencies = ['creme.persons', 'creme.commercial']

    def all_apps_ready(self):
        from . import get_pollform_model, get_pollreply_model, get_pollcampaign_model

        self.PollCampaign = get_pollcampaign_model()
        self.PollForm     = get_pollform_model()
        self.PollReply    = get_pollreply_model()
        super(PollsConfig, self).all_apps_ready()

    # def register_creme_app(self, creme_registry):
    #     creme_registry.register_app('polls', _(u'Polls'), '/polls')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.PollForm, self.PollReply, self.PollCampaign)

    def register_bricks(self, brick_registry):
        # from .blocks import block_list
        from . import bricks

        # brick_registry.register(*block_list)
        brick_registry.register(bricks.PollFormLinesBrick,
                                bricks.PollReplyLinesBrick,
                                bricks.PollRepliesBrick,
                                bricks.PersonPollRepliesBrick,
                                bricks.PollCampaignRepliesBrick,
                               )
        brick_registry.register_hat(self.PollForm, main_brick_cls=bricks.PollFormBarHatBrick)

    def register_bulk_update(self, bulk_update_registry):
        from .forms.poll_reply import InnerEditPersonForm
        from .models import PollFormLine

        bulk_update_registry.register(self.PollReply,
                                      innerforms={'person': InnerEditPersonForm},
                                     )
        bulk_update_registry.register(PollFormLine, exclude=['type'])

    def register_icons(self, icon_registry):
        reg_icon = icon_registry.register
        reg_icon(self.PollForm,     'images/poll_%(size)s.png')
        reg_icon(self.PollReply,    'images/poll_%(size)s.png')
        reg_icon(self.PollCampaign, 'images/poll_%(size)s.png')

    def register_menu(self, creme_menu):
        from django.conf import settings

        PCampaign = self.PollCampaign
        PForm     = self.PollForm
        PReply    = self.PollReply

        if settings.OLD_MENU:
            from django.core.urlresolvers import reverse_lazy as reverse
            from creme.creme_core.auth import build_creation_perm as cperm

            reg_item = creme_menu.register_app('polls', '/polls/').register_item
            # reg_item('/polls/',                         _(u'Portal of polls'),    'polls')
            reg_item(reverse('polls__portal'),          _(u'Portal of polls'),    'polls')
            reg_item(reverse('polls__list_forms'),      _(u'All forms'),          'polls')
            reg_item(reverse('polls__create_form'),     PForm.creation_label,     cperm(PForm))
            reg_item(reverse('polls__list_replies'),    _(u'All replies'),        'polls')
            reg_item(reverse('polls__create_reply'),    PReply.creation_label,    cperm(PReply))
            reg_item(reverse('polls__list_campaigns'),  _(u'All campaigns'),      'polls')
            reg_item(reverse('polls__create_campaign'), PCampaign.creation_label, cperm(PCampaign))
        else:
            LvURLItem = creme_menu.URLItem.list_view
            creme_menu.get('features', 'tools') \
                      .get_or_create(creme_menu.ItemGroup, 'polls', priority=300, defaults={'label': _(u'Polls')}) \
                      .add(LvURLItem('polls-pforms',    model=PForm),     priority=10) \
                      .add(LvURLItem('polls-preplies',  model=PReply),    priority=20) \
                      .add(LvURLItem('polls-campaigns', model=PCampaign), priority=30)
            creme_menu.get('creation', 'any_forms') \
                      .get_or_create_group('tools', _(u'Tools'), priority=100) \
                      .add_link('polls-create_pform',    PForm,     priority=300) \
                      .add_link('polls-create_preply',   PReply,    priority=302) \
                      .add_link('polls-create_campaign', PCampaign, priority=304)
