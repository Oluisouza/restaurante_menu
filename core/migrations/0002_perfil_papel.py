from django.db import migrations, models


def perfis_existentes_viram_gerente(apps, schema_editor):
    """Quem já usava o sistema tinha acesso a tudo: continua com acesso a tudo."""
    Perfil = apps.get_model('core', 'Perfil')
    Perfil.objects.update(papel='gerente')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfil',
            name='papel',
            field=models.CharField(
                choices=[('gerente', 'Gerente'), ('atendente', 'Atendente')],
                default='atendente',
                max_length=20,
            ),
        ),
        migrations.RunPython(perfis_existentes_viram_gerente, migrations.RunPython.noop),
    ]