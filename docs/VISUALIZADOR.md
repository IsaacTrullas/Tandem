# Visualizador temporal · Tandem Local 0.8.2

La pestaña **Gráfico** abre el último día con lecturas disponibles. Todas las consultas son de lectura y mantienen el reloj de la bomba. No se inicia ninguna descarga por abrir el gráfico.

## Navegación

- **Anterior / Siguiente** desplazan una ventana completa.
- Fecha, duración y **Ver** permiten consultar otro tramo. Duraciones de 3 horas a 7 días; 24 horas por defecto.
- Arrastrar desplaza el eje temporal. La rueda acerca o aleja; al salir del tramo ya cargado se consulta el siguiente.
- **Último día** vuelve a los datos más recientes. Elegir la bomba y pulsar **Ver** si hay varias.
- El ratón mueve una guía vertical sobre los cuatro paneles. Un clic fija el instante; **Seguir ratón** libera la selección.
- Cada bolo, registro de carbohidratos, glucemia introducida, alerta o cambio de modo, perfil y reloj tiene una **guía vertical tenue** en los paneles sincronizados. Los sucesos con la misma hora comparten guía.
- Bajo la escala horaria aparecen las **horas de los eventos**, centradas sobre sus guías y repartidas en dos filas. Se mantienen todas las guías; cuando las horas están muy juntas, se priorizan las etiquetas que caben. Acerca el gráfico para separar las demás. Al pasar el ratón por esa zona del eje se muestran la fecha, los segundos y los tipos de evento cercanos. Con un zoom de hasta tres horas se rotulan los segundos; para más de 24 horas, también la fecha.

## Qué se representa

Glucosa del sensor y glucemia introducida se distinguen por sus marcadores. Se usa la hora de medición del sensor, conservando por separado la hora de ingreso en el registro. Se prefiere API sobre su copia CSV y no se suma información repetida.

El panel de insulina separa bolos de insulina activa observada (IOB). La IOB procede de campos cuya unidad U está identificada: son puntos reportados, sin interpolación ni cálculo de una curva farmacológica. Si la observación previa tiene más de diez minutos, el inspector dice que no hay dato confirmado y conserva el último valor y su hora.

Un bolo terminado se dibuja en su inicio cuando la asociación de fases es única; su cantidad final y la hora de terminación permanecen en la evidencia. Inicio, fin, componentes y CSV no son dosis que deban sumarse. Los carbohidratos de solicitud de bolo no se presentan como la hora real de la comida.

Los bolos cuya dosis registrada es **0,05 U** se resaltan en **frambuesa**, con una entrada propia en la leyenda. El inspector y la ayuda de su hora los identifican como «Bolo de 0,05 U». El marcador conserva su dosis y su hora reales; un margen visual bajo el cero permite verlo completo. Los demás bolos mantienen el azul. Esta identificación depende de la dosis, sin inferir por qué se administró; una observación ambigua o con varias revisiones no se clasifica como confirmada. No cambia los registros originales ni excluye estas dosis del conjunto de bolos.

La basal es la tasa indicada en U/h, distinta de una cantidad suministrada en U. Se representa también la tasa de perfil observada con línea discontinua. No se prolongan líneas sobre huecos grandes, cambios de reloj o puntos repetidos. El carril de modos muestra sueño y ejercicio con colores, nombres e iconos, limitado a los datos disponibles. Las duraciones solo se muestran si sus límites están confirmados y caben sin solaparse.

## Programa y parámetros históricos

El inspector muestra perfil/programa, basal del perfil, ratio, sensibilidad, objetivo y modo según los registros anteriores al cursor. Cada valor muestra **Observado** y su hora. Esto identifica la última evidencia de ese ajuste; no demuestra una configuración histórica completa ni una edición que no haya quedado registrada. Las instantáneas actuales de ajustes no se aplican al pasado.

Se invalidan los parámetros previos al cambiar de perfil o de reloj sin observación posterior. Las horas repetidas y las revisiones incompatibles se señalan como ambiguas. Un dato ausente se distingue de cero.

## Memoria y tiempos de carga

El visualizador conserva una sola ventana y un margen de hasta una hora por lado, sin superar siete días. Al navegar se reemplazan los datos anteriores; mientras llega una consulta puede coexistir brevemente el tramo anterior con el nuevo. Solo se conserva una solicitud pendiente, la más reciente.

El servicio consulta SQLite por rango y limita los objetos Python a 25.000 filas fuente para las series y 20.000 para el contexto. El contexto incorpora únicamente un registro anterior necesario por variable y los nombres de perfiles relevantes. Las agregaciones de límites se ejecutan en SQLite; no se carga todo el histórico ni las imágenes/PDF en memoria.

Si un tramo es demasiado denso, se pide reducirlo o se muestra el aviso de datos limitados. Los huecos no se rellenan ni las dosis se promedian silenciosamente. Las consultas se realizan fuera del hilo de la interfaz y el movimiento del ratón consulta estructuras del tramo cargado, sin acceder a SQLite en cada movimiento.

Validación de esta versión: 195 pruebas correctas, incluyendo servicios, interpretación histórica, navegación, cursor, cambio de ventanas, liberación de las series anteriores y guías de eventos. Las nuevas pruebas verifican también la identificación de 0,05 U, conservación de dosis y horas, ambigüedades, visibilidad del marcador y restauración del color del inspector. Revisión visual con datos reales en 1420x1000, 1180x820 y escala 200 %. No hay cambios en el esquema de la base.
