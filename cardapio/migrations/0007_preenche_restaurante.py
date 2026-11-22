from django.db import migrations


def restaurante_padrao(apps, schema_editor):
    Restaurante = apps.get_model('core', 'Restaurante')
    restaurante, _ = Restaurante.objects.get_or_create(nome='Restaurante padrão')
    for nome_model in ('Categoria', 'Prato', 'Combo'):
        Model = apps.get_model('cardapio', nome_model)
        Model.objects.filter(restaurante__isnull=True).update(restaurante=restaurante)


class Migration(migrations.Migration):

    dependencies = [
        ('cardapio', '0006_restaurante_opcional'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(restaurante_padrao, migrations.RunPython.noop),
    ]