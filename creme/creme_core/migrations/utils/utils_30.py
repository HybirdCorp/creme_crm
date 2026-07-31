from datetime import datetime, timezone

from django.utils.timezone import make_aware

EPOCH = make_aware(datetime(year=1970, month=1, day=1), timezone=timezone.utc)
