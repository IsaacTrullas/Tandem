# Tandem Local 0.5

Aplicación de Windows para conservar y consultar el histórico de Tandem. Base principal: `C:\Repositorios\Tandem\data\tandem.sqlite`, esquema 6.

## Abrir y actualizar

Ejecutar `scripts\AbrirAplicacion.ps1` desde PowerShell, o `scripts\Tandem.ps1 app`.

1. **Configurar acceso** abre un formulario local. El correo y la contraseña se guardan en el Administrador de credenciales de Windows bajo `TandemLocal:EU`, para el usuario actual. No se guardan en Git, SQLite, logs o archivos de configuración. No introducirlos en el chat. La aplicación no accede a las contraseñas del navegador.
2. **Recopilar API** inicia sesión en Tandem EU y consulta las bombas vinculadas. La primera ejecución solicita todo el rango que el servidor declara disponible, en ventanas de hasta 28 días. Las siguientes reparan el primer hueco conocido y vuelven a consultar siete días de solapamiento. Las bombas sin datos disponibles se declaran en el resultado. Las fechas originales se conservan sin convertirlas a UTC.
3. **Importar CSV/PDF** incorpora un manifiesto de descargas con el formato de `PROTOCOLO_SINCRONIZACION.md`, ejecuta OCR/extracción, cruza fuentes, audita y crea copia. La descarga de estos archivos sigue realizándose desde la interfaz oficial; no está automatizada por este botón.
4. **Exportar para otro programa** crea JSON Lines completo del conjunto elegido. Incluye metadatos de formato, fuente, filtros, versión de esquema y un último registro `complete`. La exportación lee una instantánea coherente y nunca sobrescribe un archivo existente.

Las tareas se ejecutan en segundo plano y la ventana indica su estado. Se evita una segunda actualización simultánea entre instancias de esta aplicación/recopilador. No cerrar la aplicación durante una carga. Las herramientas antiguas de bajo nivel deben ejecutarse sin otra actualización en curso.

## Conservación y cruce

- `api_payloads`: cuerpo completo recibido, hash y tamaño. No incluye tokens ni cabeceras de autenticación.
- `api_receipts` y `api_runs`: petición, periodo, resultado y diagnóstico seguro. Una respuesta inválida permanece archivada; esa ventana no avanza.
- `api_windows`: ventanas recibidas y procesadas, incluidos resultados vacíos. Una ventana recibida no demuestra que el servidor conserve todos los sucesos de la bomba.
- `api_snapshots`: metadatos y ajustes completos de cada bomba. Son instantáneas de subida, no configuraciones históricas inferidas.
- `api_events` y `api_event_sources`: eventos y cambios de reloj, identidad de secuencia y posición en cada respuesta. Una misma secuencia con contenido distinto conserva todas las versiones. Sin secuencia se usa contenido y número de aparición; no demuestra identidad física entre exportaciones.
- `source_links`: coincidencias de API con CSV por bomba, hora y cantidad; diferencias explícitas; vínculos de contexto con páginas PDF del mismo día. Estos últimos no identifican un icono concreto. Los vínculos conservan sus identificadores mientras persiste la relación.

No se suman los registros de distintos formatos como dosis diferentes. Las cantidades CSV siguen disponibles; los valores gráficos mantienen su incertidumbre/revisión. El basal en U/h no se transforma en una dosis U sin una reconstrucción temporal adicional. Los eventos de bolo pueden representar fases o componentes del mismo bolo.

Se interpretan 68 códigos de evento conocidos; los demás quedan preservados como desconocidos. Los campos nuevos también se conservan. El catálogo `event_codes.json` incluye referencia, hashes y licencia de las definiciones de tconnectsync. El cliente de conexión es una implementación local independiente y no ejecuta la sincronización a Nightscout.

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

La conexión real requiere credenciales introducidas en la aplicación. Las pruebas sintéticas no prueban autenticación ni cobertura del histórico de esta cuenta. El estado inicial conserva el corte clínico del 27/10/2026; solo una recopilación real posterior permite ampliarlo. No hay tarea recurrente instalada. Las ejecuciones se lanzan desde la aplicación o CLI.

La API solicita todos los tipos que el servidor devuelve, sin filtro de códigos. No se afirma que equivalga a todos los datos que Tandem almacena internamente. Los CSV/PDF y sus evidencias siguen sirviendo para contraste y para información no expuesta por la API. Las fechas `estimatedDateTime` terminadas en Z se conservan como fuente sin tratarlas automáticamente como UTC real.
