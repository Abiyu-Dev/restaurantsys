# Generated by Django 5.1.7 on 2025-04-15 19:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('restapp', '0006_order__total'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='deliveryaddress',
            name='customer',
        ),
        migrations.AddField(
            model_name='deliveryaddress',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='deliveryaddress',
            name='order',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='delivery_address', to='restapp.order'),
        ),
    ]
