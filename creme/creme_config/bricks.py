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

from future_builtins import filter

from collections import defaultdict
import logging

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
# from django.core.urlresolvers import reverse
from django.db.models import Count
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.core import setting_key
from creme.creme_core.gui.bricks import Brick, PaginatedBrick, QuerysetBrick, brick_registry
# from creme.creme_core.gui.fields_config import fields_config_registry
from creme.creme_core.models import (CremeModel, CremeEntity, UserRole, SettingValue,
        CremePropertyType, RelationType, SemiFixedRelationType, FieldsConfig,
        CustomField, CustomFieldEnumValue,
        BlockDetailviewLocation, BlockPortalLocation, BlockMypageLocation,
        RelationBlockItem, InstanceBlockConfigItem, CustomBlockConfigItem,
        ButtonMenuItem, SearchConfigItem, HistoryConfigItem, PreferedMenuItem)
from creme.creme_core.registry import creme_registry
from creme.creme_core.utils import creme_entity_content_types
from creme.creme_core.utils.unicode_collation import collator


_PAGE_SIZE = 20
User = get_user_model()
logger = logging.getLogger(__name__)


class GenericModelBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('creme_config', 'model_config')
    dependencies  = (CremeModel,)
    page_size     = _PAGE_SIZE
    verbose_name  = u'Model configuration'
    template_name = 'creme_config/bricks/configurable-model.html'
    configurable  = False

    # NB: credentials are OK : we are sure to use the custom reloading view because of the specific constructor.
    def __init__(self, app_name, model_name, model):
        super(GenericModelBrick, self).__init__()
        self.app_name = app_name
        self.model_name = model_name
        self.model = model

    def detailview_display(self, context):
        model = self.model
        meta = model._meta

        # TODO: (must declare in the template what fields can be used to sort)
        # ordering = meta.ordering
        # if ordering:
        #     self.order_by = ordering[0]

        displayable_fields = []
        is_reorderable = False

        for field in meta.fields:
            fieldname = field.name.lower()

            if fieldname == 'is_custom':
                continue
            elif fieldname == 'order':
                is_reorderable = True
            else:
                displayable_fields.append(field)

        displayable_fields.extend(meta.many_to_many)

        return self._render(self.get_template_context(
                    context,
                    model.objects.all(),

                    model=model,
                    meta=meta,

                    app_name=self.app_name,
                    model_name=self.model_name,

                    model_is_reorderable=is_reorderable,
                    displayable_fields=displayable_fields,
        ))


class SettingsBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('creme_config', 'settings')
    dependencies  = (SettingValue,)
    page_size     = _PAGE_SIZE
    verbose_name  = u'App settings'
    # template_name = 'creme_config/templatetags/block_settings.html'
    template_name = 'creme_config/bricks/setting-values.html'
    configurable  = False

    def detailview_display(self, context):
        app_name = context['app_name']
        skeys_ids = [skey.id
                        for skey in setting_key.setting_key_registry
                            if skey.app_label == app_name and not skey.hidden
                    ]

        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                                context,
                                SettingValue.objects.filter(key_id__in=skeys_ids, user=None),
                                # # update_url='/creme_config/settings/%s/reload/' % app_name,
                                # update_url=reverse('creme_config__reload_settings_block', args=(app_name,)),
                                app_name=app_name,
                           ))


class _ConfigAdminBrick(QuerysetBrick):
    page_size    = _PAGE_SIZE
    permission   = None  # The portals can be viewed by all users => reloading can be done by all uers too.
    configurable = False


class PropertyTypesBrick(_ConfigAdminBrick):
    id_           = _ConfigAdminBrick.generate_id('creme_config', 'property_types')
    dependencies  = (CremePropertyType,)
    order_by      = 'text'
    verbose_name  = _(u'Property types configuration')
    # template_name = 'creme_config/templatetags/block_property_types.html'
    template_name = 'creme_config/bricks/property-types.html'

    def detailview_display(self, context):
        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    CremePropertyType.objects.annotate(stats=Count('cremeproperty')),
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        ))


