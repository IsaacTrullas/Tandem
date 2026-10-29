# Diseño de la interfaz · Tandem Local 0.8

La aplicación se organiza alrededor de la exploración de un día. La cronología tiene prioridad de espacio y las tareas secundarias se sitúan en la navegación lateral.

## Estructura

- **Cronología**: navegación temporal, leyenda exterior y gráficos sincronizados.
- **Archivo**: fuentes, fechas registradas y última descarga.
- **Explorar datos**: tablas por fuente, filtros y exportación completa.
- **Descargas**: resultados de las ejecuciones y motivos legibles cuando requieren atención.
- **Importar CSV/PDF** y **Acceso y conexión**: acciones secundarias en la parte inferior de la navegación.

La navegación se pliega en ventanas estrechas. Los iconos conservan sus nombres accesibles y sus ayudas; el botón inferior permite desplegarla manualmente.

## Lectura del gráfico

La leyenda queda fuera de las curvas. Los pictogramas son vectores: gota para bolos, manzana para carbohidratos, luna para sueño y corredor para ejercicio. Color, forma y texto se combinan para distinguir la información.

Un carril de modos independiente muestra sueño, ejercicio y modo estándar. Sus límites derivan de los eventos conservados; un periodo desconocido no se presenta como modo normal. No se prolongan bandas más allá de las observaciones disponibles ni a través de cambios de reloj sin confirmación posterior. La duración solo se rotula cuando los extremos están confirmados y el texto cabe.

Las lecturas cercanas al cursor ocupan cuatro tarjetas. Los ajustes observados se agrupan en una tabla compacta, con la hora de observación. El detalle de procedencia se despliega bajo petición. No se muestra un cuadro de texto grande sobre la curva.

Desde 0.8.1, los sucesos discretos se conectan mediante guías verticales tenues con dos filas de horas bajo el eje. Las etiquetas conservan su posición temporal y se separan por prioridad y espacio disponible; el zoom permite leer las zonas densas. Glucosa del sensor, IOB y basal continuas no generan una guía por muestra. Cada panel usa un solo elemento de guías para evitar crear cientos de objetos gráficos; las guías se reemplazan junto con la ventana de datos.

Desde 0.8.2, los bolos registrados de 0,05 U tienen gota frambuesa, borde claro y leyenda propia. El inspector adopta ese color y su rótulo mientras se consulta uno de ellos. El margen bajo el cero protege el pictograma sin desplazar el valor del dato; las marcas negativas de ese margen no se rotulan. No se deduce la intención ni se modifica la dosis almacenada.

Desde 0.8.3, el hover sobre un símbolo abre un mensaje compacto con nombre, cantidad/unidad cuando existe y hora original. La detección considera ambas coordenadas y el símbolo visible; no abre mensajes por compartir solo una hora. El instante fijado permanece estable. Las coincidencias del mismo tipo y hora conservan sus registros separados, y el cuadro reduce el número de entradas si no caben en el área de dibujo. Las bandas muestran su observación real y distinguen final confirmado de borde visible. El hover usa exclusivamente el tramo en memoria.

Desde 0.8.4, las tarjetas de bolo y carbohidratos muestran el último registro hasta el cursor con fecha/hora y antigüedad, incluido el registro anterior a la ventana. Las alertas incorporan descripción del identificador interno y detalles del sensor/reconocimiento. Los parámetros técnicos completos se despliegan en la procedencia y se pueden seleccionar para copiar. La búsqueda del registro anterior permanece acotada y fuera del hilo de widgets.

## Datos y funcionamiento

En 0.9, la referencia basal tiene valor numérico y sombreado de diferencias, y los bolos de origen algoritmo/Bluetooth tienen colores diferenciados; 0,05 U conserva prioridad frambuesa. El inspector incorpora secciones plegables de bolo, basal, sensor, lista de eventos y resumen PDF. Cada información mantiene su fecha, unidad, fuente o estado de revisión. Los intervalos extendidos se sombrean con los extremos registrados; candidatos de fuentes distintas no se suman.

La versión mantiene las consultas por ventanas y los límites de memoria. No cambia la base, las unidades, el reloj original ni los registros clínicos. Las configuraciones actuales no se aplican retrospectivamente. El rediseño modifica la presentación y la geometría de los modos, sin convertir observaciones parciales en una historia de ajustes completa.

La fecha y el zoom se conservan al actualizar el archivo; **Más reciente** permite volver explícitamente al último día disponible.

## Verificación

Se revisan capturas compuestas con datos reales a 1420×1000, 1180×820 y escala 200 %, además de pruebas de navegación, lectura de estados, límites temporales, trabajo en segundo plano y liberación de ventanas anteriores. Las capturas quedan en data/gui_design/, excluidas de Git.

Resultado de verificación: **167 pruebas correctas**. Se revisaron la cronología, Archivo, Explorar datos y Descargas; los iconos y textos de modos se miden para evitar solapamientos y las unidades se muestran con una jerarquía distinta del valor. Los avisos de reloj anteriores a la ventana no se mantienen como alerta permanente si ya no afectan a los parámetros observados.
