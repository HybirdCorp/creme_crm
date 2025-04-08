################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2023-2025  Hybird
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

from django.contrib.auth import password_validation
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

# NB: we say "The password ..." instead of "Your password ..." (Django)
#     because it could be confusing when an administrator edit the
#     password of another user.


class MinimumLengthValidator(password_validation.MinimumLengthValidator):
    def get_help_text(self):
        return ngettext(
            'The password must contain at least %(min_length)d character.',
            'The password must contain at least %(min_length)d characters.',
            self.min_length,
        ) % {'min_length': self.min_length}


class UserAttributeSimilarityValidator(password_validation.UserAttributeSimilarityValidator):
    def get_help_text(self):
        return _(
            "The password can’t be too similar to the other personal information."
        )


class CommonPasswordValidator(password_validation.CommonPasswordValidator):
    def get_help_text(self):
        return _("The password can’t be a commonly used password.")


class NumericPasswordValidator(password_validation.NumericPasswordValidator):
    def get_help_text(self):
        return _("The password can’t be entirely numeric.")
