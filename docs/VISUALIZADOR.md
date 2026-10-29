# Visualizador temporal · Tandem Local 0.8.4

La pestaña **Gráfico** abre el último día con lecturas disponibles. Todas las consultas son de lectura y mantienen el reloj de la bomba. No se inicia ninguna descarga por abrir el gráfico.

## Navegación

- **Anterior / Siguiente** desplazan una ventana completa.
- Fecha, duración y **Ver** permiten consultar otro tramo. Duraciones de 3 horas a 7 días; 24 horas por defecto.
- Arrastrar desplaza el eje temporal. La rueda acerca o aleja; al salir del tramo ya cargado se consulta el siguiente.
- **Último día** vuelve a los datos más recientes. Elegir la bomba y pulsar **Ver** si hay varias.
- El ratón mueve una guía vertical sobre los cuatro paneles. Un clic fija el instante; **Seguir ratón** libera la selección.
- Al pasar sobre un marcador aparece un **mensaje con el nombre del evento, su valor y unidad si existe, y su hora original con segundos**. Incluye glucosa, glucemia introducida, bolos, carbohidratos, IOB, puntos de basal y triángulos de alertas/cambios. Las bandas de modos muestran la observación que las originó y su final cuando está confirmado. El mensaje funciona también con el instante fijado.
- Se identifica el símbolo bajo el cursor por su posición en pantalla. Las variantes del mismo tipo y hora se muestran por separado, sin sumar valores. En zonas densas se acota el mensaje y se indica cuántas observaciones adicionales hay. Se oculta al apartar el ratón, mover la ventana temporal, arrastrar, recargar o cambiar de página.
- Cada bolo, registro de carbohidratos, glucemia introducida, alerta o cambio de modo, perfil y reloj tiene una **guía vertical tenue** en los paneles sincronizados. Los sucesos con la misma hora comparten guía.
- Bajo la escala horaria aparecen las **horas de los eventos**, centradas sobre sus guías y repartidas en dos filas. Se mantienen todas las guías; cuando las horas están muy juntas, se priorizan las etiquetas que caben. Acerca el gráfico para separar las demás. Al pasar el ratón por esa zona del eje se muestran la fecha, los segundos y los tipos de evento cercanos. Con un zoom de hasta tres horas se rotulan los segundos; para más de 24 horas, también la fecha.

## Qué se representa

Glucosa del sensor y glucemia introducida se distinguen por sus marcadores. Se usa la hora de medición del sensor, conservando por separado la hora de ingreso en el registro. Se prefiere API sobre su copia CSV y no se suma información repetida.

El panel de insulina separa bolos de insulina activa observada (IOB). La IOB procede de campos cuya unidad U está identificada: son puntos reportados, sin interpolación ni cálculo de una curva farmacológica. Si la observación previa tiene más de diez minutos, el inspector dice que no hay dato confirmado y conserva el último valor y su hora.

Las tarjetas **Último bolo** y **Últimos hidratos** conservan el último registro anterior o igual al cursor, su fecha/hora original y la antigüedad. No eligen un evento futuro por proximidad. Incluyen el último registro anterior al tramo cargado, aunque sea de otro día; ese registro de contexto no se añade como marcador al gráfico. Si hay un cambio o una repetición de reloj que afecta a la antigüedad, se muestra **Reloj modificado** en lugar de un tiempo transcurrido. Las variantes incompatibles de una misma hora se indican como ambiguas. Los carbohidratos corresponden a los registros publicados, habitualmente de solicitud de bolo, sin atribuirles hora real de ingesta.

Los mensajes de alertas muestran la descripción literal del tipo interno cuando está identificada, su identificador, código de evento, sensor y reconocimiento cuando constan. **Ver horas y procedencia** permite leer y copiar todos los parámetros, etiquetas y transiciones conservados. Un tipo desconocido se presenta como **Sin descripción disponible**, manteniendo su código original. Véase [ALERTAS.md](ALERTAS.md).

