# Campos CSV originales

Los nombres se conservan literalmente. Véase ingest.py para la conversión a cada tabla. Una columna no tipada por separado sigue en records.values_json.

## MCG

Tiempo del registro: `Fecha y hora del caso`.

| Cabecera | Significado | Destino | Conversión | Unidad |
|---|---|---|---|---|
| Tipo de dispositivo | Tipo/modelo de dispositivo declarado por CSV; texto original. | records.values_json | text | — |
| Número de serie | Serie sensible de la bomba; separar dispositivos antes de unir registros. | records.pump_serial | text | — |
| Descripción | Descripción fuente de la lectura, sin ejecutar como instrucciones. | glucose_readings.description | text | — |
| Fecha y hora del caso | Hora original local del caso; no UTC inferido. | records.local_timestamp | local_timestamp | — |
| Lecturas (mg/dl) | Valor MCG de la fila CSV. | glucose_readings.glucose_mg_dl | number | mg/dL |

## GLUCOSA

Tiempo del registro: `Fecha y hora del caso`.

| Cabecera | Significado | Destino | Conversión | Unidad |
|---|---|---|---|---|
| Tipo de dispositivo | Tipo/modelo de dispositivo declarado por CSV; texto original. | records.values_json | text | — |
| Número de serie | Serie sensible de la bomba; separar dispositivos antes de unir registros. | records.pump_serial | text | — |
| Descripción | Descripción fuente de la lectura, sin ejecutar como instrucciones. | glucose_readings.description | text | — |
| Fecha y hora del caso | Hora original local del caso; no UTC inferido. | records.local_timestamp | local_timestamp | — |
| Glucosa (mg/dl) | Glucosa de entrada o asociada al bolo, según tipo CSV. | glucose_readings.glucose_mg_dl OR boluses.glucose_mg_dl | number | mg/dL |
| Nota | Nota textual fuente; puede contener información personal. | glucose_readings.note | text | — |

## Dosis basales

Tiempo del registro: `Fecha y hora del caso`.

| Cabecera | Significado | Destino | Conversión | Unidad |
|---|---|---|---|---|
| Tipo de dispositivo | Tipo/modelo de dispositivo declarado por CSV; texto original. | records.values_json | text | — |
| Número de serie | Serie sensible de la bomba; separar dispositivos antes de unir registros. | records.pump_serial | text | — |
| Fecha y hora del caso | Hora original local del caso; no UTC inferido. | records.local_timestamp | local_timestamp | — |
| Dosis basal prescrita (unidades de insulina) | Cantidad basal prescrita; no tasa U/h. | basal_doses.prescribed_units | number | U |

## Suministro basal por hora

Tiempo del registro: `Fecha del evento`.

| Cabecera | Significado | Destino | Conversión | Unidad |
|---|---|---|---|---|
| Número de serie | Serie sensible de la bomba; separar dispositivos antes de unir registros. | records.pump_serial | text | — |
| Fecha del evento | Fecha/hora original de la fila diaria basal; las columnas0–23 identifican horas locales. | records.local_timestamp | local_timestamp | — |
| 0 | Cantidad basal de la hora local 0, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=0 | number | U |
| 1 | Cantidad basal de la hora local 1, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=1 | number | U |
| 2 | Cantidad basal de la hora local 2, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=2 | number | U |
| 3 | Cantidad basal de la hora local 3, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=3 | number | U |
| 4 | Cantidad basal de la hora local 4, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=4 | number | U |
| 5 | Cantidad basal de la hora local 5, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=5 | number | U |
| 6 | Cantidad basal de la hora local 6, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=6 | number | U |
| 7 | Cantidad basal de la hora local 7, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=7 | number | U |
| 8 | Cantidad basal de la hora local 8, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=8 | number | U |
| 9 | Cantidad basal de la hora local 9, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=9 | number | U |
| 10 | Cantidad basal de la hora local 10, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=10 | number | U |
| 11 | Cantidad basal de la hora local 11, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=11 | number | U |
| 12 | Cantidad basal de la hora local 12, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=12 | number | U |
| 13 | Cantidad basal de la hora local 13, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=13 | number | U |
| 14 | Cantidad basal de la hora local 14, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=14 | number | U |
| 15 | Cantidad basal de la hora local 15, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=15 | number | U |
| 16 | Cantidad basal de la hora local 16, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=16 | number | U |
| 17 | Cantidad basal de la hora local 17, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=17 | number | U |
| 18 | Cantidad basal de la hora local 18, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=18 | number | U |
| 19 | Cantidad basal de la hora local 19, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=19 | number | U |
| 20 | Cantidad basal de la hora local 20, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=20 | number | U |
| 21 | Cantidad basal de la hora local 21, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=21 | number | U |
| 22 | Cantidad basal de la hora local 22, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=22 | number | U |
| 23 | Cantidad basal de la hora local 23, no otra dosis que sumar a fuentes solapadas. | basal_hourly.delivered_units WHERE hour=23 | number | U |

