# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2012-2018 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

from django.dispatch import Signal


# form_post_save = Signal(providing_args=['instance', 'created'])

pre_merge_related = Signal(providing_args=['other_entity'])
pre_replace_related = Signal(providing_args=['old_instance', 'new_instance'])

pre_uninstall_flush  = Signal(providing_args=['content_types', 'verbosity',
                                              'stdout_write', 'stderr_write', 'style',
                                             ],
                             )
post_uninstall_flush = Signal(providing_args=['content_types', 'verbosity',
                                              'stdout_write', 'stderr_write', 'style',
                                             ],
                             )
