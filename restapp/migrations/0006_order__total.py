# Generated by Django 5.1.7 on 2025-04-13 14:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('restapp', '0005_alter_order_table'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='_total',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
