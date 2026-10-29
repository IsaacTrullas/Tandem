# Trabajo en Tandem

- Leer `README.md`, `docs/PROTOCOLO_SINCRONIZACION.md` y `docs/MODELO_DATOS.md` antes de actualizar datos.
- El usuario autoriza consultas y descargas. No modificar nada de la cuenta, bomba, perfiles, unidades, conexiones ni consentimientos.
- Para actualizar: plan, descarga oficial ZIP + PDF por ventana, manifiesto, `sync`, `ocr`, `extract-pdf`, auditoría y copia final. No avanzar el corte con una ventana incompleta.
- Registrar toda la información publicada en los archivos, incluidos gráficos, estados, ajustes, resúmenes y evidencia no clasificada. Consultar `docs/INVENTARIO_INFORMACION.md`; no declarar terminada una extracción sin la verificación de bloques fuente de las 141 páginas o de las nuevas que lleguen.
- Usar `docs/LEYENDA_PDF.md` y el catálogo completo por documento: 33 elementos diarios y 3 de tendencia. No tratar una leyenda como si fueran eventos del paciente. Distinguir catálogo completo, pasada de candidatos completa y extracción semántica completa; informar de adaptadores parciales y rechazos.
- La extracción incluye `quantitative_layers`, calibraciones y asociación de bolos extendidos por los dos extremos CSV. No dar por terminado un gráfico con escala sin resolver o un bolo extendido sin asociar; no sumar perfil y barras como dosis independientes. Conservar incertidumbres y casos ambiguos por observación.
- Mantener originales y procedencia. No corregir silenciosamente relojes, unidades, repeticiones o datos OCR.
- No dar por extraídos todos los intervalos/iconos de los PDF. Distinguir archivo completo, extracción estructurada y revisión humana.
- No guardar secretos en el repositorio ni extraer sesiones del navegador. Acceso caducado significa descarga pendiente.
- No añadir datos de salud a Git ni publicar. `data/` y todas las copias/bases/documentos están excluidos. No cambiar esas exclusiones para facilitar un commit.
- Ejecutar las pruebas con datos sintéticos tras cambios del importador y la auditoría después de las cargas reales.
- Informar por separado de datos importados, corte real, OCR pendiente/revisado y conexión en vivo comprobada.

- La interfaz gráfica usa Qt 6 / PySide6 por preferencia expresa del usuario. Mantener los servicios independientes de Qt, las credenciales en Windows y las tareas fuera del hilo de widgets.

- El visualizador carga ventanas acotadas (hasta 7 días) y sustituye la anterior; no cargar el histórico completo en memoria. Mantener horas originales, procedencia, parámetros observados y ambigüedades, sin interpolar IOB ni aplicar ajustes actuales al pasado.
