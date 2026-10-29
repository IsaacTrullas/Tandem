# Protocolo de conexión, descarga y carga local

## Recopilador API añadido en 0.5

La aplicación también ejecuta `collect` para la API EU: credenciales en Windows, consulta de todas las bombas, archivo de respuestas sin filtro de eventos, ventanas de hasta 28 días, reanudación, cruce y copias. Véase [APLICACION.md](APLICACION.md). Este canal tiene su propia cobertura en `api_windows`; nunca sustituye el estado de pares CSV/PDF descrito abajo. El acceso EU real y la recopilación histórica se verificaron el 29/10/2026.

## Alcance operativo

Este protocolo lo ejecuta el agente con acceso al navegador de Codex y a este repositorio. La conexión y exportación se realizan en la interfaz oficial de Tandem Source EU; la planificación, conservación, importación, OCR y auditoría se ejecutan con el código local. No es un conector web autónomo instalado como servicio.

Autorización vigente: consultar y descargar los datos de esta cuenta, y guardarlos en local. **No modificar cuenta, perfiles, unidades, conexiones, permisos, consentimientos ni bomba.** Cambiar filtros temporales de informes y pulsar controles de exportación forma parte de la consulta. No subir ningún archivo.

No guardar contraseñas en código, manifiestos, capturas, logs o base. Reutilizar una sesión disponible del navegador. Si aparece inicio de sesión sin credenciales disponibles, dejar el acceso al usuario y continuar únicamente con trabajo local. No dar por descargada una ventana en ese caso. Si aparece aceptación de condiciones, no aceptarla como parte de la exportación.

## 1. Preparar y planificar

Trabajar en `C:\Repositorios\Tandem`. Comprobar estado y generar plan:

```powershell
.\scripts\Tandem.ps1 status
.\scripts\Tandem.ps1 plan --output data\sync\plan.json
```

El calendario de planificación es Europe/Madrid. El último periodo debe tener **ZIP y PDF importados**. El plan vuelve a descargar los últimos siete días cubiertos, hasta hoy inclusive, y divide intervalos en bloques de como máximo 30 días. Repara periodos con un solo formato antes de avanzar. Para un rescate antiguo usar explícitamente `--since YYYY-MM-DD`; para fijar corte `--through YYYY-MM-DD`.

Un plan no demuestra que existan datos nuevos. El día actual suele ser parcial; registrar también la última subida que muestre la web. El solapamiento de siete días cubre llegadas tardías habituales, pero no garantiza detectar cambios más antiguos: un respaldo histórico completo se solicita con `--since`.

## 2. Conectar en modo consulta

Abrir `https://source.eu.tandemdiabetes.com/` en segundo plano con las herramientas de navegador autorizadas. Verificar destino EU y la cuenta/paciente visibles, sin copiar identificadores en documentación pública. Si redirige al SSO oficial `sso.tandemdiabetes.com`, completar el acceso normal con la sesión/gestor del usuario o pedir que inicie sesión. No extraer cookies, tokens ni contraseñas del navegador.

Usar el estado visible actualizado después de cada navegación/acción. No automatizar contra endpoints supuestos ni alterar la configuración de la bomba. Si el navegador no está disponible, registrar `blocked_login` o `blocked_browser` en un recibo local y parar las descargas; no marcar `sync` completado.

En un acceso autorizado disponible, revisar también los detalles emergentes de los eventos que el PDF agrupa o dibuja sin hora exacta. La guía oficial permite consultarlos pasando el cursor. Conservar texto, fecha, evento asociado y evidencia local con una herramienta de interacción admitida; no suponer ese detalle si solo se dispone del PDF. Este paso está pendiente de una sesión autenticada y no se ha validado como extracción autónoma.

## 3. Descargar cada ventana del plan

### ZIP de CSV

1. Abrir la `timeline_url` exacta del plan, ruta `/reports/timeline?startDate=...&endDate=...` observada en la aplicación.
2. Esperar al informe cargado y comprobar fechas visibles. No interpretar un estado aún en carga como ausencia de datos.
3. Pulsar **Exportar CSV**, comprobar el rango del diálogo y pulsar **Exportar**. El resultado es un ZIP con cinco CSV, aunque el botón diga CSV.
4. Registrar la espera de descarga antes de pulsar Exportar. Capturar la ruta de esa descarga concreta; los nombres del fabricante pueden repetirse.
5. Copiar bytes, sin modificar contenido, a `data/inbox/<ejecucion>/cronologia_INICIO_FIN.zip`. Conservar también la ruta temporal observada, hora UTC y SHA-256 en el recibo.

