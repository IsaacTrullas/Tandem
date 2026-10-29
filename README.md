# Tandem Local: aplicación y base de datos

Base SQLite creada en `data/tandem.sqlite`. Contiene el histórico descargado de Tandem Source, los originales íntegros dentro de la propia base y tablas para análisis. La aplicación solo escribe en local.

El protocolo operativo está en [docs/PROTOCOLO_SINCRONIZACION.md](docs/PROTOCOLO_SINCRONIZACION.md). El [diccionario completo de datos](docs/DICCIONARIO_DATOS.md) describe cada tabla, columna, código API, unidad y conversión; incluye un catálogo JSON para programas y una [guía de integración con LLM](docs/INTEGRACION_LLM.md). La arquitectura y las limitaciones se explican en [docs/MODELO_DATOS.md](docs/MODELO_DATOS.md).

La [leyenda completa desglosada](docs/LEYENDA_PDF.md) contiene 33 elementos diarios y 3 de tendencia, con su símbolo fuente, dimensiones, unidades, reglas, relación con los CSV y estado de implementación. El atlas visual queda en `data/legend/atlas_leyenda.png`. Los candidatos nuevos se consultan en `legend_symbol_hits`, y la cobertura en `v_legend_coverage`.

## Aplicación 0.10.0 · Qt

Los bolos con gramos positivos asociados se representan en naranja, igual que los carbohidratos; la leyenda los identifica como «Bolo con carbohidratos». El origen y el desglose permanecen en los detalles. El SDK incorpora `Reader.describe(dataset)` y `Reader.describe_event(code)`, y las exportaciones JSONL incluyen la huella del diccionario. Validación de esta versión: **295 pruebas correctas**, documentación contrastada con el esquema real en solo lectura; sin cambios en los registros clínicos ni en la cuenta Tandem.

La cronología incorpora [comparación de basal, origen/desglose de bolos, extendidos, sensor, ciclo de alertas, mantenimiento y resúmenes PDF](docs/CRONOLOGIA_AMPLIADA.md). Los datos originales siguen intactos y la carga continúa por ventanas. La cifra siguiente corresponde a la primera verificación; el corte actualizado se consulta en Descargas.

Validación real del 29/10/2026: acceso EU correcto, **401.411 eventos API** conservados hasta **29/10/2026 08:05:36**, **66.085 lecturas CSV contrastadas por hora de medición y valor**, cero conflictos. Esquema 7, 96 pruebas correctas. Quedan 36.042 registros de cuatro códigos sin interpretar (9, 22, 23, 52), preservados íntegramente. Las fechas de 2025 permanecen como reloj fuente, sin inferir inicio de tratamiento.

Interfaz nativa **Qt 6 / PySide6** con [navegación y diseño revisados](docs/DISENO_GUI.md): cronología principal, carril de sueño/ejercicio, leyenda exterior legible, pictogramas vectoriales, inspector compacto y navegación lateral plegable. Incluye [gráfico temporal interactivo](docs/VISUALIZADOR.md), archivo, consulta paginada, exportación e historial de descargas. El gráfico carga por ventanas acotadas e incluye valores al pasar el ratón y parámetros históricos observados. Abrir con `scripts\AbrirAplicacion.ps1`. Incluye recopilación API EU, gestor de credenciales Windows, cruce de fuentes, importación CSV/PDF y SDK de solo lectura con exportación JSONL. [Uso y límites](docs/APLICACION.md). La API está autenticada y comprobada. Los CSV/PDF mantienen su corte del 27/10; la API tiene cobertura posterior.

## Estado inicial verificado, 28/10/2026

| Contenido | Cantidad |
|---|---:|
| ZIP originales / CSV contenidos | 10 / 50 |
| PDF / páginas | 10 / 141 |
| Filas CSV conservadas y estructuradas | 133.655 |
| Lecturas MCG | 64.703 |
| Glucosas introducidas en la bomba | 1.382 |
| Bolos | 2.461 |
| Bolos con carbohidratos positivos | 869 |
| Dosis basales detalladas | 64.878 |
| Filas de basal por día, con 24 columnas horarias | 231 |
| Paneles diarios localizados por OCR, incluidos días vacíos y continuaciones | 271 |
| Candidatos de alertas/alarmas en texto OCR | 76 |

Datos clínicos desde **16/03/2026 hasta 27/10/2026**, último MCG a las **16:04:06 según el reloj de la bomba**. Se conservan por separado en su fecha original ocho filas de configuración inicial con reloj 26/01/2025. El día final es parcial. Hay MCG y basal en los 226 días desde el 16 de marzo; esto no demuestra ausencia de huecos intradía.

Los CSV sí contienen gramos de carbohidratos asociados al bolo, insulina, glucosa, objetivos y ratios. No contienen nombres/composición de comidas. El momento del bolo no se etiqueta como hora real de la comida.

La ampliación PDF registra **todas las imágenes, bloques de texto, trazados y máscaras de transparencia** de las 141 páginas, comparados contra los documentos fuente. Incorpora tablas de resumen y ajustes, horarios programados de sueño, símbolos y bandas de estado, alertas individuales con hora escrita, etiquetas de comidas/bolos/glucosa/basal y percentiles digitalizados. Véase el [inventario de información](docs/INVENTARIO_INFORMACION.md).

Los estados leídos del gráfico llevan inicio/fin estimados, margen de error, evidencia y revisión pendiente. Los símbolos puntuales tienen ventana horaria, sin duración inventada. Las bandas solapadas y los símbolos no clasificados quedan como ambiguos. **No son todos hechos clínicos verificados.** El horario programado de sueño tampoco equivale a activación observada. Las 271 cabeceras OCR incluyen días sin gráfico; hay 231 gráficos diarios embebidos.

