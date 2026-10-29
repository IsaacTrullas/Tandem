# Visualizador temporal · Tandem Local 0.7

La pestaña **Gráfico** abre el último día con lecturas disponibles. Todas las consultas son de lectura y mantienen el reloj de la bomba. No se inicia ninguna descarga por abrir el gráfico.

## Navegación

- **Anterior / Siguiente** desplazan una ventana completa.
- Fecha, duración y **Ver** permiten consultar otro tramo. Duraciones de 3 horas a 7 días; 24 horas por defecto.
- Arrastrar desplaza el eje temporal. La rueda acerca o aleja; al salir del tramo ya cargado se consulta el siguiente.
- **Último día** vuelve a los datos más recientes. Elegir la bomba y pulsar **Ver** si hay varias.
- El ratón mueve una guía vertical sobre los cuatro paneles. Un clic fija el instante; **Seguir ratón** libera la selección.

## Qué se representa

Glucosa del sensor y glucemia introducida se distinguen por sus marcadores. Se usa la hora de medición del sensor, conservando por separado la hora de ingreso en el registro. Se prefiere API sobre su copia CSV y no se suma información repetida.

El panel de insulina separa bolos de insulina activa observada (IOB). La IOB procede de campos cuya unidad U está identificada: son puntos reportados, sin interpolación ni cálculo de una curva farmacológica. Si la observación previa tiene más de diez minutos, el inspector dice que no hay dato confirmado y conserva el último valor y su hora.

Un bolo terminado se dibuja en su inicio cuando la asociación de fases es única; su cantidad final y la hora de terminación permanecen en la evidencia. Inicio, fin, componentes y CSV no son dosis que deban sumarse. Los carbohidratos de solicitud de bolo no se presentan como la hora real de la comida.

La basal es la tasa indicada en U/h, distinta de una cantidad suministrada en U. Se representa también la tasa de perfil observada con línea discontinua. No se prolongan líneas sobre huecos grandes, cambios de reloj o puntos repetidos. Las bandas azul y beige indican los modos sueño y ejercicio observados, limitadas a datos disponibles.

## Programa y parámetros históricos

El inspector muestra perfil/programa, basal del perfil, ratio, sensibilidad, objetivo y modo según los registros anteriores al cursor. Cada valor muestra **Observado** y su hora. Esto identifica la última evidencia de ese ajuste; no demuestra una configuración histórica completa ni una edición que no haya quedado registrada. Las instantáneas actuales de ajustes no se aplican al pasado.

Se invalidan los parámetros previos al cambiar de perfil o de reloj sin observación posterior. Las horas repetidas y las revisiones incompatibles se señalan como ambiguas. Un dato ausente se distingue de cero.

## Memoria y tiempos de carga

El visualizador conserva una sola ventana y un margen de hasta una hora por lado, sin superar siete días. Al navegar se reemplazan los datos anteriores; mientras llega una consulta puede coexistir brevemente el tramo anterior con el nuevo. Solo se conserva una solicitud pendiente, la más reciente.

El servicio consulta SQLite por rango y limita los objetos Python a 25.000 filas fuente para las series y 20.000 para el contexto. El contexto incorpora únicamente un registro anterior necesario por variable y los nombres de perfiles relevantes. Las agregaciones de límites se ejecutan en SQLite; no se carga todo el histórico ni las imágenes/PDF en memoria.

Si un tramo es demasiado denso, se pide reducirlo o se muestra el aviso de datos limitados. Los huecos no se rellenan ni las dosis se promedian silenciosamente. Las consultas se realizan fuera del hilo de la interfaz y el movimiento del ratón consulta estructuras del tramo cargado, sin acceder a SQLite en cada movimiento.

Validación de esta versión: 151 pruebas correctas, incluyendo servicios, interpretación histórica, navegación, cursor, cambio de ventanas y liberación de las series anteriores. Revisión visual con datos reales en 1420x1000 y 1180x820. No hay cambios en el esquema de la base.
