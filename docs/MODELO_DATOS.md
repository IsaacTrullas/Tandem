# Modelo de datos, versión 7 / aplicación 0.8 (Qt)

Todas las tablas y vistas se crean desde `tandem/schema.sql`. SQLite tiene claves foráneas activas y modo WAL. Los tiempos de ejecución son ISO 8601 UTC; los tiempos de tratamiento son texto original del reloj del dispositivo, con `utc_timestamp` nulo hasta una reconstrucción documentada.

| Tabla | Información y procedencia |
|---|---|
| `artifacts` | Archivo completo BLOB, SHA-256, tamaño, formato, primer periodo conocido, metadatos y estado. Incluye ZIP, cada CSV contenido, PDF y documentos de auditoría. |
| `artifact_locations`, `artifact_links` | Rutas observadas y relación ZIP → CSV. No se necesita que esas rutas sigan existiendo para recuperar el contenido. |
| `artifact_receipts` | Periodos solicitados y metadatos de cada recepción. Permite que el mismo contenido aparezca en consultas distintas. |
| `import_runs`, `sync_runs` | Ejecuciones, manifiestos, resultado, errores, fechas y copia previa. |
| `raw_rows` | Todas las filas de cada CSV, número original, campos originales JSON y hash. |
| `records`, `record_sources` | Campos tipados en JSON, clave de coincidencia, aparición y enlaces a todas las filas fuente. Segmentos de orden de reloj. |
| `glucose_readings` | Glucosa en mg/dL; distingue sensor de entrada en bomba. |
| `boluses` | Insulina total, parte de alimento/corrección/extendida, estados, inicio/fin extendido, gramos, objetivo, factor de corrección, I:C y demás campos CSV. El campo fuente `Tipo` se conserva en `records.values_json`. |
| `carbohydrate_entries` | Bolos con gramos positivos; nombre de alimento nulo; tiempo vinculado al final del bolo, no a una comida inferida. Los ceros permanecen en `boluses`. |
| `basal_doses` | Dosis prescrita, unidad tal como la declara el CSV. No se trata como tasa U/h ni se suma con el resumen horario. |
| `basal_hourly` | Una fila por hora de cada fila diaria CSV. Ausencia (`NULL`) diferente de cero. Días repetidos no se reducen a una sola fila por fecha. |
| `clock_observations` | Retrocesos observados en el orden fuente; son indicios, no una explicación automática del cambio de hora. |
| `pdf_pages` | Cada página, texto nativo, palabras y coordenadas PDF, número de imágenes, PNG a 150 ppp, OCR completo con posiciones, motor y estado. |
| `daily_panels` | Fecha OCR, caja del panel, cabecera y estadísticas legibles; puede haber continuaciones/días sin datos. |
| `pdf_facts` | Advertencias nativas y estadísticas OCR con texto de evidencia, unidad, método y estado. El resto del resumen/configuración se conserva íntegro en texto y PDF, aunque no todo tenga columnas específicas. |
| `therapy_events` | Candidatos de alarma/alerta con texto explícito, página, caja y asignación provisional al panel anterior. No se crean eventos a partir de la leyenda. |
| `profiles`, `profile_segments` | Ajustes de la última subida, fecha de esa instantánea, perfil activo, duración, basal, ratios y tramos. No se aplican retrospectivamente a todo el periodo del informe. |
| `quality_issues`, `review_log` | Incidencias históricas y decisiones humanas de revisión. |

## Vistas de consulta

- `v_glucose`: lecturas con fecha y origen.
- `v_boluses`: bolos con tiempo del registro.
- `v_carbohydrates`: gramos, procedencia y significado del tiempo.
- `v_daily_csv`: cobertura y suma de gramos CSV por fecha; no combina las dos fuentes de basal.
- `v_daily_context`: índice de paneles PDF para cruzar por día con los CSV. Conserva cada evidencia, sin sumar otra vez los gramos del PDF.
- `v_pending_review`: candidatos OCR pendientes.