class RelationTypesBrick(_ConfigAdminBrick):
    id_           = _ConfigAdminBrick.generate_id('creme_config', 'relation_types')
    dependencies  = (RelationType,)
    verbose_name  = _(u'List of standard relation types')
    # template_name = 'creme_config/templatetags/block_relation_types.html'
    template_name = 'creme_config/bricks/relation-types.html'

    def detailview_display(self, context):
        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    RelationType.objects.filter(is_custom=False,
                                                pk__contains='-subject_',
                                               ),
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
                    custom=False,
        ))


class CustomRelationTypesBrick(_ConfigAdminBrick):
    id_           = _ConfigAdminBrick.generate_id('creme_config', 'custom_relation_types')
    dependencies  = (RelationType,)
    verbose_name  = _(u'Custom relation types configuration')
    # template_name = 'creme_config/templatetags/block_relation_types.html'
    template_name = 'creme_config/bricks/relation-types.html'

    def detailview_display(self, context):
        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    RelationType.objects.filter(is_custom=True,
                                                pk__contains='-subject_',
                                               ),
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
                    custom=True,
        ))


class SemiFixedRelationTypesBrick(_ConfigAdminBrick):
    id_           = _ConfigAdminBrick.generate_id('creme_config', 'semifixed_relation_types')
    dependencies  = (RelationType, SemiFixedRelationType,)
    verbose_name  = _(u'List of semi-fixed relation types')
    # template_name = 'creme_config/templatetags/block_semifixed_relation_types.html'
    template_name = 'creme_config/bricks/semi-fixed-relation-types.html'

    def detailview_display(self, context):
        # btc = self.get_block_template_context(
        btc = self.get_template_context(
                    context, SemiFixedRelationType.objects.all(),
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        )

        CremeEntity.populate_real_entities([sfrt.object_entity for sfrt in btc['page'].object_list])

        return self._render(btc)


class FieldsConfigsBrick(PaginatedBrick):
    id_           = PaginatedBrick.generate_id('creme_config', 'fields_configs')
    dependencies  = (FieldsConfig,)
    page_size     = _PAGE_SIZE
    verbose_name  = u'Fields configuration'
    # template_name = 'creme_config/templatetags/block_fields_configs.html'
    template_name = 'creme_config/bricks/fields-configs.html'
    permission    = None  # NB: used by the view creme_core.views.blocks.reload_basic()
    configurable  = False

    def detailview_display(self, context):
        # from .forms.fields_config import _get_fields_enum

        # TODO: exclude CTs that user cannot see ? (should probably done everywhere in creme_config...)
        fconfigs = list(FieldsConfig.objects.all())
        sort_key = collator.sort_key
        fconfigs.sort(key=lambda fconf: sort_key(unicode(fconf.content_type)))

        # used_ctypes = {fconf.content_type for fconf in fconfigs}
        used_models = {fconf.content_type.model_class() for fconf in fconfigs}
        # btc = self.get_block_template_context(
        btc = self.get_template_context(
                    context, fconfigs,
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
                    # display_add_button=any(ct not in used_ctypes and any(_get_fields_enum(ct))
                    #                             for ct in fields_config_registry.ctypes
                    #                       ),
                    display_add_button=any(model not in used_models
                                                for model in filter(FieldsConfig.is_model_valid, apps.get_models())
                                          ),
        )

        for fconf in btc['page'].object_list:
            vnames = [unicode(f.verbose_name) for f in fconf.hidden_fields]
            vnames.sort(key=sort_key)

            fconf.fields_vnames = vnames

        return self._render(btc)


