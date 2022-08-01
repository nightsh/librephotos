# Generated by Django 3.1.14 on 2022-01-24 17:11

from django.db import migrations, models

import api.models.user


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0017_add_cover_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="config_datetime_rules",
            field=models.JSONField(
                default=api.models.user.get_default_config_datetime_rules),
        ),
    ]
