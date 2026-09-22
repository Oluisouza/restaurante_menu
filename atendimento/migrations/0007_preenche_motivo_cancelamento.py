from django.db import migrations


def preencher_motivo(apps, schema_editor):
    ItemComanda = apps.get_model('atendimento', 'ItemComanda')
    ItemComanda.objects.filter(
        status='CANCELADO', motivo_cancelamento=''
    ).update(motivo_cancelamento='Motivo não registrado (cancelamento anterior)')


class Migration(migrations.Migration):

    dependencies = [
        ('atendimento', '0006_itemcomanda_cancelado_em_and_more'),
    ]

    operations = [
        migrations.RunPython(preencher_motivo, migrations.RunPython.noop),
    ]