Los perfiles son **instantáneas de la última subida**, incluso cuando se pide un informe antiguo. Hay 40 evidencias de perfil (cuatro perfiles repetidos en diez informes), con 210 franjas; no son 40 cambios históricos de tratamiento.

La sesión web caducó durante la comprobación de actualización y el navegador dejó de estar disponible. La descarga de CSV/PDF posteriores al 27/10 sigue pendiente; la API ya aporta datos posteriores. El importador transaccional está probado con archivos reales y pruebas sintéticas. El protocolo de navegador está documentado. Se ha añadido un recopilador API local en la versión 0.5; su conexión real ya ha sido verificada. No hay tarea recurrente instalada.

Validación inicial: reimportación real con cero filas nuevas y auditoría sin errores. Última validación: **47 pruebas superadas**, 141 páginas verificadas, 357 muestras de leyenda y 231 gráficos procesados. Se han calibrado los 230 gráficos con trazas; el restante es un panel vacío por cambio de reloj. Las cinco reglas pendientes ya tienen extracción cuantitativa: 690 capas separadas, 744 anotaciones y los cuatro bolos extendidos asociados a cinco tramos diarios, sin duplicarlos. Auditoría en `data/auditorias/capas_cuantitativas_2026-10-28.json`; copia final en `data/backups/tandem_cuantitativo_2026-10-28.sqlite`. Las copias previas siguen disponibles. Los valores gráficos siguen revisables y llevan método/margen; reglas implementadas no significa validación clínica completa.

[Comparación visual de las capas extraídas](data/legend/comparacion_capas_basal.png). Las capas basales son atributos gráficos no aditivos; las cantidades originales CSV no se alteran ni se suman otra vez.

## Uso

Desde PowerShell en este directorio:

```powershell
# El entorno ya está preparado en este equipo. En otra instalación:
.\scripts\Preparar.ps1

.\scripts\Tandem.ps1 status
.\scripts\Tandem.ps1 plan --output data\sync\plan.json
# Descargar ZIP + PDF siguiendo el protocolo y crear el manifiesto:
.\scripts\Tandem.ps1 sync data\sync\descarga.json
.\scripts\Tandem.ps1 ocr
.\scripts\Tandem.ps1 extract-pdf
.\scripts\Tandem.ps1 audit --output data\auditoria.json
.\scripts\Tandem.ps1 backup data\backups\respaldo_final.sqlite

# Pruebas: usan exclusivamente datos sintéticos y bases temporales
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`sync` exige ambos archivos del mismo periodo, hace copia SQLite previa, verifica hashes si constan en el recibo, CRC del ZIP, cinco esquemas CSV y periodo del PDF. Importa todas las ventanas de un manifiesto en una transacción. Una repetición no añade duplicados normalizados y conserva la procedencia. El OCR es un paso posterior, reanudable por página; no se considera terminada una ejecución hasta comprobarlo.

El plan de la siguiente actualización ya está en `data/sync/plan_2026-10-28.json`: **21–28/10/2026**, con siete días de solapamiento sobre el último corte. No significa que esos datos nuevos estén descargados.

Para importar un respaldo anterior:

```powershell
.\scripts\Tandem.ps1 import-source 'C:\ruta\respaldo-con-carpeta-originales'
```

Para recuperar un original o consultar una página, obtener sus identificadores mediante SQLite:

```sql
SELECT id, filename, sha256, byte_count FROM artifacts WHERE mime_type IN ('application/zip','application/pdf');
SELECT id, artifact_id, page_number, ocr_status FROM pdf_pages;
SELECT * FROM v_carbohydrates ORDER BY local_timestamp;
SELECT * FROM v_daily_context WHERE local_date = '2026-10-25';
SELECT * FROM v_pending_review;
```

```powershell
.\scripts\Tandem.ps1 export-artifact 1 data\consulta\original.zip
.\scripts\Tandem.ps1 export-page 1 data\consulta\pagina.png
.\scripts\Tandem.ps1 search 'Alertas de MCG'
.\scripts\Tandem.ps1 states --day 2026-10-25
.\scripts\Tandem.ps1 events --day 2026-10-25
.\scripts\Tandem.ps1 export-visual 123 data\consulta\observacion.png
```

Los comandos de exportación rechazan sobrescribir un destino existente. Los ejemplos de identificadores son orientativos; comprobar el tipo antes de elegir extensión.

`scripts/ActualizarLocal.ps1 -Manifiesto data/sync/descarga.json` ejecuta todos los pasos locales y se detiene en el primer fallo. La conexión y la descarga oficial deben completarse antes siguiendo el protocolo.

## Conservación y límites

Los archivos originales, las filas sin transformar, las unidades y los tiempos del dispositivo permanecen disponibles. No se impone UTC ni se corrige el horario de verano/invierno. Las coincidencias entre exportaciones se agrupan por todos sus campos y número de aparición; sin un identificador de evento del fabricante, una coincidencia no prueba identidad física. Todas las filas fuente siguen conservadas para revisar esa ambigüedad.

`data/`, copias de seguridad, documentos y bases están excluidos de Git. La base SQLite no lleva cifrado propio; depende de la protección del disco y de la cuenta Windows. El repositorio no contiene contraseñas, cookies ni tokens. No se han hecho commits ni publicado datos.

Las auditorías y el registro de importaciones conservan también intentos fallidos durante el desarrollo; el estado actual de los archivos se comprueba aparte. Los valores OCR sin revisar no deben mezclarse silenciosamente con los CSV.