## Coincidencias y versiones

SHA-256 identifica contenido de archivo. Para registros, la clave incluye todos los campos normalizados y el tipo. Un contador de aparición conserva repeticiones idénticas dentro del mismo archivo. Los solapamientos se vinculan a la misma combinación clave/aparición; cambios de valor quedan como registros distintos y no sustituyen la versión anterior.

Los CSV carecen de identificador universal del evento y de desplazamiento UTC. Una colisión por reloj repetido o una exportación corregida puede requerir comparación de `raw_rows` y `record_sources`. Las fuentes íntegras permiten hacer esa reconstrucción sin pérdida. No eliminar ni fusionar datos clínicos por fecha/hora solamente.

## Revisión del PDF

Las coordenadas nativas usan puntos PDF. Las de OCR y paneles usan píxeles de la imagen almacenada; `ocr_json` registra ancho, alto y ppp. Windows OCR no proporciona confianza numérica: no se fabrica una puntuación.

Los candidatos de fecha/estadística/alarma son `ocr_unreviewed`. El texto nativo se marca `source_text`, que señala el método de obtención, no una validación clínica. La ampliación reconoce símbolos y bandas con revisión pendiente y conserva los no resueltos. No asigna exactitud a coordenadas del gráfico ni interpreta la semejanza de plantilla como confianza clínica.

Para registrar una revisión del panel o evento tras contrastar su página:

```powershell
.\scripts\Tandem.ps1 review daily_panels 123 --decision accepted --reviewer 'Nombre' --note 'Fecha, cabecera y estadísticas contrastadas con la página original'
```

La revisión del panel no cambia por sí sola el estado de cada `pdf_facts` asociado. La revisión de `chart_observations` sí actualiza el intervalo derivado asociado. `review` acepta/rechaza evidencias; no sustituye valores fuente.

## Ampliación PDF

El [inventario de información](INVENTARIO_INFORMACION.md) describe las tablas nuevas y su alcance. `state_intervals` / `v_states` contienen tramos estimados, con margen, fecha del dispositivo y límites de día. `chart_observations` conserva símbolos puntuales, ventanas horarias, recortes y ambigüedades. `v_event_evidence` reúne las evidencias gráficas y las alertas nativas: varias evidencias pueden pertenecer al mismo evento, por lo que no se deben sumar como sucesos independientes.

Las coordenadas de observaciones y etiquetas usan píxeles de la imagen embebida en `report_images`, no los de la página OCR. `report_fields`, `native_text_blocks`, plantillas y trazados usan puntos PDF. `visual_series` declara su sistema de coordenadas: envolventes de píxeles o minutos/mg/dL estimados para percentiles. No son nuevas lecturas del sensor.

Los intervalos son `visual_unreviewed`. Una banda con varios modos es `ambiguous_multi_mode_duration`; lo demás no resuelto permanece `unclassified_*`. No fusionar intervalos a través de cambios de reloj. Los avisos nativos conservan la hora escrita; el año se resuelve en el periodo solicitado solo si es único.

Los ajustes y horarios son de la última subida. `sleep_schedules.is_actual_sleep=0`: el horario configurado no demuestra activación real. La pérdida de conexión MCG, parada, suspensión automática y apagado se mantienen separados. En los archivos revisados no se ha identificado evidencia que confirme por sí sola una desconexión física del catéter.

`extract-pdf --rebuild` reconstruye solo las tablas derivadas de este extractor; conserva originales, CSV, OCR y perfiles iniciales. Rechaza la operación si encuentra datos revisados en las tablas afectadas. Hacer backup antes.

## Leyenda completa

El [desglose de la leyenda](LEYENDA_PDF.md) documenta 33 elementos del cronograma y 3 de tendencia. `legend_definitions` guarda el contrato de lectura, unidades, dimensión, destino y límites; `legend_instances` conserva cada ejemplo fuente, su etiqueta, geometría, PNG y hash. `legend_page_audits` comprueba elementos esperados, faltantes y etiquetas nuevas en cada leyenda.

