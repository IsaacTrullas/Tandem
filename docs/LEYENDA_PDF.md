# Desglose de la leyenda de Tandem Source

Catálogo de **33 elementos del cronograma diario y 3 de tendencia**. Se han cotejado las diez leyendas diarias y las nueve de tendencia presentes en el histórico descargado. El atlas usa solo los recortes de los símbolos; no incluye cabeceras de paciente.

[Abrir atlas visual](../data/legend/atlas_leyenda.png)

## Cómo leer este catálogo

Una forma, su color, su cantidad y su duración son dimensiones distintas. El catálogo no convierte los símbolos de referencia en eventos del paciente. Cada aparición requiere evidencia del gráfico, su posición y, para los valores exactos disponibles, contraste con el CSV.

La gota central de captura automática de glucemia puede coexistir con un marcador naranja, verde o rojo. Los tipos de bolo, métodos de suministro y anulación tampoco se suman como bolos independientes. Una banda de duración modifica un evento; no crea otro.

## Elementos y reglas

### Glucemia

| Clave / etiqueta literal | Símbolo | Dato y unidad | Lectura / límite |
|---|---|---|---|
| `bg_high` — Glucemia alta | círculo naranja | `glucose_readings`; mg/dL | Clasificar la forma/color en el gráfico y conservar su valor escrito o CSV sin duplicar el evento. |
| `bg_range` — Glucemia en rango | círculo verde | `glucose_readings`; mg/dL | Clasificar la forma/color en el gráfico y conservar su valor escrito o CSV sin duplicar el evento. |
| `bg_low` — Glucemia baja | círculo rojo | `glucose_readings`; mg/dL | Clasificar la forma/color en el gráfico y conservar su valor escrito o CSV sin duplicar el evento. |
| `bg_auto` — Glucemia capturada de forma automática | círculo gris con gota | `glucose_readings`; mg/dL | Detectar la forma central de la gota sin imponer el gris de la leyenda como rango. |

### MCG

| Clave / etiqueta literal | Símbolo | Dato y unidad | Lectura / límite |
|---|---|---|---|
| `cgm_high` — MCG alto | punto naranja | `visual_series`; mg/dL | Clasificar la forma/color en el gráfico y conservar su valor escrito o CSV sin duplicar el evento. |
| `cgm_range` — MCG en rango | punto verde | `visual_series`; mg/dL | Clasificar la forma/color en el gráfico y conservar su valor escrito o CSV sin duplicar el evento. |
| `cgm_low` — MCG bajo | punto rojo | `visual_series`; mg/dL | Clasificar la forma/color en el gráfico y conservar su valor escrito o CSV sin duplicar el evento. |
| `cgm_fill` — Relleno de MCG | círculo vacío; borde con el color del rango en el gráfico | `legend_symbol_hits`; mg/dL | La guía describe datos del sensor recuperados por la bomba. No se interpolan valores ni se inventa su hora de recepción. |

### Bolo

| Clave / etiqueta literal | Símbolo | Dato y unidad | Lectura / límite |
|---|---|---|---|
| `bolus_food` — Posprandial | gota azul clara | `boluses`; U | Clasificar la forma/color en el gráfico y conservar su valor escrito o CSV sin duplicar el evento. |
| `bolus_correction` — Corrección | gota azul oscura | `boluses`; U | Clasificar la forma/color en el gráfico y conservar su valor escrito o CSV sin duplicar el evento. |
| `bolus_combined` — Posprandial + corrección | gota azul clara y oscura | `boluses`; U | Clasificar la forma/color en el gráfico y conservar su valor escrito o CSV sin duplicar el evento. |
| `bolus_extended` — Extendido | barra azul clara | `extended_bolus_spans` + `boluses`; U y minutos | Asociar ambos extremos de la barra al intervalo CSV; unir fragmentos ocultos por símbolos y cortar por medianoche sin crear otro bolo. Cantidades y horas exactas proceden del CSV. |
| `bolus_override_up` — Anular aumento | gota oliva con flecha arriba | `legend_symbol_hits`; U | El CSV Anular no permite resolver por sí solo la flecha hacia arriba. |
| `bolus_override_down` — Anular disminución | gota oliva con flecha abajo | `legend_symbol_hits`; U | El CSV Anular no permite resolver por sí solo la flecha hacia abajo. |
| `bolus_quick` — Rápido | gota azul rayada | `legend_symbol_hits`; U | Clasificar la forma/color en el gráfico y conservar su valor escrito o CSV sin duplicar el evento. |
| `bolus_auto` — Automático | gota azul con rombo blanco | `boluses`; U | Clasificar la forma/color en el gráfico y conservar su valor escrito o CSV sin duplicar el evento. |

### Basal