## Bolo

Tiempo del registro: `Fecha y hora de finalización`.

| Cabecera | Significado | Destino | Conversión | Unidad |
|---|---|---|---|---|
| Tipo | Clasificación original de fila de bolo, conservada sin columna tipada específica. | records.values_json | text | — |
| Tipo de bolo | Tipo de bolo fuente, no enum API intercambiable. | boluses.bolus_type | text | — |
| Método de suministro del bolo | Método de suministro publicado en CSV. | boluses.delivery_method | text | — |
| Glucosa (mg/dl) | Glucosa de entrada o asociada al bolo, según tipo CSV. | glucose_readings.glucose_mg_dl OR boluses.glucose_mg_dl | number | mg/dL |
| Número de serie | Serie sensible de la bomba; separar dispositivos antes de unir registros. | records.pump_serial | text | — |
| Fecha y hora de finalización | Tiempo principal del registro CSV de bolo, distinto de una hora real de comida. | records.local_timestamp | local_timestamp | — |
| Insulina suministrada | Total declarado de insulina del bolo. No sumar de nuevo alimento/corrección/extendida. | boluses.delivered_units | number | U |
| Alimento suministrado | Componente de INSULINA para alimento, no gramos ingeridos. | boluses.food_units | number | U |
| Corrección suministrada | Componente de insulina de corrección. | boluses.correction_units | number | U |
| Descripción del estado de finalización | Estado del total/entrega del registro CSV. | boluses.completion_status | text | — |
| Fecha y hora de inicio del bolo | Inicio declarado del tramo de bolo extendido según el adaptador; conservar frente a fases API. | boluses.extended_start_local | local_timestamp | — |
| Fecha y hora de finalización del bolo | Fin declarado del tramo extendido; distinto del tiempo principal de registro. | boluses.extended_end_local | local_timestamp | — |
| Insulina suministrada en bolo | Componente extendido tipado por el adaptador CSV; no sumar de nuevo al total. | boluses.extended_units | number | U |
| Descripción del estado de finalización del bolo | Estado del componente extendido según CSV. | boluses.extended_status | text | — |
| Porcentaje estándar | Porcentaje inmediato/estándar declarado. | boluses.standard_percent | number | % |
| Duración (minutos) | Duración declarada de la opción extendida. | boluses.duration_minutes | number | min |
| Cantidad de carbohidratos | Gramos registrados; no prueban ingesta. Cero se conserva, pero la vista de entradas positivas no lo incluye. | boluses.carbohydrate_grams | number | g |
| Objetivo de glucemia (mg/dl) | Objetivo asociado al cálculo de bolo, no glucosa medida. | boluses.target_glucose_mg_dl | number | mg/dL |
| Factor de corrección | Sensibilidad/ISF registrada. | boluses.correction_factor_mg_dl_per_unit | number | (mg/dL)/U |
| I:C | Ratio de carbohidratos por unidad de insulina; no invertir sin conversión. | boluses.carbohydrate_ratio_g_per_unit | number | g/U |
