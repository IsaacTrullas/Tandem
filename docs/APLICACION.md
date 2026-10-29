# Tandem Local 0.8 · Qt

Aplicación de Windows con interfaz Qt 6 (PySide6) para conservar y consultar el histórico de Tandem. Base principal: `C:\Repositorios\Tandem\data\tandem.sqlite`, esquema 7.

## Abrir y actualizar

Ejecutar `scripts\AbrirAplicacion.ps1` desde PowerShell, o `scripts\Tandem.ps1 app`.

1. **Configurar acceso** abre un formulario local. El correo y la contraseña se guardan en el Administrador de credenciales de Windows bajo `TandemLocal:EU`, para el usuario actual. No se guardan en Git, SQLite, logs o archivos de configuración. No introducirlos en el chat. La aplicación no accede a las contraseñas del navegador.
2. **Recopilar API** inicia sesión en Tandem EU y consulta las bombas vinculadas. La primera ejecución solicita todo el rango que el servidor declara disponible, en ventanas de hasta 28 días. Las siguientes reparan el primer hueco conocido y vuelven a consultar siete días de solapamiento. Las bombas sin datos disponibles se declaran en el resultado. Las fechas originales se conservan sin convertirlas a UTC.
3. **Importar CSV/PDF** incorpora un manifiesto de descargas con el formato de `PROTOCOLO_SINCRONIZACION.md`, ejecuta OCR/extracción, cruza fuentes, audita y crea copia. La descarga de estos archivos sigue realizándose desde la interfaz oficial; no está automatizada por este botón.
4. **Exportar para otro programa** crea JSON Lines completo del conjunto elegido. Incluye metadatos de formato, fuente, filtros, versión de esquema y un último registro `complete`. La exportación lee una instantánea coherente y nunca sobrescribe un archivo existente.

Las pestañas **Resumen**, **Datos y exportación** y **Ejecuciones** muestran el estado, los registros paginados y los últimos intentos. En **Datos y exportación**, seleccionar una fuente, introducir fechas opcionales y pulsar **Ver datos**. **Anterior/Siguiente** recorre páginas de 100 filas; **Exportar JSONL** exporta todos los registros de la selección, no solo la página visible.

Las tareas se ejecutan en hilos Qt y la ventana indica su estado. Se evita una segunda actualización simultánea entre instancias de esta aplicación/recopilador. No cerrar la aplicación durante una carga. Las herramientas antiguas de bajo nivel deben ejecutarse sin otra actualización en curso.

## Conservación y cruce

- `api_payloads`: cuerpo completo recibido, hash y tamaño. No incluye tokens ni cabeceras de autenticación.
- `api_receipts` y `api_runs`: petición, periodo, resultado y diagnóstico seguro. Una respuesta inválida permanece archivada; esa ventana no avanza.
- `api_windows`: ventanas recibidas y procesadas, incluidos resultados vacíos. Una ventana recibida no demuestra que el servidor conserve todos los sucesos de la bomba.
- `api_snapshots`: metadatos y ajustes completos de cada bomba. Son instantáneas de subida, no configuraciones históricas inferidas.
- `api_events` y `api_event_sources`: eventos y cambios de reloj, identidad de secuencia y posición en cada respuesta. Una misma secuencia con contenido distinto conserva todas las versiones. Sin secuencia se usa contenido y número de aparición; no demuestra identidad física entre exportaciones.
- `source_links`: coincidencias de API con CSV por bomba, hora y cantidad; diferencias explícitas; vínculos de contexto con páginas PDF del mismo día. Estos últimos no identifican un icono concreto. Los vínculos conservan sus identificadores mientras persiste la relación.

No se suman los registros de distintos formatos como dosis diferentes. Las cantidades CSV siguen disponibles; los valores gráficos mantienen su incertidumbre/revisión. El basal en U/h no se transforma en una dosis U sin una reconstrucción temporal adicional. Los eventos de bolo pueden representar fases o componentes del mismo bolo.

El catálogo interpreta o clasifica 74 códigos de evento conocidos; los demás quedan preservados como desconocidos. Los campos nuevos también se conservan. El catálogo `event_codes.json` incluye referencia, hashes y licencia de las definiciones de tconnectsync. El cliente de conexión es una implementación local independiente y no ejecuta la sincronización a Nightscout.

## Uso desde programas

```python
from tandem.reader import Reader

with Reader(r'C:\Repositorios\Tandem\data\tandem.sqlite') as db:
    disponibles = db.datasets()
    glucosa = db.rows('glucose', since='2026-10-01', until='2026-10-28', limit=1000)
    eventos = db.rows('api_events', since='2026-10-01', limit=1000, offset=0)
    db.export_jsonl('api_events', r'C:\ruta\eventos.jsonl')
```

