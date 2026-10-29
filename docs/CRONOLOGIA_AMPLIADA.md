# Cronología ampliada · 0.9.0

Desde 0.9.1, el panel basal incluye además una referencia horizontal gris continua rotulada **0 U/h**, visible en toda la anchura al desplazar o ampliar el tramo. La referencia se vuelve a crear al cambiar de ventana y no altera las tasas representadas.

- **Origen del bolo:** pantalla/botón de bomba, algoritmo o Bluetooth cuando está identificado. La leyenda distingue algoritmo y Bluetooth; 0,05 U sigue resaltado en frambuesa.
- **Desglose del último bolo:** total registrado, solicitudes inmediata/extendida, alimento/corrección, estados de finalización y modificaciones/rechazos del usuario cuando se publican. Las fases se asocian por dispositivo, bolusId y ventana acotada; las asociaciones múltiples se indican. Sus cantidades son componentes y totales de la misma entrega, no dosis independientes que sumar.
- **Extendidos:** bandas en el panel de insulina solo cuando hay extremos registrados CSV o una pareja única inicio/fin API. La duración solicitada se muestra como solicitud y no se convierte en un intervalo de entrega supuesto. Las diferencias entre fuentes permanecen visibles en la procedencia.
- **Basal:** referencia discontinua y valor del perfil observado; azul por encima y ámbar por debajo. «Comparación de basal» muestra tasas indicada, de perfil, del algoritmo y temporal, así como el origen de la tasa cuando consta. No se rellenan huecos ni se prolonga una configuración actual sobre el pasado.
- **Alertas:** activación, reconocimiento y desactivación son eventos diferentes. Las identificaciones 50/51 se contrastan con la [descripción oficial de Tandem](https://www.tandemdiabetes.com/support-center/software-updates/tslimx2-insulin-pump/article/control-iq-alerts-on-tslimx2). Una lectura MCG previa a menos de diez minutos es contexto temporal, no demostración de causa ni de umbral configurado.
- **Sensor:** lecturas y hora de ingreso separadas, estado del sensor, señal, incorporaciones y finales de sesión con duración/códigos originales disponibles. Las entradas de glucemia distinguen teclado, copia de MCG y marca de uso para calibración. La marca indica uso registrado, no éxito de calibración.
- **Tendencia:** se muestra el campo `rate` original, con escala pendiente de validar. No se inventa un factor de conversión. También se calcula el cambio medio entre dos lecturas consecutivas válidas, con menos de diez minutos de separación, sin horas repetidas ni cambios de reloj; se rotula como cálculo entre lecturas, no como velocidad instantánea del sensor.
- **Mantenimiento:** inicio/fin de carga eléctrica y llenados quedan en «Eventos del tramo», con los parámetros técnicos disponibles. Esos volúmenes de llenado no se suman a insulina terapéutica.
- **Resumen PDF:** las celdas de resumen y métricas extraídas conservan documento, periodo, página y estado de revisión. No se atribuyen a un día ni se aplican instantáneas actuales al pasado. Si ningún informe cubre el tramo, se indica. Límite por consulta: 120 campos y 40 métricas, con aviso si se supera.

Las secciones se despliegan en el inspector lateral, que permite desplazamiento vertical. La lista de eventos muestra hasta 200 entradas por tramo, con aviso de límite. Todo se obtiene de la ventana cargada y sus predecesores acotados; mover el cursor no consulta SQLite.

Para repetir el análisis de todas las activaciones de alertas:

```powershell
.\.venv\Scripts\python.exe -m tandem.alert_audit --db data\tandem.sqlite --output data\auditoria_alertas
```

El informe JSON agrupa tipos y distribuciones de glucosa; el JSONL conserva cada asociación con sus identificadores, horas y antigüedad de lectura. La comparación utiliza el tiempo de medición MCG y la última lectura anterior dentro de diez minutos. Se excluyen revisiones incompatibles y barreras de reloj. El auditor mantiene una ventana de un día de sensor en memoria, sin cargar el histórico completo de glucosa. No interpreta como causas las coincidencias encontradas.