| Clave / etiqueta literal | Símbolo | Dato y unidad | Lectura / límite |
|---|---|---|---|
| `basal_delivered` — Perfil suministrado | área azul | `quantitative_layers`; U/h | Extraer el área visible bajo el escalón del perfil. Puede quedar cubierta por las barras: no sumarla como otra dosis ni asumir suministro real donde la capa esté oculta. |
| `basal_setting` — Configuración del perfil | línea azul con tasa | `quantitative_layers`, `basal_rate_annotations`; U/h | Separar la línea continua oscura y sus etiquetas. Conservar aparte las anotaciones sin un escalón asociado, sin asignarles una hora de evento. |
| `basal_temporary` — Temporal | área naranja con límite superior discontinuo | `quantitative_layers`; U/h | Exigir interior naranja y el patrón de borde fuente: superior de trazos y laterales/base continuos. Conservar como ambiguos los interiores sin borde suficiente. |
| `basal_control_iq` — Control-IQ | barras azules de altura variable | `quantitative_layers`; U/h | Separar los bordes superiores azul brillante del escalón oscuro; calibrar su altura con la escala del mismo gráfico y conservar margen de error. |
| `basal_zero` — 0 unidades/hora | línea roja continua | `legend_symbol_hits`; U/h | Línea continua de tasa cero; no prueba desconexión física. |
| `basal_zero_temp` — 0 unidades/hora temp. | línea azul discontinua | `legend_symbol_hits`; U/h | Línea azul de trazos en el eje cero; exigir repetición de trazos. |
| `basal_auto_suspend` — Suspensión automática | hachurado rojo | `state_intervals`; U/h | Hachurado rojo; distinto de línea de tasa cero y de parada manual. |

### Evento

| Clave / etiqueta literal | Símbolo | Dato y unidad | Lectura / límite |
|---|---|---|---|
| `carbs` — Carbohidratos (g) | manzana y número | `carbohydrate_entries`; g | Manzana y gramos; ni nombre de alimento ni hora real de comida inferidos. |
| `sleep` — Sueño | nube Zzz | `state_intervals`; sin unidad numérica propia | Clasificar la forma/color en el gráfico y conservar su valor escrito o CSV sin duplicar el evento. |
| `exercise` — Ejercicio | persona corriendo | `state_intervals`; sin unidad numérica propia | Clasificar la forma/color en el gráfico y conservar su valor escrito o CSV sin duplicar el evento. |
| `cartridge` — Cambio de cartucho o sitio | círculo con flecha | `chart_observations`; sin unidad numérica propia | Clasificar la forma/color en el gráfico y conservar su valor escrito o CSV sin duplicar el evento. |
| `event_duration` — Duración del evento | banda gris con límite vertical | `state_intervals`; min | Identificar símbolo asociado y límites; conservar solapamientos ambiguos. |
| `cgm_lost` — Conexión MCG perdida | hachurado gris | `state_intervals`; min | Patrón diagonal gris de comunicación MCG, distinto de bomba desconectada. |
| `cgm_alert` — Alerta de MCG | triángulo con exclamación | `report_text_events`; sin unidad numérica propia | Triángulo; preferir la hora y descripción escritas si están disponibles. |
| `pump_alarm` — Alarma de la bomba | círculo con exclamación | `report_text_events`; sin unidad numérica propia | Círculo con exclamación; separado de las alertas MCG. |
| `manual_stop` — Detener de forma manual | círculo con cuadrado | `chart_observations`; sin unidad numérica propia | Círculo con cuadrado; no equivale automáticamente a suspensión automática. |
| `power_off` — Apagado | círculo con símbolo de encendido | `chart_observations`; sin unidad numérica propia | Símbolo de apagado; que aparezca en la leyenda no demuestra un apagado en el historial. |

### Tendencia

| Clave / etiqueta literal | Símbolo | Dato y unidad | Lectura / límite |
|---|---|---|---|
| `percentile_50` — 50 % medio | línea gris continua | `visual_series`; mg/dL | Digitalizar el agregado del periodo con margen; no son muestras nuevas del sensor. |
| `percentiles_25_75` — 25/75 % | banda gris | `visual_series`; mg/dL | Digitalizar el agregado del periodo con margen; no son muestras nuevas del sensor. |
| `percentiles_10_90` — 10/90 % | líneas grises de puntos | `visual_series`; mg/dL | Digitalizar el agregado del periodo con margen; no son muestras nuevas del sensor. |

## Estado real de extracción

El **catálogo fuente está completo**: 330 ejemplos diarios y 27 de tendencia. Se guardan etiquetas, cajas, PNG, paletas y hash por documento. La tercera etiqueta de tendencia fue leída por OCR como `10190` en algunos informes: solo se admite como `10/90` al comprobar también el símbolo de puntos contra una referencia correcta; el OCR original se conserva.

Los detectores generan candidatos revisables para marcadores de glucemia, relleno MCG, tipos de bolo, flechas de anulación, carbohidratos, líneas de cero y símbolos/estados ya registrados. Los rechazos automáticos se conservan con motivo. Los campos CSV exactos siguen siendo la referencia para dosis, gramos y tiempos cuando esa información existe.

