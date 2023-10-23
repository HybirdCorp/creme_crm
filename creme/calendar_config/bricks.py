################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.bricks import QuerysetBrick

from .models import CalendarConfigItem


class CalendarConfigItemsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('activities', 'calendar_view_config')
    verbose_name = 'Calendar view configuration'
    dependencies = (CalendarConfigItem,)
    template_name = 'calendar_config/bricks/calendar-config.html'
    configurable = False

    def detailview_display(self, context):
        user = context['user']
        configs = CalendarConfigItem.objects.filter(
            role__isnull=False, superuser=False
        ).order_by('role__name')

        brick_context = self.get_template_context(
            context,
            configs,
            has_app_perm=user.has_perm('activities'),
        )

        page = brick_context['page']

        try:
            default = CalendarConfigItem.objects.get_default()
        except ConflictError as e:
            brick_context['error'] = e
            return self._render(brick_context)

        if page.number < 2:
            superuser = CalendarConfigItem.objects.filter(role=None, superuser=True).first()

            brick_context['default'] = default
            brick_context['superuser'] = superuser

            # Little hack to force display of default & superuser even without any role
            # configuration
            paginator = page.paginator
            paginator.count += 2 if superuser else 1

        return self._render(brick_context)