### PDF completo

1. Abrir la pantalla **Guardar e imprimir** o `/reports/print` de la misma sesión.
2. Mantener seleccionados los tres informes: resumen general, cronograma diario y configuración de la bomba.
3. Establecer **por separado** el rango del resumen y el del cronograma. La pantalla de impresión puede ignorar las fechas de la URL y volver a sus dos semanas por defecto.
4. En cada selector, elegir **Personalizado**, inicio y final con el calendario, y **Seleccionar**. Los controles anteriores pueden cambiar la selección del calendario: releer el estado tras cada acción y comprobar las dos etiquetas finales contra `expected_pdf_label`.
5. Con ambos rangos correctos y **Guardar informes** habilitado, esperar la descarga y pulsar ese botón. Aquí Guardar informes descarga un PDF; no guarda configuración en la cuenta.
6. Copiar a `data/inbox/<ejecucion>/informes_INICIO_FIN.pdf`; registrar ruta, hora y SHA-256. La configuración incluida representa la última subida, no una configuración histórica del rango pedido.

Solicitar una exportación cada vez y esperar a que termine. Ante caducidad de sesión, error o contenido inesperado, conservar los archivos recibidos, registrar el punto de parada y reanudar; no lanzar bucles de reintento ni declarar éxito.

## 4. Manifiesto de recepción

Crear `data/sync/descarga_<ejecucion>.json` después de que ambos archivos estén completos. Ejemplo de estructura (sustituir rutas, hashes y marcas por valores comprobados; no inventarlos):

```json
{
  "schema_version": 1,
  "plan": {"path": "data/sync/plan.json"},
  "windows": [{
    "start": "2026-10-21",
    "end": "2026-10-28",
    "last_upload": "texto observado de última subida y zona horaria",
    "csv_zip": {
      "path": "C:/Repositorios/Tandem/data/inbox/EJECUCION/cronologia_2026-10-21_2026-10-28.zip",
      "sha256": "HASH_SHA256_REAL",
      "downloaded_at": "MARCA_UTC_REAL"
    },
    "pdf": {
      "path": "C:/Repositorios/Tandem/data/inbox/EJECUCION/informes_2026-10-21_2026-10-28.pdf",
      "sha256": "HASH_SHA256_REAL",
      "downloaded_at": "MARCA_UTC_REAL"
    }
  }]
}
```

Los hashes se calculan con `Get-FileHash -Algorithm SHA256` o SHA-256 de los bytes descargados. Pueden añadirse `download_source_path` y `observed_date_labels` para trazabilidad; el manifiesto completo se conserva en `sync_runs`. Rutas relativas se resuelven desde la carpeta del manifiesto. No escribir un manifiesto de éxito si falta un archivo.

## 5. Importar, procesar y auditar

```powershell
.\scripts\Tandem.ps1 sync data\sync\descarga_EJECUCION.json
.\scripts\Tandem.ps1 ocr
.\scripts\Tandem.ps1 extract-pdf
.\scripts\Tandem.ps1 audit --output data\auditorias\EJECUCION.json
.\scripts\Tandem.ps1 status
```

`sync` crea una copia previa mediante la API de backup de SQLite, archiva otra copia por SHA-256 y aplica una sola transacción al manifiesto. Comprueba extensión, SHA si se proporciona, CRC, cinco tipos de CSV con cabecera conocida, fechas de cada fila y los encabezados de resumen/cronograma del PDF. Un archivo no válido revierte toda la importación de ese manifiesto y registra el fallo; los archivos descargados permanecen. No cambiar automáticamente el esquema para aceptar campos desconocidos.

La importación de respaldo con `import-source` es por archivo y admite cuarentena; para actualizaciones usar siempre `sync`, que exige parejas y transacción completa. Nunca interpretar un archivo en cuarentena como normalizado.