class CustomFieldsBrick(Brick):
    id_           = Brick.generate_id('creme_config', 'custom_fields')
    dependencies  = (CustomField,)
    verbose_name  = u'Configuration of custom fields'
    template_name = 'creme_config/bricks/custom-fields.html'
    permission    = None  # NB: used by the view creme_core.views.bricks.reload_basic
    configurable  = False

    def detailview_display(self, context):
        # NB: we wrap the ContentType instances instead of store extra data in
        #     them because the instances are stored in a global cache, so we do
        #     not want to mutate them.
        class _ContentTypeWrapper(object):
            __slots__ = ('ctype', 'cfields')

            def __init__(self, ctype, cfields):
                self.ctype = ctype
                self.cfields = cfields

        cfields = CustomField.objects.all()

        # Retrieve & cache Enum values (in order to display them of course)
        enums_types = {CustomField.ENUM, CustomField.MULTI_ENUM}
        enums_cfields = [cfield
                            for cfield in cfields
                                if cfield.field_type in enums_types
                        ]
        evalues_map = defaultdict(list)

        for enum_value in CustomFieldEnumValue.objects.filter(custom_field__in=enums_cfields):
            evalues_map[enum_value.custom_field_id].append(enum_value.value)

        for enums_cfield in enums_cfields:
            enums_cfield.enum_values = evalues_map[enums_cfield.id]
        # ------

        cfields_per_ct_id = defaultdict(list)
        for cfield in cfields:
            cfields_per_ct_id[cfield.content_type_id].append(cfield)

        get_ct = ContentType.objects.get_for_id
        ctypes = [_ContentTypeWrapper(get_ct(ct_id), ct_cfields)
                    for ct_id, ct_cfields in cfields_per_ct_id.iteritems()
                 ]

        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                        context, ctypes=ctypes,
        ))


class UsersBrick(_ConfigAdminBrick):
    id_           = _ConfigAdminBrick.generate_id('creme_config', 'users')
    dependencies  = (User,)
    order_by      = 'username'
    verbose_name  = u'Users configuration'
    # template_name = 'creme_config/templatetags/block_users.html'
    template_name = 'creme_config/bricks/users.html'

    def detailview_display(self, context):
        users = User.objects.filter(is_team=False)

        if not context['user'].is_staff:
            users = users.exclude(is_staff=True)

        # btc = self.get_block_template_context(
        btc = self.get_template_context(
                    context, users,
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        )
        page = btc['page']
        page_users = page.object_list
        TIME_ZONE = settings.TIME_ZONE
        btc['display_tz'] = (any(user.time_zone != TIME_ZONE for user in page_users)
                             # All users are displayed if our page
                             if page.paginator.count == len(page_users) else
                             User.objects.exclude(time_zone=TIME_ZONE).exists()
                            )

        return self._render(btc)


class TeamsBrick(_ConfigAdminBrick):
    id_           = _ConfigAdminBrick.generate_id('creme_config', 'teams')
    dependencies  = (User,)
    order_by      = 'username'
    verbose_name  = u'Teams configuration'
    # template_name = 'creme_config/templatetags/block_teams.html'
    template_name = 'creme_config/bricks/teams.html'

    def detailview_display(self, context):
        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context, User.objects.filter(is_team=True),
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        ))


