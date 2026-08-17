# Calendarios LaLiga para Apple Calendar

Genera dos calendarios de suscripción actualizados una vez al día desde las páginas oficiales de LaLiga:

- Atlético de Madrid — LaLiga EA Sports
- CD Leganés — LaLiga Hypermotion

Los calendarios son independientes, pero pueden mostrarse juntos en Apple Calendar. Los títulos distinguen los partidos en casa (`🏠`) y fuera (`✈️`). Los encuentros sin hora confirmada aparecen como eventos de día completo y se actualizan sin duplicarse cuando LaLiga publica el horario.

## Calendarios publicados

Después de la primera ejecución correcta, los calendarios están disponibles en:

- `https://raw.githubusercontent.com/JavierMazarioPicazo/Laliga-calendar/main/docs/atletico-de-madrid.ics`
- `https://raw.githubusercontent.com/JavierMazarioPicazo/Laliga-calendar/main/docs/cd-leganes.ics`

GitHub Actions los actualiza diariamente. Los datos son públicos y no se guarda ninguna credencial de Apple.

## Suscripción desde iPhone o iPad

Para cada URL, abre **Calendario → Calendarios → Añadir calendario → Añadir calendario de suscripción**, pega la URL y guarda el calendario. Activa ambos calendarios para visualizarlos conjuntamente; cada uno puede tener un color diferente.

No importes el archivo descargándolo: utiliza **Añadir calendario de suscripción**, porque así recibirás las actualizaciones posteriores.

## Configuración

`config.json` permite cambiar:

- `duration_minutes`: duración del partido, inicialmente 120 minutos.
- `alerts_minutes_before`: avisos, inicialmente 24 horas y 2 horas antes.
- nombre y color sugerido de cada calendario.
- URLs oficiales consultadas.

## Ejecución local

```bash
python -m venv .venv
source .venv/bin/activate
python -m unittest discover -s tests -v
python generate_calendars.py
```

Los archivos resultantes se guardan en `docs/`.

## Consideraciones

- LaLiga no publica una API abierta documentada para este uso, por lo que el generador lee las tablas visibles de sus páginas oficiales.
- Si LaLiga cambia la estructura HTML, el proceso falla expresamente antes de publicar calendarios vacíos.
- GitHub enviará una notificación cuando falle la acción programada.
- Las fechas sin horario son provisionales. El calendario las marca como eventos de día completo y transparentes para que no bloqueen la agenda.