`legend_symbol_hits` contiene candidatos gráficos con alternativas de clase, ventana de posición, recorte y estado de revisión. `legend_feature_links` relaciona cada significado con evidencias CSV o PDF ya existentes: una relación no equivale a otro evento ni confirma una coincidencia física. El caso `direction_not_resolved_in_csv` relaciona ambos sentidos de Anular con un bolo cuya dirección aún no se conoce; no confirma ni aumento ni disminución.

`legend_chart_scans` registra la pasada sobre cada gráfico, y `v_legend_coverage` resume fuentes, candidatos y enlaces. `rule_json.implementation_state` distingue la implementación disponible. Las cinco reglas cuantitativas ya están implementadas; una pasada terminada sigue sin implicar validación clínica de todos sus candidatos.

Los candidatos refutados por una regla más precisa se conservan como `algorithm_rejected`, con motivo. No se cambian decisiones revisadas. La gota central de captura de glucemia automática es un atributo independiente del rango por color. Una manzana, un bolo CSV y sus gramos pueden ser evidencias del mismo evento; no deben sumarse tres veces.

## Extracción cuantitativa de capas

- `plot_calibrations`: eje cero, marcas leídas, escala U/h por píxel, margen, OCR específico y validación. No hay una escala universal fija: se lee la de cada gráfico.
- `quantitative_layers`: serie separada por significado de la leyenda, con caja, recorte, unidades y puntos `[x, minuto, y, valor, método]`. Perfil, línea de configuración y Control-IQ son capas visuales no aditivas; no representan nuevas dosis CSV. `v_basal_plot_points` permite consultar los puntos mediante JSON1.
- `basal_rate_annotations`: transcripción de cada tasa escrita a resolución embebida, caja y escalón asociado. Las anotaciones sin asociación conservan el texto y su posición gráfica, con tiempo de evento nulo.
- `extended_bolus_spans`: coincidencia única de los dos extremos gráficos con inicio/fin CSV, incluyendo fragmentos ocultos por iconos. Cada fila es una porción diaria de un bolo, no un bolo nuevo. `bolus_record_id` conserva la identidad; cantidad total, cantidad extendida y duración siguen procediendo del CSV.
- `quantitative_runs`: estado por gráfico y versión. Los paneles totalmente vacíos por cambio de reloj se registran explícitamente y no se rellenan con tasas.

Los valores de altura se conservan como estimaciones revisables. Las etiquetas OCR incompatibles con la escala no se propagan al perfil. Una región naranja necesita evidencia del borde de trazos; sin ella queda ambigua. La auditoría distingue implementación de la regla y datos gráficos efectivamente revisados.

## Fuente API y consumo

`api_schema.sql` añade respuestas originales, recibos, instantáneas, eventos versionados, procedencia por ordinal, ventanas y relaciones entre fuentes. Las vistas `v_api_events` y `v_source_links` y el SDK `tandem.reader.Reader` sirven a otros programas. Véase [APLICACION.md](APLICACION.md). Las versiones de evento no se reducen silenciosamente a una sola; `revision_count > 1` exige elegir o revisar una versión antes de agregaciones.

Las vistas `v_api_measurements` y `v_api_state_transitions` conservan, respectivamente, la hora de medición separada del ingreso al log y los cambios de estado explícitos. Las mediciones MCG usan el contador `egvTimeStamp` desde 2008 en reloj local sin inferir UTC. El valor original y el método permanecen en `values_json` y `raw_json`.

El visualizador consulta ventanas acotadas mediante `timeline_data.py` y `pump_context.py`, sin persistir ni sobrescribir reconstrucciones. La hora de cursor se expresa con un eje numérico de reloj local, no como UTC inferido. Parámetros y estados llevan su hora de observación y se invalidan ante cambios de perfil/reloj según evidencia.