class BlockDetailviewLocationsBrick(PaginatedBrick):
    id_           = PaginatedBrick.generate_id('creme_config', 'blocks_dv_locations')
    dependencies  = (BlockDetailviewLocation,)
    page_size     = _PAGE_SIZE - 1  # '-1' because there is always the line for default config on each page
    verbose_name  = u'Blocks locations on detailviews'
    # template_name = 'creme_config/templatetags/block_blocklocations.html'
    template_name = 'creme_config/bricks/bricklocations-detailviews.html'
    permission    = None  # NB: used by the view creme_core.views.blocks.reload_basic
    configurable  = False

    def detailview_display(self, context):
        # NB: we wrap the ContentType instances instead of store extra data in
        #     them because the instances are stored in a global cache, so we do
        #     not want to mutate them.
        class _ContentTypeWrapper(object):  # TODO: move from here ?
            __slots__ = ('ctype', 'locations_info', 'default_count')

            def __init__(self, ctype):
                self.ctype = ctype
                self.default_count = 0
                self.locations_info = ()  # List of tuples (role_arg, role_label, block_count)
                                          # with role_arg == role.id or 'superuser'

        # TODO: factorise with SearchConfigBlock ?
        # TODO: factorise with CustomBlockConfigItemCreateForm , add a method in block_registry ?
        get_ct = ContentType.objects.get_for_model
        is_invalid = brick_registry.is_model_invalid
        ctypes = [_ContentTypeWrapper(get_ct(model))
                      for model in creme_registry.iter_entity_models()
                          if not is_invalid(model)
                 ]

        sort_key = collator.sort_key
        ctypes.sort(key=lambda ctw: sort_key(unicode(ctw.ctype)))

        # btc = self.get_block_template_context(
        btc = self.get_template_context(
                    context, ctypes,
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
                    max_conf_count=UserRole.objects.count() + 1,  # NB: '+ 1' is for super-users config.
        )

        ctypes_wrappers = btc['page'].object_list

        block_counts = defaultdict(lambda: defaultdict(int)) # block_counts[content_type.id][(role_id, superuser)] -> count
        role_ids = set()

        for bdl in BlockDetailviewLocation.objects \
                                          .filter(content_type__in=[ctw.ctype for ctw in ctypes_wrappers])\
                                          .exclude(zone=BlockDetailviewLocation.HAT):
            if bdl.block_id:  # Do not count the 'place-holder' (empty block IDs which mean "no-block for this zone")
                role_id = bdl.role_id
                block_counts[bdl.content_type_id][(role_id, bdl.superuser)] += 1
                role_ids.add(role_id)

        role_names = dict(UserRole.objects.filter(id__in=role_ids).values_list('id', 'name'))
        superusers_label = ugettext(u'Superuser')  # TODO: cached_lazy_ugettext

        for ctw in ctypes_wrappers:
            count_per_role = block_counts[ctw.ctype.id]
            ctw.default_count = count_per_role.pop((None, False), 0)

            ctw.locations_info = locations_info = []
            for (role_id, superuser), block_count in count_per_role.iteritems():
                if superuser:
                    role_arg = 'superuser'
                    role_label = superusers_label
                else:
                    role_arg = role_id
                    role_label = role_names[role_id]

                locations_info.append((role_arg, role_label, block_count))

            locations_info.sort(key=lambda t: sort_key(t[1]))  # Sort by role label

        btc['default_count'] = BlockDetailviewLocation.objects.filter(content_type=None,
                                                                      role=None, superuser=False,
                                                                     ).count()

        return self._render(btc)


# TODO: remove when portals/old_menu are removed (template file too)
class BlockPortalLocationsBrick(PaginatedBrick):
    id_           = PaginatedBrick.generate_id('creme_config', 'blocks_portal_locations')
    dependencies  = (BlockPortalLocation,)
    page_size     = _PAGE_SIZE - 2  # '-2' because there is always the line for default config & home config on each page
    verbose_name  = u'Blocks locations on portals'
    # template_name = 'creme_config/templatetags/block_blockportallocations.html'
    template_name = 'creme_config/bricks/bricklocations-portals.html'
    permission    = None  # NB: used by the view creme_core.views.blocks.reload_basic()
    configurable  = False

    def detailview_display(self, context):
        # get_app = creme_registry.get_app
        # apps = list(filter(None,
        #                    (get_app(name, silent_fail=True)
        #                         for name in BlockPortalLocation.objects.exclude(app_name='creme_core')
        #                                                        .order_by('app_name')  # In order that distinct() works correctly
        #                                                        .distinct()
        #                                                        .values_list('app_name', flat=True)
        #                                if name
        #                    )
        #            ))
        app_configs = []

        for label in (BlockPortalLocation.objects.exclude(app_name='creme_core')
                                                 .order_by('app_name')  # In order that distinct() works correctly
                                                 .distinct()
                                                 .values_list('app_name', flat=True)):
            try:
                app_configs.append(apps.get_app_config(label))
            except LookupError:
                logger.warn('BlockPortalLocationsBlock: the app "%s" is not installed')

        sort_key = collator.sort_key
        # apps.sort(key=lambda app: sort_key(app.verbose_name))
        app_configs.sort(key=lambda app: sort_key(app.verbose_name))

        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    # apps,
                    app_configs,
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        ))


