# Generated by Django 5.0.7 on 2024-12-11 08:01

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookingsystem', '0015_auto_20241205_0029'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='room',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bookings', to='bookingsystem.room'),
        ),
        migrations.AlterField(
            model_name='booking',
            name='vehicle',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bookings', to='bookingsystem.vehicle'),
        ),
    ]