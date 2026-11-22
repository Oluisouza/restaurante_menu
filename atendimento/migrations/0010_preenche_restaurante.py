from django.db import migrations


def restaurante_padrao(apps, schema_editor):
    Restaurante = apps.get_model('core', 'Restaurante')
    restaurante, _ = Restaurante.objects.get_or_create(nome='Restaurante padrão')
    for nome_model in ('Mesa', 'Comanda'):
        Model = apps.get_model('atendimento', nome_model)
        Model.objects.filter(restaurante__isnull=True).update(restaurante=restaurante)


class Migration(migrations.Migration):

    dependencies = [
        ('atendimento', '0009_restaurante_opcional'),
        ('cardapio', '0007_preenche_restaurante'),
    ]

    operations = [
        migrations.RunPython(restaurante_padrao, migrations.RunPython.noop),
    ]