class BlockHomeLocationsBrick(_ConfigAdminBrick):
    id_           = _ConfigAdminBrick.generate_id('creme_config', 'blocks_home_locations')
    dependencies  = (BlockPortalLocation,)
    verbose_name  = u'Locations of blocks on the home page.'
    template_name = 'creme_config/bricks/bricklocations-home.html'

    def detailview_display(self, context):
        return self._render(self.get_template_context(
                    context,
                    BlockPortalLocation.objects.filter(app_name='creme_core'),
        ))


class BlockDefaultMypageLocationsBrick(_ConfigAdminBrick):
    id_           = _ConfigAdminBrick.generate_id('creme_config', 'blocks_default_mypage_locations')
    dependencies  = (BlockMypageLocation,)
    verbose_name  = u'Default blocks locations on "My page"'
    # template_name = 'creme_config/templatetags/block_blockdefmypagelocations.html'
    template_name = 'creme_config/bricks/bricklocations-mypage-default.html'

    def detailview_display(self, context):
        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    BlockMypageLocation.objects.filter(user=None),
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        ))


class BlockMypageLocationsBrick(_ConfigAdminBrick):
    id_           = _ConfigAdminBrick.generate_id('creme_config', 'blocks_mypage_locations')
    dependencies  = (BlockMypageLocation,)
    verbose_name  = u'Blocks locations on "My page"'
    # template_name = 'creme_config/templatetags/block_blockmypagelocations.html'
    template_name = 'creme_config/bricks/bricklocations-mypage-user.html'

    def detailview_display(self, context):
        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    BlockMypageLocation.objects.filter(user=context['user']),
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        ))


class RelationBlocksConfigBrick(_ConfigAdminBrick):
    id_           = _ConfigAdminBrick.generate_id('creme_config', 'relation_blocks_config')
    # BlockDetailviewLocation because they can be deleted if we delete a RelationBlockItem
    dependencies  = (RelationBlockItem, BlockDetailviewLocation)
    verbose_name  = u'Relation blocks configuration'
    # template_name = 'creme_config/templatetags/block_relationblocksconfig.html'
    template_name = 'creme_config/bricks/relationbricks-configs.html'

    def detailview_display(self, context):
        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context, RelationBlockItem.objects.all(),
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        ))


class InstanceBlocksConfigBrick(_ConfigAdminBrick):
    id_           = _ConfigAdminBrick.generate_id('creme_config', 'instance_blocks_config')
    # BlockDetailviewLocation because they can be deleted if we delete a InstanceBlockConfigItem
    dependencies  = (InstanceBlockConfigItem, BlockDetailviewLocation)
    verbose_name  = u'Instance blocks configuration'
    # template_name = 'creme_config/templatetags/block_instanceblocksconfig.html'
    template_name = 'creme_config/bricks/instancebricks-configs.html'

    def detailview_display(self, context):
        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context, InstanceBlockConfigItem.objects.all(),
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        ))


