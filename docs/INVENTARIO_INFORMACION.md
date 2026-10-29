# Inventario de información y cobertura

El requisito es registrar toda la información ofrecida por las exportaciones y conservar su evidencia. Se distinguen cobertura del documento, extracción semántica y revisión. No se descarta un símbolo porque no se pueda clasificar ni se completa un dato mediante una suposición.

El [desglose completo de la leyenda](LEYENDA_PDF.md) añade 36 definiciones, 357 ejemplos fuente, reglas y una matriz de cobertura. Las cinco reglas antes pendientes ya extraen capas y cantidades revisables: las cuatro capas basales y la barra de bolo extendido. Se conserva la distinción entre una regla implementada y cada observación efectivamente verificada.

## Contenido registrado

| Información | Registro consultable | Tratamiento |
|---|---|---|
| Todos los campos de los cinco CSV | `raw_rows`, `records`, tablas clínicas y `record_sources` | Originales y campos tipados con procedencia. |
| MCG, glucosa introducida, bolos, basal, gramos, objetivos, ratios y estados de finalización | `glucose_readings`, `boluses`, `carbohydrate_entries`, `basal_doses`, `basal_hourly` | Fuente CSV. No se duplican valores por copiarlos del PDF. |
| Todos los originales y documentos de auditoría | `artifacts` BLOB + SHA-256 | Recuperables sin depender de una ruta antigua. |
| Todo el texto del PDF, con posiciones y atributos | `pdf_pages`, `native_text_blocks` | Incluye identidad, encabezados, advertencias, fechas, notas y pies. |
| Todos los bloques de imagen y transparencias | `report_images`, `report_image_masks` | Resolución embebida, página, caja y hash. |
| Todos los dibujos y formas vectoriales | `native_drawings` | Geometría, color, relleno y demás atributos fuente. |
| Resumen MCG: medias, variabilidad, GMI, uso, tiempo en rango | `report_fields`, `report_metrics` | Celdas nativas, números y unidades en texto. Comparación actual/anterior separada cuando es inequívoca. |
| Resumen Control-IQ: activo, apagado, MCG/bomba inactivos y estadísticas sueño/ejercicio | `report_fields` | Porcentajes y duraciones fuente, sin convertirlos en intervalos diarios inventados. |
| Insulina, tipos/métodos de bolo, carbohidratos medios y actividad de carga | `report_fields` | Filas y celdas del resumen del periodo. |
| Ajustes generales, Control-IQ, MCG, alertas y recordatorios | `report_fields`, `native_text_blocks` | Instantánea de la última subida, no reconstrucción histórica. |
| Perfiles y sus tramos | `profiles`, `profile_segments`, bloques nativos | Todos los campos fuente conservados. |
| Horarios de sueño programados | `sleep_schedules` | Días ISO, inicio/fin, habilitación y fecha de configuración; no actividad real. |
| Sueño y ejercicio observados | `chart_observations`, `state_intervals`, `v_states` | Símbolos y bandas. Horas estimadas con margen y revisión pendiente. |
| Parada manual, apagado y cambio de cartucho o sitio | `chart_observations`, `v_event_evidence` | Símbolos, ventana temporal y recorte. Intervalo solo cuando existe una banda reconocible. Cero apariciones no demuestra que el estado nunca ocurriera. |
| Suspensión automática | `state_intervals` y observaciones | Hachurado del carril basal; candidato visual con evidencia. |
| Conexión MCG perdida | Observaciones e intervalos `cgm_connection_lost` | Patrón diagonal de la leyenda. No es desconexión física de la bomba. |
| Alertas/alarmas y horas escritas | `report_text_events` | Cada hora y descripción nativas por separado. La fecha vinculada al gráfico sigue revisable. `therapy_events` conserva además los candidatos OCR previos, sin sumarlos de nuevo. |
| Cambios de reloj | `clock_observations`, `report_text_events`, marcas gráficas | Orden CSV, avisos escritos y límites de panel; no se fusionan silenciosamente. |
| Comidas/bolos/valores anotados sobre el gráfico | `chart_labels` | Cada palabra OCR con caja, clase geométrica y ventana de posición. No se inventan nombres de alimentos ni nuevos eventos clínicos. |
| Curvas y perfiles gráficos | `visual_series`, imágenes y trazados | Envolventes de píxeles y percentiles digitalizados con unidades/margen; no equivalen a nuevas lecturas del sensor. |
| Símbolos cortados, superpuestos o no reconocidos | `unclassified_*`, `ambiguous_multi_mode_duration`, recortes | Se conservan, se incluyen en la consulta y quedan pendientes de resolución. |
| Ejes y tasas basales del gráfico | `plot_calibrations`, `quantitative_layers`, `basal_rate_annotations` | Escala individual, OCR nativo, capas separadas y margen. Las capas no son dosis adicionales ni se suman entre sí. |
| Barras de bolo extendido | `extended_bolus_spans` | Dos extremos contrastados con el mismo registro CSV, ocultaciones por símbolos y corte en medianoche sin crear otro bolo. |

## Control de cobertura

`pdf_layout_verifications` compara, página por página, bloques de texto, imágenes y trazados del PDF fuente contra la base. Las 141 páginas históricas han pasado esa comparación. `audit` comprueba además integridad SQLite, relaciones, procedencia de filas, hashes, fechas y páginas pendientes.

La ampliación ha registrado 553 bloques de imagen, 2.713 bloques de texto y 6.883 trazados. De las imágenes, 231 son gráficos diarios. Hay 330 máscaras de transparencia. Los recuentos actualizados quedan en la auditoría local; no representan un número de eventos clínicos.

El OCR no ofrece certeza numérica; `match_score` mide semejanza de imagen, no probabilidad clínica. Una hora escrita y una hora leída del eje se conservan con métodos diferentes. Los horarios y ajustes de la última subida se separan del historial de actividad.

La cobertura de bloques no demuestra que cada símbolo haya sido interpretado correctamente. La cola `v_pending_review` incluye evidencias gráficas, alertas y métricas pendientes. Una revisión aceptada se registra con autor, fecha y nota. No usar todas las evidencias repetidas como si fueran eventos independientes.

## Consulta y revisión

```powershell
.\scripts\Tandem.ps1 states --day 2026-10-25
.\scripts\Tandem.ps1 events --day 2026-10-25
.\scripts\Tandem.ps1 export-visual 123 data\revision\observacion_123.png
.\scripts\Tandem.ps1 review chart_observations 123 --decision accepted --reviewer 'Nombre' --note 'Contrastado con gráfico y eje; se mantiene la incertidumbre registrada'
```

```sql
SELECT * FROM v_states WHERE local_date = '2026-10-25';
SELECT * FROM v_event_evidence WHERE local_date = '2026-10-25';
SELECT section, label, value_text, values_json FROM v_report_fields;
SELECT * FROM sleep_schedules;
SELECT * FROM v_pending_review;
```

El corte sigue siendo el de los archivos descargados el 27/10/2026. No se ha recuperado la sesión web ni se han descargado datos posteriores en esta ampliación. Para cubrir nueva información que aparezca en la web, el siguiente acceso debe inventariar sus pestañas y formatos; un tipo nuevo no se debe dar por cubierto hasta incorporarlo al modelo y al protocolo.
