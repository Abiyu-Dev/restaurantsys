# Generated by Django 5.1.7 on 2025-04-17 11:24

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('restapp', '0010_alter_user_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='delivery_boy',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='delivery_orders', to=settings.AUTH_USER_MODEL),
        ),
    ]