El OCR se ejecuta localmente con Windows.Media.Ocr y el idioma ya instalado. Reintenta solo páginas pendientes o con error. No instala idiomas del sistema. Una reejecución tras interrupción continúa el trabajo pendiente; los archivos importados quedan intactos.

`extract-pdf` es obligatorio después del OCR. Registra imágenes, transparencias, texto y dibujos; filas de tablas, horarios, símbolos, bandas, alertas, etiquetas y curvas. Compara los bloques de cada página fuente con lo almacenado. Continúa las páginas pendientes sin duplicar evidencias y conserva márgenes de error y clasificaciones no resueltas.

También desglosa y verifica cada leyenda, calibra las 33 clases del cronograma y los 3 elementos de tendencia, ejecuta la pasada de símbolos y conserva la matriz de cobertura. Una etiqueta nueva, ausente o ilegible debe producir un resultado incompleto, sin reutilizar silenciosamente otra leyenda. La leyenda es una referencia de símbolos, nunca un registro de eventos del paciente.

La misma fase ejecuta la extracción cuantitativa: separa escalón/etiquetas, área de perfil, barras variables y temporales; calibra U/h por gráfico, y asocia las barras extendidas al CSV por ambos extremos. `quantify` permite reanudar solo esta parte. Conservar sus márgenes y candidatos; no sumar capas visuales como dosis adicionales.

Para reconstruir solo el atlas y revisar el catálogo: `scripts/Tandem.ps1 legend --atlas data/legend/atlas_leyenda.png`. Añadir `--scan` para procesar gráficos pendientes. La extracción normal ya incluye ambas fases.

`scripts/ActualizarLocal.ps1 -Manifiesto RUTA` ejecuta secuencialmente carga, OCR, extracción ampliada, auditoría y copia final. Se detiene en el primer fallo. Sigue necesitando la conexión y descarga oficiales previas.

## 6. Criterios de finalización

- `sync` termina con código cero y su fila está `complete`; todas las ventanas tienen ZIP y PDF, incluido el caso de periodo vacío.
- `audit` termina con código cero: integridad SQLite correcta, claves foráneas sin errores, hashes originales/filas correctos, toda fila fuente vinculada, sin archivos en cuarentena ni fechas OCR fuera de rango.
- Todas las páginas aparecen con OCR `complete`. Si Windows OCR no está disponible, declarar importación completa pero **extracción PDF pendiente**, sin ocultar ese estado.
- Todas las páginas tienen extracción ampliada y verificación de bloques `complete`. No quedan páginas sin ampliar, bloques omitidos o imágenes/máscaras con hashes incorrectos. Los símbolos y valores ambiguos siguen explícitos en el inventario y la cola de revisión.
- Todas las leyendas tienen catálogo completo y todos los gráficos diarios su pasada registrada. Revisar también `legend_partial_adapters`: un control estructural correcto no autoriza a afirmar que todos los significados se han resuelto. La auditoría de símbolos no sustituye esa revisión semántica.
- Todos los gráficos con trazas tienen calibración y capas procesadas, sin conflictos de etiquetas/eje. Todos los bolos extendidos disponibles y sus tramos diarios tienen asociación gráfica; en caso contrario la auditoría falla y registra lo pendiente. Un panel vacío por cambio de reloj no requiere una tasa inventada.
- Comparar número de registros, fechas mínima/máxima y `daily_coverage` con la ejecución anterior. No exigir un incremento: puede no haber nuevas subidas. No inferir un hueco solo de fechas antiguas del reloj.
- Los candidatos OCR quedan separados como no revisados; finalización de descarga no equivale a validación de su contenido gráfico.
- Crear copia final con `backup`, comprobar que abre y que sus hashes/originales coinciden. Registrar corte real y limitaciones.

Tras una interrupción, comprobar primero `sync_runs`, `import_runs`, estado OCR y recibos. No borrar intentos fallidos, originales o filas para que los números cuadren.

## Programación futura

La versión 0.5 añade un recopilador API ejecutable desde aplicación o CLI y acceso persistido en Windows Credential Manager. No hay un proceso de navegador autónomo ni una tarea recurrente instalada. Una programación futura deberá ejecutar el recopilador bajo el mismo usuario Windows, conservar el registro y avisar solo ante novedades/fallos/acceso requerido. No afirmar que funciona de extremo a extremo hasta verificar una ejecución real autenticada.