`rows` devuelve una página; usar `offset` para continuar o `export_jsonl` para el conjunto completo en una instantánea. El SDK abre SQLite en modo de solo lectura. Admite glucosa, bolos, carbohidratos, estados, basal CSV, perfiles, curvas PDF, metadatos, eventos API y relaciones. `records` conserva las claves para unir `basal_doses` y `basal_hourly` a su fecha y bomba. `values_json` conserva propiedades y medidas de cada evento.

También es posible abrir SQLite directamente en modo de lectura desde cualquier lenguaje. Consultar `MODELO_DATOS.md` para unidades y procedencia. La base no tiene cifrado propio; la protección de credenciales de Windows no cifra los datos clínicos exportados.

```powershell
.\scripts\Tandem.ps1 collect
.\scripts\Tandem.ps1 collect --since 2026-03-01 --until 2026-10-28
.\scripts\Tandem.ps1 export-data glucose data\glucosa.jsonl --since 2026-10-01
.\scripts\Tandem.ps1 audit --output data\auditorias\actual.json
```

## Estado y límites

Conector basado en los endpoints EU investigados en https://github.com/jwoglom/tconnectsync. API no documentada oficialmente: puede cambiar. No realiza modificaciones de terapia, cuenta, conexiones o consentimientos. Las únicas peticiones POST son inicio de sesión e intercambio de código OAuth. Tokens/cookies solo en memoria. Si el acceso exige otra interacción, se detiene y registra el fallo.

La conexión EU real se verificó el 29/10/2026 tras guardar el acceso corregido en la aplicación. Se recopilaron 401.411 eventos. Los CSV/PDF mantienen su corte del 27/10 y la API llega hasta 29/10/2026 08:05:36 según el reloj fuente. No hay tarea recurrente instalada. Las ejecuciones se lanzan desde la aplicación o CLI.

La API solicita todos los tipos que el servidor devuelve, sin filtro de códigos. No se afirma que equivalga a todos los datos que Tandem almacena internamente. Los CSV/PDF y sus evidencias siguen sirviendo para contraste y para información no expuesta por la API. Las fechas `estimatedDateTime` terminadas en Z se conservan como fuente sin tratarlas automáticamente como UTC real.

### Comprobación real de conexión

Acceso EU operativo. HTTPS validado con el almacén de certificados de Windows; no se desactiva TLS. La ejecución 8 terminó completa, incluida una repetición incremental con cero eventos nuevos. Se verificaron 403.641 posiciones de las respuestas originales contra su ordinal, registro y hash, sin discrepancias (antes de la repetición incremental). Toda la ventana de fechas declarada por el servidor está consultada; no equivale a garantizar continuidad intradía.

El catálogo tiene 74 códigos. Quedan 36.042 eventos de códigos 9,22,23,52 sin interpretar; sus propiedades están conservadas. Existen 96 pruebas sintéticas correctas. Se corrigieron índices de auditoría y cruce para evitar consultas cuadráticas con este volumen.

`api_measurements` expone la hora de medición de glucosa separada de la hora de registro de la bomba. `api_state_transitions` expone inicios/finales observados de sueño, ejercicio y suspensión, sin inventar duración cuando falta un extremo. Son 20 conjuntos accesibles por el SDK. El cruce exacto confirmó las 64.703 lecturas MCG y 1.382 entradas de glucosa de los CSV. No fusiona filas fuente ni duplica dosis.

### Migración de la interfaz a Qt

Versión 0.6: toda la interfaz, incluido el formulario de acceso con Mostrar contraseña, usa PySide6. El almacén de Windows sigue usando la misma identidad y no requiere volver a introducir las credenciales existentes. Sin migración de datos: el esquema sigue siendo 7. La importación se coordina desde `tandem/services.py`; el lector, el recopilador y los datos originales mantienen sus contratos. Validación: 114 pruebas correctas; revisión visual a 1180x820 y 940x700; consulta de las 98 mediciones API del 29/10/2026 desde la base real en modo de lectura.

## Gráfico temporal

La pestaña Gráfico incluye navegación por fechas, arrastre/zoom, cursor con valores de glucosa, IOB observada, bolos, carbohidratos y contexto de perfil. La carga se limita al tramo visible y su margen; no mantiene el histórico completo en memoria. Véase [VISUALIZADOR.md](VISUALIZADOR.md). Las consultas son de lectura y no alteran la base.

## Rediseño de usabilidad 0.8

La navegación lateral reúne Cronología, Archivo, Explorar datos y Descargas; se pliega en ventanas estrechas. La cronología incorpora un carril de modos rotulado con luna/corredor, leyenda exterior, pictogramas de mayor tamaño y un inspector compacto con unidades diferenciadas. Las fechas de observación continúan visibles. Ver [DISENO_GUI.md](DISENO_GUI.md). Actualizar datos conserva la ventana analizada; Más reciente vuelve explícitamente al último día. La presentación usa coma decimal; los valores fuente y las exportaciones mantienen su formato.
