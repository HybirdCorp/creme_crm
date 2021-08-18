# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class CommercialConfig(CremeAppConfig):
    default = True
    name = 'creme.commercial'
    verbose_name = _('Commercial strategy')
    # XXX: remove 'creme.activities' if we remove CommercialApproach?
    dependencies = ['creme.persons', 'creme.activities', 'creme.opportunities']

    def all_apps_ready(self):
        from django.apps import apps

        from . import get_act_model, get_pattern_model, get_strategy_model

        self.Act      = get_act_model()
        self.Pattern  = get_pattern_model()
        self.Strategy = get_strategy_model()
        super().all_apps_ready()

        from . import signals  # NOQA

        if apps.is_installed('creme.activities'):
            self.hook_activities()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Act, self.Pattern, self.Strategy)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.ApproachesBrick,
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
        from . import models

        register = bulk_update_registry.register
        # TODO: min_value/max_value constraint in the model... )
        register(models.ActObjectivePatternComponent, exclude=['success_rate'])
        # TODO: special form for segment
        register(models.MarketSegmentDescription, exclude=['segment'])

    def register_buttons(self, button_registry):
        from . import buttons

        button_registry.register(buttons.CompleteGoalButton)

    def register_creme_config(self, config_registry):
        from . import models

        config_registry.register_model(models.ActType, 'act_type')

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.ACT_CREATION_CFORM,
            custom_forms.ACT_EDITION_CFORM,

            custom_forms.PATTERN_CREATION_CFORM,
            custom_forms.PATTERN_EDITION_CFORM,

            custom_forms.STRATEGY_CREATION_CFORM,
            custom_forms.STRATEGY_EDITION_CFORM,
        )

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(
            self.Act, self.Pattern, self.Strategy,
        )

    def register_icons(self, icon_registry):
        icon_registry.register(
            self.Act,      'images/commercial_%(size)s.png',
        ).register(
            self.Pattern,  'images/commercial_%(size)s.png',
        ).register(
            self.Strategy, 'images/commercial_%(size)s.png',
        )

    # def register_menu(self, creme_menu):
    #     from django.urls import reverse_lazy as reverse
    #
    #     from creme.persons import get_contact_model
    #
    #     from .models import MarketSegment
    #
    #     Act = self.Act
    #     Pattern  = self.Pattern
    #     Strategy = self.Strategy
    #
    #     URLItem = creme_menu.URLItem
    #     features = creme_menu.get('features')
    #     features.get(
    #         'persons-directory',
    #     ).add(
    #         URLItem(
    #             'commercial-salesmen', url=reverse('commercial__list_salesmen'),
    #             label=_('Salesmen'), perm='persons',
    #         ),
    #         priority=100
    #     )
    #     features.get_or_create(
    #         creme_menu.ContainerItem, 'opportunities-commercial',
    #         priority=30,
    #         defaults={'label': _('Commercial')},
    #     ).add(
    #         URLItem.list_view('commercial-acts', model=Act),
    #         priority=50,
    #     ).add(
    #         URLItem.list_view('commercial-strategies', model=Strategy),
    #         priority=55,
    #     ).add(
    #         URLItem.list_view('commercial-segments', model=MarketSegment),
    #         priority=60,
    #     ).add(
    #         URLItem.list_view('commercial-patterns', model=Pattern),
    #         priority=70,
    #     )
    #
    #     creation = creme_menu.get('creation')
    #     creation.get(
    #         'main_entities',
    #     ).add(
    #         URLItem.creation_view('commercial-create_act', model=Act),
    #         priority=100,
    #     )
    #
    #     any_forms = creation.get('any_forms')
    #     any_forms.get_or_create_group(
    #         'persons-directory', _('Directory'), priority=10,
    #     ).add_link(
    #         'create_salesman', model=get_contact_model(), label=_('Salesman'),
    #         url=reverse('commercial__create_salesman'), priority=10,
    #     )
    #     any_forms.get_or_create_group(
    #         'opportunities-commercial', _('Commercial'), priority=15,
    #     ).add_link(
    #         'commercial-create_act', Act, priority=50,
    #     ).add_link(
    #         'commercial-create_strategy', Strategy, priority=55,
    #     ).add_link(
    #         'commercial-create_pattern', Pattern,  priority=60,
    #     )

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.ActsEntry,
            menu.StrategiesEntry,
            menu.PatternsEntry,
            menu.SegmentsEntry,

            menu.SalesmenEntry,

            menu.ActCreationEntry,
            menu.StrategyCreationEntry,
            menu.PatternCreationEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        from django.urls import reverse_lazy as reverse

        from creme.persons import get_contact_model

        creation_menu_registry.get_or_create_group(
            'persons-directory', _('Directory'), priority=10,
        ).add_link(
            'create_salesman', model=get_contact_model(), label=_('Salesman'),
            url=reverse('commercial__create_salesman'), priority=10,
        )
        creation_menu_registry.get_or_create_group(
            'opportunities-commercial', _('Commercial'), priority=15,
        ).add_link(
            'commercial-create_act',      self.Act,      priority=50,
        ).add_link(
            'commercial-create_strategy', self.Strategy, priority=55,
        ).add_link(
            'commercial-create_pattern',  self.Pattern,  priority=60,
        )

    def register_setting_keys(self, setting_key_registry):
        from . import setting_keys

        setting_key_registry.register(setting_keys.orga_approaches_key)

    def hook_activities(self):
        from creme.activities import custom_forms as act_cforms
        from creme.activities import get_activity_model
        from creme.commercial.forms.activity import IsCommercialApproachSubCell

        Activity = get_activity_model()

        for cform_desc in (
            act_cforms.ACTIVITY_CREATION_CFORM,
            act_cforms.ACTIVITY_CREATION_FROM_CALENDAR_CFORM,
        ):
            cform_desc.extra_sub_cells = [
                *cform_desc.extra_sub_cells,
                IsCommercialApproachSubCell(model=Activity),
            ]
