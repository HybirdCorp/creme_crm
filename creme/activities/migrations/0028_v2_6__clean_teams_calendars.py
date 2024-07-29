from collections import defaultdict

from django.db import migrations


def clean_calendars(apps, schema_editor):
    calendars = defaultdict(list)

    for calendar in apps.get_model('activities', 'Calendar').objects.filter(user__is_team=True):
        calendars[calendar.user_id].append(calendar)

    for team_calendars in calendars.values():
        for calendar in team_calendars:
            if calendar.is_default:
                if not calendar.is_public:
                    calendar.is_public = True
                    calendar.save()
            else:
                calendar.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0027_v2_6__settingvalue_json'),
    ]

    operations = [
        migrations.RunPython(clean_calendars),
    ]
