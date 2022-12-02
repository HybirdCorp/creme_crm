################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2022  Hybird
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

from django.middleware.locale import LocaleMiddleware as OriginalMiddleware
from django.utils import translation


class LocaleMiddleware(OriginalMiddleware):
    def process_request(self, request):
        # NB: AnonymousUser has no language attribute
        language = getattr(request.user, 'language', '')

        if not language:
            super().process_request(request=request)

        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()