Un bolo terminado se dibuja en su inicio cuando la asociación de fases es única; su cantidad final y la hora de terminación permanecen en la evidencia. Inicio, fin, componentes y CSV no son dosis que deban sumarse. Los carbohidratos de solicitud de bolo no se presentan como la hora real de la comida.

Los bolos cuya dosis registrada es **0,05 U** se resaltan en **frambuesa**, con una entrada propia en la leyenda. El inspector y la ayuda de su hora los identifican como «Bolo de 0,05 U». El marcador conserva su dosis y su hora reales; un margen visual bajo el cero permite verlo completo. Los demás bolos mantienen el azul. Esta identificación depende de la dosis, sin inferir por qué se administró; una observación ambigua o con varias revisiones no se clasifica como confirmada. No cambia los registros originales ni excluye estas dosis del conjunto de bolos.

La basal es la tasa indicada en U/h, distinta de una cantidad suministrada en U. Se representa también la tasa de perfil observada con línea discontinua. No se prolongan líneas sobre huecos grandes, cambios de reloj o puntos repetidos. El carril de modos muestra sueño y ejercicio con colores, nombres e iconos, limitado a los datos disponibles. Las duraciones solo se muestran si sus límites están confirmados y caben sin solaparse.

## Programa y parámetros históricos

El inspector muestra perfil/programa, basal del perfil, ratio, sensibilidad, objetivo y modo según los registros anteriores al cursor. Cada valor muestra **Observado** y su hora. Esto identifica la última evidencia de ese ajuste; no demuestra una configuración histórica completa ni una edición que no haya quedado registrada. Las instantáneas actuales de ajustes no se aplican al pasado.

Se invalidan los parámetros previos al cambiar de perfil o de reloj sin observación posterior. Las horas repetidas y las revisiones incompatibles se señalan como ambiguas. Un dato ausente se distingue de cero.

## Memoria y tiempos de carga

El visualizador conserva una sola ventana y un margen de hasta una hora por lado, sin superar siete días. Al navegar se reemplazan los datos anteriores; mientras llega una consulta puede coexistir brevemente el tramo anterior con el nuevo. Solo se conserva una solicitud pendiente, la más reciente.

El servicio consulta SQLite por rango y limita los objetos Python a 25.000 filas fuente para las series y 20.000 para el contexto. El contexto incorpora únicamente un registro anterior necesario por variable y los nombres de perfiles relevantes. Las agregaciones de límites se ejecutan en SQLite; no se carga todo el histórico ni las imágenes/PDF en memoria.

La búsqueda de los últimos bolos/carbohidratos tiene un presupuesto separado de 2.048 filas fuente: SQLite obtiene fechas ancla y solo se cargan sus ventanas de fases. Se conserva únicamente el último grupo de cada tipo anterior al tramo. Si se alcanza el límite, se devuelve aviso y se evita presentar un último valor parcial como completo. La búsqueda se realiza en el trabajador al cargar una ventana; el movimiento del cursor usa exclusivamente índices en memoria.

Si un tramo es demasiado denso, se pide reducirlo o se muestra el aviso de datos limitados. Los huecos no se rellenan ni las dosis se promedian silenciosamente. Las consultas se realizan fuera del hilo de la interfaz y el movimiento del ratón consulta estructuras del tramo cargado, sin acceder a SQLite en cada movimiento.

Validación de esta versión: 270 pruebas correctas. Incluyen alertas y campos desconocidos, último registro fuera del día/semana, exclusión de futuros, fuentes, fases de bolo, duplicados, revisiones, relojes y límites de memoria. Se corrigió una omisión de carbohidratos CSV cuando su dosis ya estaba asociada con API pero faltaba la solicitud API de carbohidratos; se conserva la deduplicación entre fuentes. Revisión visual con datos reales en 1420x1000, 1180x820 y escala 200 %. No hay cambios en el esquema de la base ni en las filas originales.
