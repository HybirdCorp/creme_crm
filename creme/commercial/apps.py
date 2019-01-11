# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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


class CommercialConfig(CremeAppConfig):
    name = 'creme.commercial'
    verbose_name = _(u'Commercial strategy')
    dependencies = ['creme.persons', 'creme.opportunities']

    def all_apps_ready(self):
        from django.apps import apps

        from . import get_act_model, get_pattern_model, get_strategy_model

        self.Act      = get_act_model()
        self.Pattern  = get_pattern_model()
        self.Strategy = get_strategy_model()
        super().all_apps_ready()

        from . import signals

        if apps.is_installed('creme.activities'):
            self.hook_activities()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Act, self.Pattern, self.Strategy)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(bricks.ApproachesBrick,
                                bricks.SegmentsBrick,
                                bricks.SegmentDescriptionsBrick,
                                bricks.AssetsBrick,
                                bricks.CharmsBrick,
                                bricks.EvaluatedOrgasBrick,
                                bricks.AssetsMatrixBrick,
                                bricks.CharmsMatrixBrick,
                                bricks.AssetsCharmsMatrixBrick,
                                bricks.ActObjectivesBrick,
                                bricks.RelatedOpportunitiesBrick,
                                bricks.PatternComponentsBrick,
                               )

    def register_bulk_update(self, bulk_update_registry):
        from .models import ActObjectivePatternComponent, MarketSegmentDescription

        register = bulk_update_registry.register
        register(ActObjectivePatternComponent, exclude=['success_rate'])  # TODO: min_value/max_value constraint in the model... )
        register(MarketSegmentDescription,     exclude=['segment'])  # TODO: special form for segment

    def register_buttons(self, button_registry):
        from . import buttons

        button_registry.register(buttons.CompleteGoalButton)

    def register_icons(self, icon_registry):
        reg_icon = icon_registry.register
        reg_icon(self.Act,      'images/commercial_%(size)s.png')
        reg_icon(self.Pattern,  'images/commercial_%(size)s.png')
        reg_icon(self.Strategy, 'images/commercial_%(size)s.png')

    def register_menu(self, creme_menu):
        from django.urls import reverse_lazy as reverse

        from creme.persons import get_contact_model

        from .models import MarketSegment

        Act = self.Act
        Pattern  = self.Pattern
        Strategy = self.Strategy

        URLItem = creme_menu.URLItem
        features = creme_menu.get('features')
        features.get('persons-directory') \
                .add(URLItem('commercial-salesmen', url=reverse('commercial__list_salesmen'),
                             label=_(u'Salesmen'), perm='persons',
                            ),
                     priority=100
                    )
        features.get_or_create(creme_menu.ContainerItem, 'opportunities-commercial', priority=30,
                               defaults={'label': _(u'Commercial')},
                              ) \
                .add(URLItem.list_view('commercial-acts',       model=Act),           priority=50) \
                .add(URLItem.list_view('commercial-strategies', model=Strategy),      priority=55) \
                .add(URLItem.list_view('commercial-segments',   model=MarketSegment), priority=60) \
                .add(URLItem.list_view('commercial-patterns',   model=Pattern),       priority=70)

        creation = creme_menu.get('creation')
        creation.get('main_entities').add(URLItem.creation_view('commercial-create_act', model=Act), priority=100)

        any_forms = creation.get('any_forms')
        any_forms.get_or_create_group('persons-directory', _(u'Directory'), priority=10) \
                 .add_link('create_salesman', model=get_contact_model(), label=_(u'Salesman'),
                           url=reverse('commercial__create_salesman'), priority=10,
                          )
        any_forms.get_or_create_group('opportunities-commercial', _(u'Commercial'), priority=15) \
                 .add_link('commercial-create_act',      Act,      priority=50) \
                 .add_link('commercial-create_strategy', Strategy, priority=55) \
                 .add_link('commercial-create_pattern',  Pattern,  priority=60)

    def register_setting_keys(self, setting_key_registry):
        from . import setting_keys

        setting_key_registry.register(setting_keys.orga_approaches_key)

    def hook_activities(self):
        from functools import partial

        from django.forms import BooleanField

        from creme.activities.forms.activity import ActivityCreateForm

        from .models import CommercialApproach

        def add_commapp_field(form):
            form.fields['is_comapp'] = BooleanField(
                required=False, label=_(u'Is a commercial approach ?'),
                help_text=_(u'All participants (excepted users), subjects and linked entities '
                            u'will be linked to a commercial approach.'
                           ),
                initial=True
            )

        def save_commapp_field(form):
            cleaned_data = form.cleaned_data

            if not cleaned_data.get('is_comapp', False):
                return

            comapp_subjects = list(cleaned_data['other_participants'])
            comapp_subjects += cleaned_data['subjects']
            comapp_subjects += cleaned_data['linked_entities']

            if not comapp_subjects:
                return

            instance = form.instance
            create_comapp = partial(CommercialApproach.objects.create,
                                    title=instance.title,
                                    description=instance.description,
                                    related_activity=instance,
                                   )

            for entity in comapp_subjects:
                create_comapp(creme_entity=entity)

        ActivityCreateForm.add_post_init_callback(add_commapp_field)
        ActivityCreateForm.add_post_save_callback(save_commapp_field)
