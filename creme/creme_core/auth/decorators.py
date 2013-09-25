# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import user_passes_test


superuser_required = user_passes_test(lambda u: u.is_superuser)
admin_required = user_passes_test(lambda u: u.can_admin)