Las cinco reglas antes parciales ya tienen extracción específica: línea/etiquetas del perfil, área visible del perfil, barras variables, región temporal con borde contrastado y bolo extendido con coincidencia de extremos CSV. Esto significa reglas implementadas con candidatos cuantificados, **no validación clínica completa de cada punto**.

Se han calibrado los **230 gráficos con trazas**. El gráfico restante es un panel vacío separado por cambio de reloj. Las capas conservan unidades, posición, método y error. Las etiquetas coherentes con el eje conservan el valor OCR; las alturas digitalizadas tienen su margen. Cuando el OCR solo lee una marca de escala, se exige el cero dibujado y la validación adicional contra las etiquetas del perfil.

Los **cuatro bolos extendidos** están asociados a **cinco tramos gráficos**, porque uno cruza medianoche. No son cinco bolos ni se suman otra vez sus cantidades. La regla de basal temporal ha sido contrastada también con el símbolo original del PDF; su límite superior es discontinuo y los otros lados son continuos. No se han identificado regiones temporales válidas en estos gráficos: es un resultado del detector, no una garantía de ausencia.

## Reglas de asociación

- Color del marcador y captura automática se registran como atributos compatibles.
- Distinguir mg/dL, gramos, U y U/h. No convertir la dosis de una fila basal CSV en tasa sin una regla de tiempo documentada.
- Las coincidencias de plantilla y ventanas gráficas son candidatos, no identidades físicas verificadas.
- La cantidad procede del texto adyacente o del CSV, nunca del tamaño del icono.
- La hora escrita y el tiempo estimado de un eje conservan métodos y precisión distintos.
- No unir paneles a través de cambios de reloj ni inventar finales de eventos ocultos.
- Ni basal cero, ni suspensión, ni pérdida MCG confirman por sí solas desconexión física.
- No sumar como eventos separados el símbolo, la anotación, el CSV y el resumen que describen el mismo hecho.

## Consultas y verificación

```powershell
.\scripts\Tandem.ps1 legend --scan --atlas data\legend\atlas_leyenda.png
.\scripts\Tandem.ps1 export-symbol 123 data\revision\simbolo_123.png
.\scripts\Tandem.ps1 review legend_symbol_hits 123 --decision accepted --reviewer Nombre --note "Contraste con símbolo, cantidad y eje del informe"
```

```sql
SELECT * FROM v_legend_coverage;
SELECT * FROM legend_page_audits WHERE status != 'complete';
SELECT definition_key, review_status, COUNT(*) FROM legend_symbol_hits GROUP BY 1,2;
SELECT * FROM legend_definitions WHERE json_extract(rule_json,'$.implementation_state') LIKE 'partial%';
```

La auditoría distingue catálogo completo, pasada de candidatos y adaptadores semánticos parciales. Una leyenda nueva o incompleta debe detener la afirmación de cobertura. El corte de los datos continúa en los archivos del 27/10/2026.

La fase cuantitativa añade controles de gráficos pendientes, ejes sin calibrar, incompatibilidades entre etiquetas y eje, y bolos/tramos extendidos sin asociar. Las ambigüedades concretas, los símbolos solapados y los valores sin revisión siguen explícitos. No convertir una regla implementada en la afirmación de que todos los eventos estén verificados.

```sql
SELECT q.definition_key, i.local_date, count(*) capas
FROM quantitative_layers q JOIN report_images i ON i.id=q.image_id
GROUP BY 1,2;
SELECT p.*, i.local_date FROM v_basal_plot_points p
JOIN report_images i ON i.id=p.image_id WHERE i.local_date='2026-09-29';
SELECT bolus_record_id, count(*) tramos FROM extended_bolus_spans GROUP BY 1;
SELECT * FROM basal_rate_annotations WHERE association != 'step_label';
```

## Contraste con el fabricante

La [guía oficial de Tandem Source en español](https://www.tandemdiabetes.com/docs/default-source/user-guide/user-guide-tandem-source-professional-es-es-aw1013410.pdf?sfvrsn=d37dd8d7_4), páginas impresas 13–14, respalda el significado de bolos, basal y eventos. El icono de cartucho puede agrupar cambio, llenado de tubo o de cánula: no fija el subtipo. Los símbolos de sueño/ejercicio indican modo habilitado; la guía también describe lecturas MCG recuperadas y bordes según rango. Esos significados no justifican inferir eventos adicionales.

La copia íntegra de esta guía está archivada como documentación del fabricante (`application/pdf_reference`), separada del histórico del paciente. Los informes del paciente siguen siendo la referencia de sus datos concretos. La guía indica que algunos eventos ofrecen más detalles al pasar el cursor en la web; ese detalle necesita captura autenticada y todavía no está incorporado desde una nueva sesión.
