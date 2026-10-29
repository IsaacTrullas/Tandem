# Diccionario de datos de Tandem Local

Este es el punto de entrada para saber qué almacena el proyecto y cómo utilizarlo sin cambiar el significado de los registros. El esquema SQLite es versión 7. La documentación generada cubre **73 tablas/vistas, 640 columnas y 371 propiedades de 74 códigos API**; las claves JSON abiertas y los campos desconocidos se declaran explícitamente como no resueltos. Cobertura de documentación no equivale a interpretación clínica completa.

| Documento | Contenido |
|---|---|
| [Diccionario por tabla y columna](data_dictionary/SCHEMA.md) | Significado, tipo SQLite, claves, restricciones declaradas, unidad, reloj, productor y SQL exacto de cada objeto. |
| [Códigos y propiedades API](data_dictionary/API_EVENTS.md) | Cada código, propiedad, enum/posición de bit, unidad declarada, conversión efectivamente aplicada y grado de interpretación. |
| [Campos originales CSV](data_dictionary/CSV.md) | Cabeceras literales de los cinco formatos, destino normalizado, unidad y significado del tiempo. |
| [Catálogo JSON](data_dictionary/dictionary.json) | Los mismos metadatos para otros programas/LLM, contratos JSON, 20 datasets del SDK y reglas comunes. No contiene filas clínicas. |
| [Integración para análisis con LLM](INTEGRACION_LLM.md) | Receta local con Reader, ejemplos sintéticos, procedencia exigida y límites de interpretación. |
| [Modelo y limitaciones](MODELO_DATOS.md) | Arquitectura, originales, revisiones, incertidumbre gráfica y estados pendientes. |
| [Inventario de información](INVENTARIO_INFORMACION.md) | Qué fuentes/evidencias se conservan y qué sigue pendiente de revisión. |
| [Alertas](ALERTAS.md) y [cronología](CRONOLOGIA_AMPLIADA.md) | Interpretación de alertas y diferencia entre fuente almacenada y representación gráfica. |

## Cómo leer el catálogo

- `meaning`: significado del campo dentro de su tabla/evento. Un nombre idéntico en otras tablas no garantiza el mismo concepto.
- `sqlite_type`, `declared_not_null`, `primary_key_position`, `foreign_keys`: estructura física. En vistas, SQLite puede no declarar tipo/clave aunque procedan de una tabla. Una PK no siempre se refleja como NOT NULL declarado; consultar SQL exacto.
- `unit` y `time_semantics`: magnitud/reloj cuando corresponde. Unidades variables requieren consultar la columna `unit`, el código o la capa fuente. Ausente no significa cero.
- `json_contract`: contrato conocido del contenedor. Un JSON de estructura abierta conserva datos cuyo significado no está catalogado; no inventar semántica para sus claves nuevas.
- `source_unit_declared`: unidad del catálogo fuente, que puede describir la codificación original. `normalized_measures` declara solo las transformaciones realmente aplicadas por `event_decode.py`, incluyendo campo, factor y unidad de salida.
- `interpretation_status`: distingue un campo descrito de un enum solo catalogado, unidad solo catalogada, reservado o no resuelto. Un enum comunitario no es una validación oficial del fabricante.
- `scale_status`: indica si hay conversión explícita del decodificador o si la escala sigue sin validar. Por ejemplo, `rate` se conserva sin inventar factor.
- `source_hashes` y `fingerprint`: identifican el código/esquema/catálogo con que se generó el documento. Los textos se codifican en UTF-8 con saltos LF para que el cambio automático CRLF de Git en Windows no cambie la huella. No incluyen registros del paciente. El hash de procedencia del catálogo fuente se conserva por separado.

Los sobres originales, documentos, texto OCR, nombres, rutas e identificadores pueden contener información personal. El catálogo describe esos campos, pero no contiene sus valores. Las credenciales están en el gestor de Windows y no forman parte del diccionario ni deben añadirse a los paquetes de análisis.

## Regeneración y comprobación

```powershell
.\.venv\Scripts\python.exe -m tandem.data_dictionary
.\.venv\Scripts\python.exe -m tandem.data_dictionary --check
.\.venv\Scripts\python.exe -m tandem.data_dictionary --check --db data\tandem.sqlite
```

La generación usa una base vacía en memoria, los SQL del proyecto y anotaciones semánticas de `tandem/semantic_definitions.py`. No abre ni copia datos del paciente. La opción `--db` abre la base real en solo lectura y comprueba exclusivamente definiciones/columnas, sin leer filas clínicas ni migrar la base. Se omiten índices de SQLite de uso interno.

Si se añade una tabla/columna, se amplía su anotación y se regenera. La generación falla si falta una descripción de almacenamiento. Si cambia un productor o el decodificador, cambia la huella y `--check` obliga a actualizar los documentos. Una propiedad nueva dentro de JSON no obtiene significado automáticamente: se mantiene como no reconocida hasta documentarla.

## Estado de interpretación

Los códigos no catalogados, incluidos 9, 22, 23 y 52 observados en el archivo, conservan sus originales. `Reader.describe_event(code)` devuelve explícitamente `unknown` cuando no existe especificación local. El significado de `param1`, `param2`, campos reservados y motivos de sesión sin enum documentado no se deduce de su coincidencia con una glucosa. Los PDF/OCR conservan sus estados de revisión: completar un inventario de bloques no valida cada símbolo.
