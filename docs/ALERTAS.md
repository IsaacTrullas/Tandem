# Alertas y detalle de eventos · Tandem Local 0.8.4

La base conserva más información que el rótulo genérico del gráfico. Según el evento, incluye `alertId`, `alarmId` o `dalertId`, etiquetas del catálogo, `sensorType`, `ackSource`, `faultLocatorData`, `param1`, `param2` y otros campos originales. No todos tienen un significado o unidad documentados.

El mensaje sobre el triángulo muestra una descripción legible del identificador cuando existe una traducción inequívoca, el código exacto, la fase registrada y el sensor. Por ejemplo, `aaAlert_CGM_NO_READINGS` se presenta como falta de lecturas del sensor; `Alert_CGM_CALIB_ERROR`, como error de calibración según la etiqueta interna. Un reconocimiento describe la confirmación registrada y su origen; no establece por sí solo que la incidencia se haya resuelto.

**Ver horas y procedencia** contiene las propiedades, etiquetas y transiciones completas como texto seleccionable. También conserva los datos técnicos de otros eventos aunque no tengan descripción específica. Los campos sin unidad documentada permanecen como valores originales, sin convertir `param1` o `param2` en glucosa, duración u otra magnitud.

Las descripciones de códigos proceden de traducciones literales del catálogo local `event_codes.json`, obtenido de [tconnectsync](https://github.com/jwoglom/tconnectsync/tree/master/tconnectsync/eventparser), con origen, hashes y licencia conservados. Se contrasta que las etiquetas de la observación y las del catálogo coincidan; un conflicto o un código desconocido se muestra explícitamente.

La [guía oficial española de Tandem Control-IQ 7.7](https://www.tandemdiabetes.com/docs/default-source/user-guide/user-guide-tslimx2-control-iq-7-7-mgdl-es-es-aw1011418.pdf?sfvrsn=8c47c7d7_4#page=241) incluye un apartado de alerta de error de calibración, pero no acredita una correspondencia directa entre cada identificador interno de Source y una pantalla concreta de todas las versiones. La aplicación mantiene esa distinción y no añade causas ni instrucciones terapéuticas a partir de un código.

La interfaz consulta exclusivamente los registros descargados. No modifica alertas, ajustes ni estados de la bomba o de la cuenta.
