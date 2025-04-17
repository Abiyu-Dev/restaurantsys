# Generated by Django 5.1.7 on 2025-04-17 11:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('restapp', '0009_activitylog'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('manager', 'Manager'), ('server', 'Server'), ('chef', 'Chef'), ('cashier', 'Cashier'), ('customer', 'Customer'), ('deliveryboy', 'Delivery Boy')], default='customer', max_length=20),
        ),
    ]
