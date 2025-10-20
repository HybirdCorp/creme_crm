################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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

from django.contrib.auth import get_user_model

from creme.creme_core import models as core_models


class AdminHistoryExplainer:
    template_name = ''

    def __init__(self, *,
                 hline,
                 user,
                 # prefetcher: PreFetcher,
                 ):
        self.hline = hline
        self.user = user
        # self._prefetcher = prefetcher

    def get_context(self):
        return {
            'template_name': self.template_name,
            'hline': self.hline,
            'user': self.user,
        }


class EmptyExplainer(AdminHistoryExplainer):
    template_name = 'creme_config/history/empty.html'


class CremeUserHistoryExplainer(AdminHistoryExplainer):
    template_name = 'creme_config/history/user.html'


class PropertyTypeHistoryExplainer(AdminHistoryExplainer):
    # template_name = 'creme_config/history/property-type.html'
    pass


# Registry ---------------------------------------------------------------------
# TODO: use <PreFetcher()>?
# TODO: docstring
# TODO: typing
class AdminHistoryRegistry:
    def __init__(self):
        self._explainer_classes = {}

    def explainers(self, hlines, user):
        get_cls = self._explainer_classes.get
        return [
            get_cls(hline.content_type.model_class(), EmptyExplainer)(hline=hline, user=user)
            for hline in hlines
        ]

    def register(self, model, explainer):
        # TODO: errors
        self._explainer_classes[model] = explainer
        return self


admin_history_registry = AdminHistoryRegistry().register(
    model=get_user_model(), explainer=CremeUserHistoryExplainer,
).register(
    model=core_models.CremePropertyType, explainer=PropertyTypeHistoryExplainer,
)  # TODO: complete