# class CustomBlocksConfigBlock(_ConfigAdminBlock):
class CustomBlocksConfigBrick(PaginatedBrick):
    id_           = _ConfigAdminBrick.generate_id('creme_config', 'custom_blocks_config')
    dependencies  = (CustomBlockConfigItem,)
    verbose_name  = u'Custom blocks configuration'
    # template_name = 'creme_config/templatetags/block_customblocksconfig.html'
    template_name = 'creme_config/bricks/custombricks-configs.html'
    page_size    = _PAGE_SIZE
    permission   = None  # The portals can be viewed by all users => reloading can be done by all uers too.
    configurable = False

    def detailview_display(self, context):
        # NB: we wrap the ContentType instances instead of store extra data in
        #     them because teh instances are stored in a global cache, so we do
        #     not want to mutate them.
        class _ContentTypeWrapper(object):  # TODO: move from here ?
            __slots__ = ('ctype', 'items')

            def __init__(self, ctype, items):
                self.ctype = ctype
                self.items = items

        cbi_per_ctid = defaultdict(list)

        for cb_item in CustomBlockConfigItem.objects.order_by('name'):
            cbi_per_ctid[cb_item.content_type_id].append(cb_item)

        get_ct = ContentType.objects.get_for_id
        ctypes = [_ContentTypeWrapper(get_ct(ct_id), cb_items)
                      for ct_id, cb_items in cbi_per_ctid.iteritems()
                 ]

        sort_key = collator.sort_key
        ctypes.sort(key=lambda ctw: sort_key(unicode(ctw.ctype)))

        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                context, ctypes,
                # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        ))


class ButtonMenuBrick(Brick):
    id_           = Brick.generate_id('creme_config', 'button_menu')
    dependencies  = (ButtonMenuItem,)
    verbose_name  = u'Button menu configuration'
    # template_name = 'creme_config/templatetags/block_button_menu.html'
    template_name = 'creme_config/bricks/button-menu.html'
    permission    = None  # NB: used by the view creme_core.views.blocks.reload_basic()
    configurable  = False

    def detailview_display(self, context):
        buttons_map = defaultdict(list)

        for bmi in ButtonMenuItem.objects.order_by('order'):
            buttons_map[bmi.content_type_id].append(bmi)

        build_verbose_names = lambda bm_items: [unicode(bmi) for bmi in bm_items if bmi.button_id]
        default_buttons = build_verbose_names(buttons_map.pop(None, ()))

        get_ct = ContentType.objects.get_for_id
        buttons = [(get_ct(ct_id), build_verbose_names(bm_items))
                        for ct_id, bm_items in buttons_map.iteritems()
                  ]
        sort_key = collator.sort_key
        buttons.sort(key=lambda t: sort_key(unicode(t[0])))

        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    default_buttons=default_buttons,
                    buttons=buttons,
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        ))


class SearchConfigBrick(PaginatedBrick):
    id_           = PaginatedBrick.generate_id('creme_config', 'searchconfig')
    dependencies  = (SearchConfigItem,)
    verbose_name  = u'Search configuration'
    # template_name = 'creme_config/templatetags/block_searchconfig.html'
    template_name = 'creme_config/bricks/search-config.html'
    order_by      = 'content_type'
    # TODO _ConfigAdminBlock => Mixin
    page_size    = _PAGE_SIZE * 2  # Only one block
    permission   = None  # NB: used by the view creme_core.views.blocks.reload_basic()
    configurable = False

    def detailview_display(self, context):
        # NB: we wrap the ContentType instances instead of store extra data in
        #     them because teh instances are stored in a global cache, so we do
        #     not want to mutate them.
        class _ContentTypeWrapper(object): # TODO: move from here ?
            __slots__ = ('ctype', 'sc_items')

            def __init__(self, ctype):
                self.ctype = ctype
                self.sc_items = ()

        ctypes = [_ContentTypeWrapper(ctype) for ctype in creme_entity_content_types()]
        sort_key = collator.sort_key
        ctypes.sort(key=lambda ctw: sort_key(unicode(ctw.ctype)))

        # btc = self.get_block_template_context(
        btc = self.get_template_context(
                context, ctypes,
                # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
                # NB: '+ 2' is for default config + super-users config.
                max_conf_count=UserRole.objects.count() + 2,
        )

        ctypes_wrappers = btc['page'].object_list

        sci_map = defaultdict(list)
        for sci in SearchConfigItem.objects \
                                   .filter(content_type__in=[ctw.ctype for ctw in ctypes_wrappers])\
                                   .select_related('role'):
            sci_map[sci.content_type_id].append(sci)

        superusers_label = ugettext(u'Superuser')

        for ctw in ctypes_wrappers:
            ctype = ctw.ctype
            ctw.sc_items = sc_items = sci_map.get(ctype.id) or []
            sc_items.sort(key=lambda sci: sort_key(unicode(sci.role) if sci.role
                                                   else superusers_label if sci.superuser
                                                   else ''
                                                  )
                         )

            if not sc_items or not sc_items[0].is_default:  # No default config -> we build it
                SearchConfigItem.objects.create(content_type=ctype)

        return self._render(btc)


