# Generated by Django 5.1 on 2025-01-19 16:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookingsystem', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='booking',
            name='total_passenger',
        ),
    ]
