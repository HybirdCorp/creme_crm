# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.translation import ugettext as _

from creme.emails.utils import get_images_from_html, ImageFromHTMLError


def create_image_validation_error(filename):
    return ValidationError(_(u"The image «%s» no longer exists or isn't valid.") % filename)

def validate_images_in_html(html, user):
    try:
        images = get_images_from_html(html)
    except ImageFromHTMLError as e:
        raise create_image_validation_error(e.filename)

    for filename, (image, src) in images.iteritems():
        if image is None:
            raise create_image_validation_error(filename)

        try:
            user.has_perm_to_view_or_die(image)
        except PermissionDenied as pde:
            raise ValidationError(pde)

    return images