class HistoryConfigBrick(_ConfigAdminBrick):
    id_           = _ConfigAdminBrick.generate_id('creme_config', 'historyconfig')
    dependencies  = (HistoryConfigItem,)
    verbose_name  = u'History configuration'
    # template_name = 'creme_config/templatetags/block_historyconfig.html'
    template_name = 'creme_config/bricks/history-config.html'

    def detailview_display(self, context):
        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context, HistoryConfigItem.objects.all(),
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        ))


class UserRolesBrick(_ConfigAdminBrick):
    id_           = _ConfigAdminBrick.generate_id('creme_config', 'user_roles')
    dependencies  = (UserRole,)
    order_by      = 'name'
    verbose_name  = u'User roles configuration'
    # template_name = 'creme_config/templatetags/block_user_roles.html'
    template_name = 'creme_config/bricks/user-roles.html'

    def detailview_display(self, context):
        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context, UserRole.objects.all(),
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        ))


class UserPreferredMenusBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('creme_config', 'user_prefered_menus')
    dependencies  = (PreferedMenuItem,)
    verbose_name  = u'My preferred menus'
    # template_name = 'creme_config/templatetags/block_user_prefered_menus.html'
    template_name = 'creme_config/bricks/preferred-menus.html'
    configurable  = False
    order_by      = 'order'
    permission    = None  # NB: used by the view creme_core.views.blocks.reload_basic ;
                          #     None means 'No special permission required'

    def detailview_display(self, context):
        # NB: credentials OK: user can only view his own settings
        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    PreferedMenuItem.objects.filter(user=context['user']),
                    page_size=self.page_size,
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        ))


class UserSettingValuesBrick(Brick):
    id_           = QuerysetBrick.generate_id('creme_config', 'user_setting_values')
    # dependencies  = (User,) ??
    verbose_name  = u'My setting values'
    template_name = 'creme_config//bricks/user-setting-values.html'
    configurable  = False
    permission    = None  # NB: used by the view creme_core.views.blocks.reload_basic ;
                          #     None means 'No special permission required'

    def detailview_display(self, context):
        # NB: credentials OK: user can only view his own settings
        settings = context['user'].settings
        sv_info_per_app = defaultdict(list)
        # get_app = creme_registry.get_app
        get_app_config = apps.get_app_config
        count = 0

        for skey in setting_key.user_setting_key_registry:
            if skey.hidden:
                continue

            info = {
                'description': skey.description,
                'key_id':      skey.id,
            }

            try:
                info['value'] = settings.as_html(skey)
            except KeyError:
                info['not_set'] = True

            sv_info_per_app[skey.app_label].append(info)
            count += 1

        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    # # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
                    values_per_app=[
                        # (get_app(app_label, silent_fail=True).verbose_name, svalues)
                        (get_app_config(app_label).verbose_name, svalues)
                            for app_label, svalues in sv_info_per_app.iteritems()
                    ],
                    count=count,
        ))
