# Generated by Django 4.2.3 on 2025-05-31 17:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('livability', '0003_category_alter_categoryfuzzycomparison_category1_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoryfuzzycomparison',
            name='consistency_ratio',
            field=models.FloatField(default=None, null=True),
        ),
    ]
