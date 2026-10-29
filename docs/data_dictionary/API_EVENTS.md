# Diccionario de códigos y propiedades API

Cada propiedad conserva unidad declarada, enum/bits y transformaciones realmente aplicadas por el decodificador. La procedencia es el catálogo local comunitario versionado; no una especificación clínica oficial. Unidades de catálogo sin escala validada no autorizan una conversión.

## 3 · LID_BASAL_RATE_CHANGE

Clase: `basal_rate` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| commandedBasalRate | Tasa indicada en evento3; distinta escala de279: leer conversión por código. | documented_source_field | units/hour | [{"name": "commandedBasalRate", "unit": "U/h", "source_field": "commandedBasalRate", "factor": 1}] | null |
| baseBasalRate | Tasa de perfil en evento3, unidades fuente según catálogo. | documented_source_field | units/hour | [{"name": "baseBasalRate", "unit": "U/h", "source_field": "baseBasalRate", "factor": 1}] | null |
| maxBasalRate | Límite de tasa reportado, no tasa real suministrada. | documented_source_field | units/hour | [{"name": "maxBasalRate", "unit": "U/h", "source_field": "maxBasalRate", "factor": 1}] | null |
| idp | Propiedad fuente de LID_BASAL_RATE_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| changeType | Propiedad fuente de LID_BASAL_RATE_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | bitmask | [] | {"0": "timed segment", "1": "new profile", "2": "temp rate start", "3": "temp rate end", "4": "pump suspended", "5": "pump resumed"} |

## 4 · LID_ALERT_ACTIVATED

Clase: `alert` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| alertId | Identificador de tipo de alerta en su espacio de nombres; no es event_code. | documented_source_field | enum | [] | {"0": "oaAlert_LIQ_LOW", "1": "oaAlert_USB_INSUFF_CURRENT", "2": "aaAlert_LIPO_LOW", "3": "aaAlert_LIPO_VERY_LOW", "4": "oaAlert_NVM", "5": "oaAlert_AUTO_OFF", "6": "oaAlert_BASAL_RATE_LIMIT", "7": "oaAlert_LIPO_CANT_CHARGE", "8": "oaAlert_BASAL_RATE_TOO_LOW", "9": "aaAlert_USB_NOT_RECOGNIZED", "10": "aaAlert_BAD_PC_COM", "11": "oaAlert_INCOMPLETE_BOLUS", "12": "oaAlert_INCOMPLETE_TEMP_RATE", "13": "oaAlert_INCOMPLETE_CARTRIDGE", "14": "oaAlert_INCOMPLETE_TUBING", "15": "oaAlert_INCOMPLETE_CANNULA", "16": "oaAlert_INCOMPLETE_SETTING", "17": "oaAlert_LIQ_VERY_LOW", "18": "oaAlert_ABS_MAX_BASAL_LIMIT", "19": "aaAlert_STUCK_BUTTON", "20": "aaAlert_CGM_SUPPORT_PACKAGE_ERROR", "21": "aaAlert_FSL2_SUPPORT_PACKAGE_ERROR", "22": "aaAlert_STK_CSP_REQ", "23": "oaAlert_USB_SHUTDOWN", "24": "aaAlert_CGM_MANY_SENSORS", "25": "aaAlert_CGM_GRAPH_REMOVAL", "26": "oaAlert_BASAL_RATE_LOW", "27": "aaAlert_CGM_INCOMPLETE_CAL", "28": "aaAlert_CGM_CAL_TIMEOUT", "29": "aaAlert_CGM_INVALID_TX_ID", "30": "aaAlert_DEBUG_INFO_DECLARED", "31": "oaAlert_UNUSED_1", "32": "oaAlert_OPEN_SESAME", "33": "aaAlert_QUICK_BOLUS_ABORT", "34": "aaAlert_MANY_FAILED_QUICK_BOLUS", "35": "Alert_AP_ALERT", "36": "aaAlert_STK_EXCHANGE_REQ", "37": "aaAlert_STK_ODYSSEY_REQ", "38": "aaAlert_STK_INVALID", "39": "aaAlert_CGM_TX_EOL", "40": "aaAlert_CGM_BLE_SD", "41": "aaAlert_CGM_BLE_HW_WATCHDOG", "42": "aaAlert_CGM_BLE_HW_TIMEOUT", "43": "aaAlert_CGM_INCOMPATIBLE", "44": "aaAlert_CGM_TX_EXPIRING_SOON_1", "45": "aaAlert_CGM_TX_EXPIRING_SOON_2", "46": "aaAlert_CGM_TX_EXPIRING_STARTUP", "47": "oaAlert_TZ_INCOMPLETE_SETTING", "48": "aaAlert_CGM_NO_READINGS", "49": "aaAlert_PRIME_LIMIT", "50": "aaAlert_TZ_HYPER_LIGHT", "51": "aaAlert_TZ_HYPO_LIGHT", "52": "aaAlert_TZ_IIDM", "53": "aaAlert_BLE_CRASH_DUMP", "54": "aaAlert_MH_PAIRED", "55": "aaAlert_BLE_HW_ERROR", "56": "aaAlert_USER_SET_MAX_BASAL", "57": "aaAlert_SENSOR", "58": "aaAlert_COM_LOG_ERROR_LOGGED", "59": "alert_FCL_AUTOMATION_OFF", "60": "oaAlert_CONTROLLER_CONNECTION_LOST", "61": "aaAlert_LIPO_SUPER_LOW", "62": "aaAlert_LIPO_INSUFF_POWER", "63": "oaAlert_BTLE_PAIRING_TIMEOUT", "64": "NUM_ALERTS"} |
| faultLocatorData | Dato técnico de localización de fallo preservado; significado/unidad clínica no documentados. | documented_source_field | — | [] | null |
| param1 | Parámetro interno dependiente de tipo de alerta; sin significado/unidad generales documentados. | documented_source_field | — | [] | null |
| param2 | Parámetro interno dependiente de tipo de alerta; sin significado/unidad generales documentados. | documented_source_field | — | [] | null |

## 5 · LID_ALARM_ACTIVATED

Clase: `alarm` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| alarmId | Identificador de tipo de alarma en su espacio de nombres; no es alertId ni event_code. | documented_source_field | enum | [] | {"0": "Alarm_DELIVERY_NOT_STOPPED", "1": "Alarm_SPOOL_MOVE", "2": "Alarm_OCCLUSION", "3": "Alarm_NO_STARTUP_ACK", "4": "Alarm_OBE", "5": "Alarm_P2", "6": "Alarm_VENT_NOT_WORKING", "7": "Alarm_AUTO_OFF_TRIGGERED", "8": "Alarm_LIQ_OUT", "9": "Alarm_LIQ_EX", "10": "Alarm_TEMPERATURE_OOR", "11": "Alarm_TEMPERATURE_XDCR", "12": "Alarm_LIPO_VERY_LOW", "13": "Alarm_FLUID_CHANGE_obsolete", "14": "Alarm_USER_DATE_INVALID", "15": "Alarm_LIPO_TEMPERATURE", "16": "Alarm_DELIVERY_REQUEST_FAIL", "17": "Alarm_CANT_HOME_obsolete", "18": "Alarm_STATE_SUSPEND", "19": "Alarm_UNICORN_DO_NOT_USE", "20": "Alarm_MOTOR_PICASSO", "21": "Alarm_PRESSURE_DISAGREE", "22": "Alarm_STUCK_BUTTON", "23": "Alarm_GENERIC", "24": "Alarm_PATM", "25": "Alarm_CART_REMOVED", "26": "Alarm_OCCLUSION_THE_YOUNGER", "27": "Alarm_UNUSED_1", "28": "Alarm_UNUSED_2", "29": "Alarm_MOTOR_CART_RANGE_LOW", "30": "Alarm_MOTOR_STALL", "31": "Alarm_MOTOR_VENT_STALL", "32": "Alarm_NO_CARTRIDGE_DETECTED", "33": "Alarm_LIPO_INSUFF_POWER", "34": "Alarm_MOTOR_HALL_EFFECT_FAIL", "35": "Alarm_MOTOR_FAILURE_MODE", "36": "Alarm_MOTOR_PRIME_STALL_OBE", "37": "Alarm_AUXCPU_SYSTEM_RESET", "38": "NUM_ALARMS"} |
| faultLocatorData | Dato técnico de localización de fallo preservado; significado/unidad clínica no documentados. | documented_source_field | — | [] | null |
| param1 | Parámetro interno dependiente de tipo de alerta; sin significado/unidad generales documentados. | documented_source_field | — | [] | null |
| param2 | Parámetro interno dependiente de tipo de alerta; sin significado/unidad generales documentados. | documented_source_field | — | [] | null |

## 6 · LID_MALFUNCTION_ACTIVATED

Clase: `malfunction` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| malfId | Propiedad fuente de LID_MALFUNCTION_ACTIVATED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "Malf_SOFTWARE", "1": "Malf_CPU_CORE", "2": "Malf_ARM_MSP_COM", "3": "Malf_SENSOR", "4": "Malf_LIPO", "5": "Malf_TOUCHSCREEN", "6": "Malf_NVM", "7": "Malf_DISPLAY", "8": "Malf_MSP", "9": "Malf_MOTOR", "10": "Malf_EXTERNAL_BINS", "11": "Malf_SW_INIT", "12": "Malf_VIBE", "13": "Malf_PERIPH_POWER", "14": "Malf_P2", "15": "Malf_DATALOG", "16": "Malf_SPEAKER", "17": "Malf_MSP_SUPPLY", "18": "Malf_CAL_DATA", "19": "Malf_BTLE", "20": "Malf_AP", "21": "Malf_RTC", "22": "Malf_ARM_BLE_COM", "23": "Malf_OVERTRAVEL_STALL", "24": "Malf_UNDERTRAVEL_STALL", "25": "Malf_PUSHOFF_STALL", "26": "Malf_HW_CRYPTO_FAIL", "27": "NUM_MALFUNCTIONS"} |
| faultLocatorData | Dato técnico de localización de fallo preservado; significado/unidad clínica no documentados. | documented_source_field | — | [] | null |
| param1 | Parámetro interno dependiente de tipo de alerta; sin significado/unidad generales documentados. | documented_source_field | — | [] | null |
| param2 | Parámetro interno dependiente de tipo de alerta; sin significado/unidad generales documentados. | documented_source_field | — | [] | null |

## 8 · LID_ALARM_ACK

Clase: `alarm_acknowledged` · estado: `reference_named`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| alarmId | Identificador de tipo de alarma en su espacio de nombres; no es alertId ni event_code. | documented_source_field | — | [] | null |

## 11 · LID_PUMPING_SUSPENDED

Clase: `suspend` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| preSuspendState | Propiedad fuente de LID_PUMPING_SUSPENDED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | enum | [] | null |
| insulinAmount | Propiedad fuente de LID_PUMPING_SUSPENDED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | units | [] | null |
| suspendReason | Propiedad fuente de LID_PUMPING_SUSPENDED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "User Aborted", "1": "Terminated by Alarm", "2": "Terminated by Malfunction", "6": "Auto Suspend by PLGS"} |
| rpaTimeout | Propiedad fuente de LID_PUMPING_SUSPENDED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | minutes | [] | null |

## 12 · LID_PUMPING_RESUMED

Clase: `resume` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| preResumeState | Propiedad fuente de LID_PUMPING_RESUMED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | enum | [] | null |
| insulinAmount | Propiedad fuente de LID_PUMPING_RESUMED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | units | [] | null |

## 13 · LID_TIME_CHANGED

Clase: `clock_change` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| timePrior | Propiedad fuente de LID_TIME_CHANGED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ms | [] | null |
| timeAfter | Propiedad fuente de LID_TIME_CHANGED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ms | [] | null |
| rawRtcTime | Propiedad fuente de LID_TIME_CHANGED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ms | [] | null |

## 14 · LID_DATE_CHANGED

Clase: `clock_change` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| datePrior | Propiedad fuente de LID_DATE_CHANGED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | day | [] | null |
| dateAfter | Propiedad fuente de LID_DATE_CHANGED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | day | [] | null |
| rawRtcTime | Propiedad fuente de LID_DATE_CHANGED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ms | [] | null |

## 16 · LID_BG_READING_TAKEN

Clase: `bg` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| bg | Glucemia asociada al registro/solicitud, en mg/dL; origen según bgEntryType y bgSourceType. | documented_source_field | mg/dL | [{"name": "bg", "unit": "mg/dL", "source_field": "bg", "factor": 1}] | null |
| cgmCalibration | Marca de uso de la entrada para calibrar: 1sí, 0no. No prueba éxito ni sustitución de sensor. | documented_source_field | enum | [] | {"0": "No, it was not used to Calibrate.", "1": "Yes, it was used to calibrate."} |
| bgEntryType | Origen de entrada: teclado o valor autopoblado de MCG según enum. No toda entrada es una medición capilar. | documented_source_field | enum | [] | {"0": "Manual Entry by the User via Numpad", "1": "Auto Populated BG using CGM"} |
| iob | Insulina activa reportada en U en los códigos identificados por pump_context.IOB_CODES; conservar hora, sin interpolación. | documented_source_field | units | [] | null |
| targetBg | Objetivo de glucosa reportado, no lectura medida. | documented_source_field | mg/dL | [] | null |
| isf | Sensibilidad/factor de corrección reportado, en (mg/dL)/U según fuente. | documented_source_field | (mg/dL)/unit | [] | null |
| selectedIob | Selección/modelo de IOB, enum sin magnitud de insulina. | documented_source_field | enum | [] | {"0": "Mudaliar IOB", "1": "Swan IOB Meal"} |
| bgSourceType | Procedencia local/remota de la entrada según enum. | documented_source_field | enum | [] | {"0": "Local Pump entry", "1": "Remote entry"} |

## 20 · LID_BOLUS_COMPLETED

Clase: `bolus_completed` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| completionStatus | Estado fuente de finalización del componente; conservar incompletos/cancelados. | documented_source_field | enum | [] | {"0": "User Aborted", "1": "Terminated by Alarm", "2": "Terminated by Malfunction", "3": "Completed", "4": "Reserved - Used in non-commercial software", "5": "Bolus rejected", "6": "Aborted by PLGS", "7": "Reserved", "8": "Reserved - For future use"} |
| bolusId | Identificador de asociación de fases de un bolo, condicionado por dispositivo y ventana temporal; puede repetirse. | documented_source_field | — | [] | null |
| iob | Insulina activa reportada en U en los códigos identificados por pump_context.IOB_CODES; conservar hora, sin interpolación. | documented_source_field | units | [] | null |
| insulinDelivered | Cantidad reportada para el componente de bolo en20/21; no sumar otra vez al total280. | documented_source_field | units | [{"name": "insulinDelivered", "unit": "U", "source_field": "insulinDelivered", "factor": 1}] | null |
| insulinRequested | Cantidad solicitada del componente correspondiente, no cantidad suministrada. | documented_source_field | units | [{"name": "insulinRequested", "unit": "U", "source_field": "insulinRequested", "factor": 1}] | null |

## 21 · LID_BOLEX_COMPLETED

Clase: `bolus_extended_completed` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| completionStatus | Estado fuente de finalización del componente; conservar incompletos/cancelados. | documented_source_field | enum | [] | {"0": "User Aborted", "1": "Terminated by Alarm", "2": "Terminated by Malfunction", "3": "Completed", "4": "Reserved - Used in non-commercial software", "5": "Bolus rejected", "6": "Aborted by PLGS", "7": "Reserved", "8": "Reserved - For future use"} |
| bolusId | Identificador de asociación de fases de un bolo, condicionado por dispositivo y ventana temporal; puede repetirse. | documented_source_field | — | [] | null |
| iob | Insulina activa reportada en U en los códigos identificados por pump_context.IOB_CODES; conservar hora, sin interpolación. | documented_source_field | units | [] | null |
| insulinDelivered | Cantidad reportada para el componente de bolo en20/21; no sumar otra vez al total280. | documented_source_field | units | [{"name": "insulinDelivered", "unit": "U", "source_field": "insulinDelivered", "factor": 1}] | null |
| insulinRequested | Cantidad solicitada del componente correspondiente, no cantidad suministrada. | documented_source_field | units | [{"name": "insulinRequested", "unit": "U", "source_field": "insulinRequested", "factor": 1}] | null |

## 26 · LID_ALERT_CLEARED

Clase: `alert_cleared` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| alertId | Identificador de tipo de alerta en su espacio de nombres; no es event_code. | documented_source_field | enum | [] | {"0": "oaAlert_LIQ_LOW", "1": "oaAlert_USB_INSUFF_CURRENT", "2": "aaAlert_LIPO_LOW", "3": "aaAlert_LIPO_VERY_LOW", "4": "oaAlert_NVM", "5": "oaAlert_AUTO_OFF", "6": "oaAlert_BASAL_RATE_LIMIT", "7": "oaAlert_LIPO_CANT_CHARGE", "8": "oaAlert_BASAL_RATE_TOO_LOW", "9": "aaAlert_USB_NOT_RECOGNIZED", "10": "aaAlert_BAD_PC_COM", "11": "oaAlert_INCOMPLETE_BOLUS", "12": "oaAlert_INCOMPLETE_TEMP_RATE", "13": "oaAlert_INCOMPLETE_CARTRIDGE", "14": "oaAlert_INCOMPLETE_TUBING", "15": "oaAlert_INCOMPLETE_CANNULA", "16": "oaAlert_INCOMPLETE_SETTING", "17": "oaAlert_LIQ_VERY_LOW", "18": "oaAlert_ABS_MAX_BASAL_LIMIT", "19": "aaAlert_STUCK_BUTTON", "20": "aaAlert_CGM_SUPPORT_PACKAGE_ERROR", "21": "aaAlert_FSL2_SUPPORT_PACKAGE_ERROR", "22": "aaAlert_STK_CSP_REQ", "23": "oaAlert_USB_SHUTDOWN", "24": "aaAlert_CGM_MANY_SENSORS", "25": "aaAlert_CGM_GRAPH_REMOVAL", "26": "oaAlert_BASAL_RATE_LOW", "27": "aaAlert_CGM_INCOMPLETE_CAL", "28": "aaAlert_CGM_CAL_TIMEOUT", "29": "aaAlert_CGM_INVALID_TX_ID", "30": "aaAlert_DEBUG_INFO_DECLARED", "31": "oaAlert_UNUSED_1", "32": "oaAlert_OPEN_SESAME", "33": "aaAlert_QUICK_BOLUS_ABORT", "34": "aaAlert_MANY_FAILED_QUICK_BOLUS", "35": "Alert_AP_ALERT", "36": "aaAlert_STK_EXCHANGE_REQ", "37": "aaAlert_STK_ODYSSEY_REQ", "38": "aaAlert_STK_INVALID", "39": "aaAlert_CGM_TX_EOL", "40": "aaAlert_CGM_BLE_SD", "41": "aaAlert_CGM_BLE_HW_WATCHDOG", "42": "aaAlert_CGM_BLE_HW_TIMEOUT", "43": "aaAlert_CGM_INCOMPATIBLE", "44": "aaAlert_CGM_TX_EXPIRING_SOON_1", "45": "aaAlert_CGM_TX_EXPIRING_SOON_2", "46": "aaAlert_CGM_TX_EXPIRING_STARTUP", "47": "oaAlert_TZ_INCOMPLETE_SETTING", "48": "aaAlert_CGM_NO_READINGS", "49": "aaAlert_PRIME_LIMIT", "50": "aaAlert_TZ_HYPER_LIGHT", "51": "aaAlert_TZ_HYPO_LIGHT", "52": "aaAlert_TZ_IIDM", "53": "aaAlert_BLE_CRASH_DUMP", "54": "aaAlert_MH_PAIRED", "55": "aaAlert_BLE_HW_ERROR", "56": "aaAlert_USER_SET_MAX_BASAL", "57": "aaAlert_SENSOR", "58": "aaAlert_COM_LOG_ERROR_LOGGED", "59": "alert_FCL_AUTOMATION_OFF", "60": "oaAlert_CONTROLLER_CONNECTION_LOST", "61": "aaAlert_LIPO_SUPER_LOW", "62": "aaAlert_LIPO_INSUFF_POWER", "63": "oaAlert_BTLE_PAIRING_TIMEOUT", "64": "NUM_ALERTS"} |
| faultLocatorData | Dato técnico de localización de fallo preservado; significado/unidad clínica no documentados. | documented_source_field | — | [] | null |

## 27 · LID_ALERT_ACK

Clase: `alert_acknowledged` · estado: `reference_named`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| alertId | Identificador de tipo de alerta en su espacio de nombres; no es event_code. | documented_source_field | — | [] | null |
| ackSource | Origen del reconocimiento según enum; no demuestra resolución. | documented_source_field | — | [] | null |

## 28 · LID_ALARM_CLEARED

Clase: `alarm_cleared` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| alarmId | Identificador de tipo de alarma en su espacio de nombres; no es alertId ni event_code. | documented_source_field | enum | [] | {"0": "Alarm_DELIVERY_NOT_STOPPED", "1": "Alarm_SPOOL_MOVE", "2": "Alarm_OCCLUSION", "3": "Alarm_NO_STARTUP_ACK", "4": "Alarm_OBE", "5": "Alarm_P2", "6": "Alarm_VENT_NOT_WORKING", "7": "Alarm_AUTO_OFF_TRIGGERED", "8": "Alarm_LIQ_OUT", "9": "Alarm_LIQ_EX", "10": "Alarm_TEMPERATURE_OOR", "11": "Alarm_TEMPERATURE_XDCR", "12": "Alarm_LIPO_VERY_LOW", "13": "Alarm_FLUID_CHANGE_obsolete", "14": "Alarm_USER_DATE_INVALID", "15": "Alarm_LIPO_TEMPERATURE", "16": "Alarm_DELIVERY_REQUEST_FAIL", "17": "Alarm_CANT_HOME_obsolete", "18": "Alarm_STATE_SUSPEND", "19": "Alarm_UNICORN_DO_NOT_USE", "20": "Alarm_MOTOR_PICASSO", "21": "Alarm_PRESSURE_DISAGREE", "22": "Alarm_STUCK_BUTTON", "23": "Alarm_GENERIC", "24": "Alarm_PATM", "25": "Alarm_CART_REMOVED", "26": "Alarm_OCCLUSION_THE_YOUNGER", "27": "Alarm_UNUSED_1", "28": "Alarm_UNUSED_2", "29": "Alarm_MOTOR_CART_RANGE_LOW", "30": "Alarm_MOTOR_STALL", "31": "Alarm_MOTOR_VENT_STALL", "32": "Alarm_NO_CARTRIDGE_DETECTED", "33": "Alarm_LIPO_INSUFF_POWER", "34": "Alarm_MOTOR_HALL_EFFECT_FAIL", "35": "Alarm_MOTOR_FAILURE_MODE", "36": "Alarm_MOTOR_PRIME_STALL_OBE", "37": "Alarm_AUXCPU_SYSTEM_RESET", "38": "NUM_ALARMS"} |

## 33 · LID_CARTRIDGE_FILLED

Clase: `cartridge_fill` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| insulinVolume | Volumen/cantidad de llenado reportado; no insulina terapéutica suministrada al paciente. | documented_source_field | units | [{"name": "insulinVolume", "unit": "U", "source_field": "insulinVolume", "factor": 1}] | null |
| v2Volume | Propiedad fuente de LID_CARTRIDGE_FILLED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | units | [] | null |

## 34 · ChargingStarted

Clase: `charging_started` · estado: `provisional_reference`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| abc | Propiedad fuente de ChargingStarted; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| ibc | Propiedad fuente de ChargingStarted; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| liPoMV | Propiedad fuente de ChargingStarted; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | mV | [] | null |
| batteryTemperature | Propiedad fuente de ChargingStarted; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| fullChargeCapacity | Propiedad fuente de ChargingStarted; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| remainingChargeCapacity | Propiedad fuente de ChargingStarted; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| reservedD12 | Campo reservado: sin significado clínico asignado. | reserved_uninterpreted | — | [] | null |
| wombatMotorTemp | Propiedad fuente de ChargingStarted; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |

## 35 · ChargingStopped

Clase: `charging_stopped` · estado: `provisional_reference`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| abc | Propiedad fuente de ChargingStopped; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| ibc | Propiedad fuente de ChargingStopped; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| liPoMV | Propiedad fuente de ChargingStopped; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | mV | [] | null |
| batteryTemperature | Propiedad fuente de ChargingStopped; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| fullChargeCapacity | Propiedad fuente de ChargingStopped; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| remainingChargeCapacity | Propiedad fuente de ChargingStopped; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| reservedD12 | Campo reservado: sin significado clínico asignado. | reserved_uninterpreted | — | [] | null |
| wombatMotorTemp | Propiedad fuente de ChargingStopped; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |

## 36 · LID_USB_CONNECTED

Clase: `usb_connected` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| negotiatedCurrent | Propiedad fuente de LID_USB_CONNECTED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | mA | [] | null |

## 37 · LID_USB_DISCONNECTED

Clase: `usb_disconnected` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| negotiatedCurrent | Propiedad fuente de LID_USB_DISCONNECTED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | mA | [] | null |

## 48 · LID_CARBS_ENTERED

Clase: `carb_entry` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| carbs | Propiedad fuente de LID_CARBS_ENTERED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | carbs | [] | null |

## 53 · LID_SHELF_MODE

Clase: `storage_mode` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| msecSinceReset | Propiedad fuente de LID_SHELF_MODE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ms | [] | null |
| liPoCurrent | Propiedad fuente de LID_SHELF_MODE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | mA | [] | null |
| liPoAbc | Propiedad fuente de LID_SHELF_MODE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | % | [] | null |
| liPoIbc | Propiedad fuente de LID_SHELF_MODE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | % | [] | null |
| liPoRemCap | Propiedad fuente de LID_SHELF_MODE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | mAh | [] | null |
| liPoMV | Propiedad fuente de LID_SHELF_MODE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | mV | [] | null |

## 55 · LID_BOLUS_ACTIVATED

Clase: `bolus_started` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| bolusId | Identificador de asociación de fases de un bolo, condicionado por dispositivo y ventana temporal; puede repetirse. | documented_source_field | — | [] | null |
| selectedIob | Selección/modelo de IOB, enum sin magnitud de insulina. | documented_source_field | enum | [] | {"0": "Mudaliar IOB", "1": "Algorithm IOB"} |
| iob | Insulina activa reportada en U en los códigos identificados por pump_context.IOB_CODES; conservar hora, sin interpolación. | documented_source_field | units | [] | null |
| bolusSize | Cantidad de activación solicitada en55, no confirmación de suministro. | documented_source_field | units | [{"name": "bolusSize", "unit": "U", "source_field": "bolusSize", "factor": 1}] | null |

## 57 · LID_IDP_MSG2

Clase: `settings` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| idp | Propiedad fuente de LID_IDP_MSG2; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| name8 | Propiedad fuente de LID_IDP_MSG2; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |
| name9 | Propiedad fuente de LID_IDP_MSG2; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |
| name10 | Propiedad fuente de LID_IDP_MSG2; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |
| name11 | Propiedad fuente de LID_IDP_MSG2; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |
| name12 | Propiedad fuente de LID_IDP_MSG2; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |
| name13 | Propiedad fuente de LID_IDP_MSG2; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |
| name14 | Propiedad fuente de LID_IDP_MSG2; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |
| name15 | Propiedad fuente de LID_IDP_MSG2; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |

## 59 · LID_BOLEX_ACTIVATED

Clase: `bolus_extended_started` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| bolusId | Identificador de asociación de fases de un bolo, condicionado por dispositivo y ventana temporal; puede repetirse. | documented_source_field | — | [] | null |
| selectedIob | Selección/modelo de IOB, enum sin magnitud de insulina. | documented_source_field | enum | [] | {"0": "Mudaliar IOB", "1": "Swan IOB Meal"} |
| iob | Insulina activa reportada en U en los códigos identificados por pump_context.IOB_CODES; conservar hora, sin interpolación. | documented_source_field | units | [] | null |
| bolexSize | Cantidad de activación del extendido en59; conservar asociación con el final21. | documented_source_field | units | [{"name": "bolexSize", "unit": "U", "source_field": "bolexSize", "factor": 1}] | null |

## 60 · LID_DATA_LOG_CORRUPTION

Clase: `log_corruption` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| block | Propiedad fuente de LID_DATA_LOG_CORRUPTION; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| reason | Propiedad fuente de LID_DATA_LOG_CORRUPTION; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "Invalid Header Id", "1": "Bad Integrity", "2": "Invalid Block", "3": "Spare Deactivation Failed", "4": "Invalid Sequence Number", "5": "Pattern Mismatch", "6": "Bad First Block", "7": "Discovery Bad Sequence Number Increment"} |

## 61 · LID_CANNULA_FILLED

Clase: `cannula_fill` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| primeSize | Cantidad de cebado/llenado; no sumar como bolo terapéutico. | documented_source_field | units | [{"name": "primeSize", "unit": "U", "source_field": "primeSize", "factor": 1}] | null |
| completionStatus | Estado fuente de finalización del componente; conservar incompletos/cancelados. | documented_source_field | enum | [] | {"0": "User Aborted (Does not apply to Mobi)", "1": "Terminated by Alarm", "2": "Terminated by Malfunction", "3": "Completed"} |
| infusionSetType | Propiedad fuente de LID_CANNULA_FILLED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "Default (tubed)", "1": "Tubed", "2": "Tubeless"} |

## 63 · LID_TUBING_FILLED

Clase: `tubing_fill` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| primeSize | Cantidad de cebado/llenado; no sumar como bolo terapéutico. | documented_source_field | units | [{"name": "primeSize", "unit": "U", "source_field": "primeSize", "factor": 1}] | null |
| completionStatus | Estado fuente de finalización del componente; conservar incompletos/cancelados. | documented_source_field | enum | [] | {"0": "User Aborted", "1": "Terminated by Alarm", "2": "Terminated by Malfunction", "3": "Completed"} |
| position | Propiedad fuente de LID_TUBING_FILLED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | counts | [] | null |

## 64 · LID_BOLUS_REQUESTED_MSG1

Clase: `bolus_request` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| bolusId | Identificador de asociación de fases de un bolo, condicionado por dispositivo y ventana temporal; puede repetirse. | documented_source_field | — | [] | null |
| bolusType | Lista de posiciones de bits, no un entero bitmask a reinterpretar. Now/Later/Correction/Carb/Override describen el tipo. | documented_source_field | enum | [] | {"0": "Insulin", "1": "Carb", "2": "Automatic Correction", "3": "Remote"} |
| correctionBolusIncluded | Propiedad fuente de LID_BOLUS_REQUESTED_MSG1; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "False", "1": "True"} |
| carbAmount | Gramos introducidos en solicitud; no evento de ingesta confirmado. | documented_source_field | grams | [{"name": "carbAmount", "unit": "g", "source_field": "carbAmount", "factor": 1}] | null |
| bg | Glucemia asociada al registro/solicitud, en mg/dL; origen según bgEntryType y bgSourceType. | documented_source_field | mg/dL | [{"name": "bg", "unit": "mg/dL", "source_field": "bg", "factor": 1}] | null |
| iob | Insulina activa reportada en U en los códigos identificados por pump_context.IOB_CODES; conservar hora, sin interpolación. | documented_source_field | units | [] | null |
| carbRatio | Ratio I:C codificado; decoder multiplica por0,001 para normalizar g/U. | documented_source_field | 1ct = 0.001 g/u | [{"name": "carbRatio", "unit": "g/U", "source_field": "carbRatio", "factor": 0.001}] | null |

## 65 · LID_BOLUS_REQUESTED_MSG2

Clase: `bolus_request_options` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| bolusId | Identificador de asociación de fases de un bolo, condicionado por dispositivo y ventana temporal; puede repetirse. | documented_source_field | — | [] | null |
| options | Opción/tipo de bolo declarado: normal, extendido, automático, Bluetooth, etc., según enum. | documented_source_field | enum | [] | {"0": "Standard Bolus", "1": "Extended Bolus", "2": "Quick Bolus", "3": "Automatic Bolus", "4": "BLE Standard Bolus", "5": "BLE Extended Bolus", "6": "Eating Soon Automatic Bolus", "7": "Late Bolus", "8": "BLE with AID Recommendation Bolus"} |
| standardPercent | Porcentaje estándar/inmediato solicitado. | documented_source_field | % | [] | null |
| duration | Duración de opción de bolo en minutos según catálogo; no probar fin físico por sumar esta duración. | documented_source_field | minutes | [] | null |
| isf | Sensibilidad/factor de corrección reportado, en (mg/dL)/U según fuente. | documented_source_field | (mg/dL)/unit | [] | null |
| targetBg | Objetivo de glucosa reportado, no lectura medida. | documented_source_field | mg/dL | [] | null |
| userOverride | Indicador de modificación del tamaño por el usuario; consultar enum, no confundir con estado de entrega. | documented_source_field | enum | [] | {"0": "No, user did not override the bolus size", "1": "Yes, user did override the bolus size"} |
| declinedCorrection | Indicador de rechazo de corrección recomendada según enum. | documented_source_field | enum | [] | {"0": "No, user did not decline the recommended correction", "1": "Yes, user declined the recommended correction"} |
| selectedIob | Selección/modelo de IOB, enum sin magnitud de insulina. | documented_source_field | enum | [] | {"0": "Mudaliar IOB", "1": "Swan IOB Meal"} |

## 66 · LID_BOLUS_REQUESTED_MSG3

Clase: `bolus_request_amounts` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| bolusId | Identificador de asociación de fases de un bolo, condicionado por dispositivo y ventana temporal; puede repetirse. | documented_source_field | — | [] | null |
| queued | Propiedad fuente de LID_BOLUS_REQUESTED_MSG3; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Boolean | [] | null |
| foodBolusSize | Componente para carbohidratos del cálculo solicitado del bolo; no alimento ingerido ni dosis adicional. | documented_source_field | units | [{"name": "foodBolusSize", "unit": "U", "source_field": "foodBolusSize", "factor": 1}] | null |
| correctionBolusSize | Componente de corrección del cálculo solicitado; no suma adicional a totalBolusSize. | documented_source_field | units | [{"name": "correctionBolusSize", "unit": "U", "source_field": "correctionBolusSize", "factor": 1}] | null |
| totalBolusSize | Total solicitado del cálculo; no total independiente de las fases de entrega. | documented_source_field | units | [{"name": "totalBolusSize", "unit": "U", "source_field": "totalBolusSize", "factor": 1}] | null |

## 69 · LID_IDP

Clase: `settings` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| idp | Propiedad fuente de LID_IDP; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| status | Propiedad fuente de LID_IDP; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "new", "1": "copy", "2": "delete", "3": "activate", "4": "rename"} |
| sourceIdp | Propiedad fuente de LID_IDP; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| name0 | Propiedad fuente de LID_IDP; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |
| name1 | Propiedad fuente de LID_IDP; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |
| name2 | Propiedad fuente de LID_IDP; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |
| name3 | Propiedad fuente de LID_IDP; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |
| name4 | Propiedad fuente de LID_IDP; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |
| name5 | Propiedad fuente de LID_IDP; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |
| name6 | Propiedad fuente de LID_IDP; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |
| name7 | Propiedad fuente de LID_IDP; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ASCII | [] | null |

## 81 · LID_DAILY_BASAL

Clase: `basal_daily_summary` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| dailyTotalBasal | Resumen acumulado basal reportado; no sumar con dosis/intervalos de sus componentes. | documented_source_field | units | [{"name": "dailyTotalBasal", "unit": "U", "source_field": "dailyTotalBasal", "factor": 1}] | null |
| lastBasalRate | Propiedad fuente de LID_DAILY_BASAL; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | units/hour | [] | null |
| iob | Insulina activa reportada en U en los códigos identificados por pump_context.IOB_CODES; conservar hora, sin interpolación. | documented_source_field | units | [] | null |
| displayInHistory | Propiedad fuente de LID_DAILY_BASAL; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| abc | Propiedad fuente de LID_DAILY_BASAL; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | percent | [] | null |
| liPoMV | Propiedad fuente de LID_DAILY_BASAL; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | millivolts | [] | null |

## 90 · LID_NEW_DAY

Clase: `new_day` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| commandedBasalRate | Tasa indicada en evento3; distinta escala de279: leer conversión por código. | documented_source_field | units/hour | [] | null |
| featuresBitmask | Propiedad fuente de LID_NEW_DAY; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Bitmask | [] | null |
| featureBitmaskIndex | Propiedad fuente de LID_NEW_DAY; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Bitmask | [] | null |

## 99 · LID_ARM_INIT

Clase: `device_initialization` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| version | Propiedad fuente de LID_ARM_INIT; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| configABits | Propiedad fuente de LID_ARM_INIT; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Bitmask | [] | null |
| configBBits | Propiedad fuente de LID_ARM_INIT; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Bitmask | [] | null |
| numLogEntries | Propiedad fuente de LID_ARM_INIT; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |

## 140 · LID_PLGS_PERIODIC

Clase: `basal_algorithm_status` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| timestamp | Propiedad fuente de LID_PLGS_PERIODIC; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| fmr | Propiedad fuente de LID_PLGS_PERIODIC; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | mg/dL | [] | null |
| pgv | Propiedad fuente de LID_PLGS_PERIODIC; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | mg/dL | [] | null |
| fmrStatus | Propiedad fuente de LID_PLGS_PERIODIC; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "No FMR", "1": "Periodic glucose reading", "2": "Calibration response glucose reading", "3": "Sensor session stopped (no FMR)", "4": "Sensor session started (no FMR)", "5": "Calibration entered (no FMR)", "6": "Pumping event (no FMR)"} |
| pgvValid | Propiedad fuente de LID_PLGS_PERIODIC; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Boolean | [] | null |
| ruleState | Propiedad fuente de LID_PLGS_PERIODIC; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | Bitmask | [] | {"0": "HO_SUSPEND_RULE", "1": "HO_RECOVERY_RULE", "2": "HO_UNAVAILABLE_RULE"} |
| hoMinState | Propiedad fuente de LID_PLGS_PERIODIC; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "On and available", "1": "On and suspended", "2": "False", "3": "On and not available"} |
| status | Propiedad fuente de LID_PLGS_PERIODIC; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | Bitmask | [] | {"0": "Suspend Predicted", "1": "Suspend Current", "2": "Unused", "3": "Unused", "4": "Resume EGV Rise", "5": "Unused", "6": "Resume Nadir Lock", "7": "Unavailable - Time Small", "8": "Unavailable - Suspend Override", "9": "Unavailable - CGM Off", "10": "Unavailable - High EGV", "11": "Unavailable - Not Therapy", "12": "Unavailable - Bolus Active", "13": "Unavailable - No Current"} |

## 171 · LID_CGM_ALERT_ACTIVATED

Clase: `cgm_alert` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| dalertId | Identificador de tipo de alerta del sensor en su espacio de nombres. | documented_source_field | enum | [] | {"0": "Alert_CGM_DEPRECATED_3", "1": "Alert_CGM_FIXED_LOW", "2": "Alert_CGM_USER_HIGH_EGV", "3": "Alert_CGM_USER_LOW_EGV", "4": "Alert_CGM_CALIBRATION_REQUEST", "5": "Alert_CGM_RISE", "6": "Alert_CGM_RAPID_RISE", "7": "Alert_CGM_FALL", "8": "Alert_CGM_RAPID_FALL", "9": "Alert_CGM_CALIB_ERROR", "10": "Alert_CGM_CALIB_HIGH_WEDGE", "11": "Alert_CGM_SENSOR_FAILED", "12": "Alert_CGM_SENSOR_EXPIRING", "13": "Alert_CGM_SENSOR_EXPIRED", "14": "Alert_CGM_OUT_OF_RANGE", "15": "Alert_CGM_DEPRECATED", "16": "Alert_CGM_CALIB_START_FIRST", "17": "Alert_CGM_CALIB_START_SECOND", "18": "Alert_CGM_CALIB_REQUIRED", "19": "Alert_CGM_LOW_TX_BATTERY", "20": "Alert_CGM_TRANSMITTER_ERROR", "21": "Alert_CGM_DEPRECATED_2", "22": "Alert_CGM_SENSOR_EXPIRING_SOON", "23": "Alert_CGM_DEPRECATED_4", "24": "Alert_CGM_URGENT_LOW_SOON", "25": "Alert_CGM_SENSOR_REUSE", "26": "Alert_CGM_SENSOR_TEMP", "27": "Alert_CGM_CONNECTION_ERROR", "28": "Alert_CGM_CHECK_SENSOR", "29": "Alert_CGM_EGV_UNUSABLE", "30": "Alert_CGM_UNUSED1", "31": "Alert_CGM_GRACE_PERIOD_START", "32": "Alert_CGM_GRACE_PERIOD_EXPIRING_SOON", "33": "NUM_CGM_ALERTS"} |
| faultLocatorData | Dato técnico de localización de fallo preservado; significado/unidad clínica no documentados. | documented_source_field | — | [] | null |
| param1 | Parámetro interno dependiente de tipo de alerta; sin significado/unidad generales documentados. | documented_source_field | — | [] | null |
| param2 | Parámetro interno dependiente de tipo de alerta; sin significado/unidad generales documentados. | documented_source_field | — | [] | null |

## 172 · LID_CGM_ALERT_CLEARED

Clase: `cgm_alert_cleared` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| dalertId | Identificador de tipo de alerta del sensor en su espacio de nombres. | documented_source_field | enum | [] | {"0": "Alert_CGM_DEPRECATED_3", "1": "Alert_CGM_FIXED_LOW", "2": "Alert_CGM_USER_HIGH_EGV", "3": "Alert_CGM_USER_LOW_EGV", "4": "Alert_CGM_CALIBRATION_REQUEST", "5": "Alert_CGM_RISE", "6": "Alert_CGM_RAPID_RISE", "7": "Alert_CGM_FALL", "8": "Alert_CGM_RAPID_FALL", "9": "Alert_CGM_CALIB_ERROR", "10": "Alert_CGM_CALIB_HIGH_WEDGE", "11": "Alert_CGM_SENSOR_FAILED", "12": "Alert_CGM_SENSOR_EXPIRING", "13": "Alert_CGM_SENSOR_EXPIRED", "14": "Alert_CGM_OUT_OF_RANGE", "15": "Alert_CGM_DEPRECATED", "16": "Alert_CGM_CALIB_START_FIRST", "17": "Alert_CGM_CALIB_START_SECOND", "18": "Alert_CGM_CALIB_REQUIRED", "19": "Alert_CGM_LOW_TX_BATTERY", "20": "Alert_CGM_TRANSMITTER_ERROR", "21": "Alert_CGM_DEPRECATED_2", "22": "Alert_CGM_SENSOR_EXPIRING_SOON", "23": "Alert_CGM_DEPRECATED_4", "24": "Alert_CGM_URGENT_LOW_SOON", "25": "Alert_CGM_SENSOR_REUSE", "26": "Alert_CGM_SENSOR_TEMP", "27": "Alert_CGM_CONNECTION_ERROR", "28": "Alert_CGM_CHECK_SENSOR", "29": "Alert_CGM_EGV_UNUSABLE", "30": "Alert_CGM_UNUSED1", "31": "Alert_CGM_GRACE_PERIOD_START", "32": "Alert_CGM_GRACE_PERIOD_EXPIRING_SOON", "33": "NUM_CGM_ALERTS"} |

## 191 · LID_VERSION_INFO

Clase: `device_version` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| version | Propiedad fuente de LID_VERSION_INFO; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| configABits | Propiedad fuente de LID_VERSION_INFO; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Bitmask | [] | null |
| configBBits | Propiedad fuente de LID_VERSION_INFO; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Bitmask | [] | null |
| armCrc | Propiedad fuente de LID_VERSION_INFO; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |

## 203 · LID_UPDATE_STATUS

Clase: `device_update_status` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| swUpdateStatus | Propiedad fuente de LID_UPDATE_STATUS; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | Bitmask | [] | {"0": "ARM update success", "1": "MSP update success", "2": "Radio processor update success", "3": "Alphamasks (GUI images) update success", "4": "Raster (GUI images) update success", "5": "Radio application update success", "6": "Radio bootloader update success", "7": "Radio stack update success", "8": "ARM update failed", "9": "MSP update failed", "10": "Radio processor update failed", "11": "Alphamasks (GUI images) update failed", "12": "Raster (GUI images) update failed", "13": "Radio application update failed", "14": "Radio bootloader update failed", "15": "Radio stack update failed"} |
| metadataAndVersionStatus | Propiedad fuente de LID_UPDATE_STATUS; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | Bitmask | [] | {"0": "ARM metadata CRC failed", "1": "MSP metadata CRC failed", "2": "Radio processor metadata CRC failed", "3": "Alphamasks (GUI images) metadata CRC failed", "4": "Raster (GUI images) metadata CRC failed", "5": "Radio application metadata CRC failed", "6": "Radio bootloader metadata CRC failed", "7": "Radio stack metadata CRC failed", "8": "ARM version failed", "9": "MSP version failed", "10": "Radio processor version failed", "11": "Alphamasks (GUI images) version failed", "12": " Raster (GUI images) version failed", "13": "Radio application version failed", "14": "Radio bootloader version failed", "15": "Radio stack version failed"} |
| fullDlAndCrcStatus | Propiedad fuente de LID_UPDATE_STATUS; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | Bitmask | [] | {"0": "ARM full download failed", "1": "MSP full download failed", "2": "Radio processor full download failed", "3": "Alphamasks (GUI images) full download failed", "4": "Raster (GUI images) full download failed", "5": "Radio application full download failed", "6": "Radio bootloader full download failed", "7": "Radio stack full download failed", "8": "ARM CRC failed", "9": "MSP CRC failed", "10": "Radio processor CRC failed", "11": "Alphamasks (GUI images) CRC failed", "12": "Raster (GUI images) CRC failed", "13": "Radio application CRC failed", "14": "Radio bootloader CRC failed", "15": "Radio stack CRC failed"} |
| fileDlAndSideloadStatus | Propiedad fuente de LID_UPDATE_STATUS; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | Bitmask | [] | {"0": "ARM file downloaded", "1": "MSP file downloaded", "2": "Radio file downloaded", "3": "Alphamasks (GUI images) file downloaded", "4": "Raster (GUI images) file downloaded", "5": "Radio application file downloaded", "6": "Radio bootloader file downloaded", "7": "Radio stack file downloaded", "8": "ARM sideload started", "9": "MSP sideload started", "10": "Radio sideload started", "11": "Alphamasks (GUI images) sideload started", "12": "Raster (GUI images) sideload started", "13": "Radio application sideload started", "14": "Radio bootloader sideload started", "15": "Radio stack sideload started"} |
| externalFlashStatus | Propiedad fuente de LID_UPDATE_STATUS; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Bitmask | [] | null |
| updateSuccessful | Propiedad fuente de LID_UPDATE_STATUS; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Boolean | [] | null |
| swPartNum | Propiedad fuente de LID_UPDATE_STATUS; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |

## 212 · LID_CGM_START_SESSION_GX

Clase: `cgm_session_start` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| currentTransmitterTime | Propiedad fuente de LID_CGM_START_SESSION_GX; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionStartTime | Propiedad fuente de LID_CGM_START_SESSION_GX; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionDuration | Duración de sesión en días según catálogo447; conservar como dato fuente. | documented_source_field | days | [] | null |
| sessionStartReason | Propiedad fuente de LID_CGM_START_SESSION_GX; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | Enum | [] | {"0": "DEXBLES_REASON_USER", "1": "DEXBLES_REASON_UNKNOWN", "2": "Reserved", "3": "DEXBLES_REASON_TX_END_OF_LIFE", "4": "DEXBLES_REASON_TRANSMITTER_ERROR", "5": "DEXBLES_REASON_SESSION_STOP_SUCCESS", "6": "DEXBLES_REASON_TRANSMITTER_NOT_IN_SESSION", "7": "Reserved", "8": "DEXBLES_REASON_NEW_SESSION_STARTED_SUCCESS", "9": "DEXBLES_REASON_SESSION_STARTED_IN_PROGRESS", "10": "DEXBLES_REASON_TRANSMITTER_IN_SESSION", "11": "DEXBLES_REASON_BLESTACK_INVALID", "12": "DEXBLES_REASON_NEW_AUTOCAL_SESSION_STARTED_SUCCESS", "13": "DEXBLES_REASON_AUTOCAL_SESSION_IN_PROGRESS", "21": "DEXBLES_REASON_STALE_START_CMD", "22": "DEXBLES_REASON_STALE_STOP_CMD"} |

## 213 · LID_CGM_JOIN_SESSION_GX

Clase: `cgm_session_join` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| currentTransmitterTime | Propiedad fuente de LID_CGM_JOIN_SESSION_GX; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionStartTime | Propiedad fuente de LID_CGM_JOIN_SESSION_GX; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionDuration | Duración de sesión en días según catálogo447; conservar como dato fuente. | documented_source_field | days | [] | null |
| sessionJoinReason | Propiedad fuente de LID_CGM_JOIN_SESSION_GX; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | Enum | [] | {"0": "DEXBLES_REASON_USER", "1": "DEXBLES_REASON_UNKNOWN", "2": "Reserved", "3": "DEXBLES_REASON_TX_END_OF_LIFE", "4": "DEXBLES_REASON_TRANSMITTER_ERROR", "5": "DEXBLES_REASON_SESSION_STOP_SUCCESS", "6": "DEXBLES_REASON_TRANSMITTER_NOT_IN_SESSION", "7": "Reserved", "8": "DEXBLES_REASON_NEW_SESSION_STARTED_SUCCESS", "9": "DEXBLES_REASON_SESSION_STARTED_IN_PROGRESS", "10": "DEXBLES_REASON_TRANSMITTER_IN_SESSION", "11": "DEXBLES_REASON_BLESTACK_INVALID", "12": "DEXBLES_REASON_NEW_AUTOCAL_SESSION_STARTED_SUCCESS", "13": "DEXBLES_REASON_AUTOCAL_SESSION_IN_PROGRESS", "21": "DEXBLES_REASON_STALE_START_CMD", "22": "DEXBLES_REASON_STALE_STOP_CMD"} |

## 214 · LID_CGM_STOP_SESSION_GX

Clase: `cgm_session_stop` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| currentTransmitterTime | Propiedad fuente de LID_CGM_STOP_SESSION_GX; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionStartTime | Propiedad fuente de LID_CGM_STOP_SESSION_GX; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionStopTime | Propiedad fuente de LID_CGM_STOP_SESSION_GX; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionDuration | Duración de sesión en días según catálogo447; conservar como dato fuente. | documented_source_field | days | [] | null |
| sessionStopReason | Código de motivo de fin de sesión: enum no documentado en este catálogo; no inventar explicación. | documented_source_field | Enum | [] | {"0": "CGMBLES_REASON_USER", "1": "CGMBLES_REASON_UNKNOWN", "2": "Reserved", "3": "CGMBLES_REASON_TX_END_OF_LIFE", "4": "CGMBLES_REASON_TRANSMITTER_ERROR", "5": "CGMBLES_REASON_SESSION_STOP_SUCCESS", "6": "CGMBLES_REASON_TRANSMITTER_NOT_IN_SESSION", "7": "Reserved", "8": "CGMBLES_REASON_NEW_SESSION_STARTED_SUCCESS", "9": "CGMBLES_REASON_SESSION_STARTED_IN_PROGRESS", "10": "CGMBLES_REASON_TRANSMITTER_IN_SESSION", "11": "CGMBLES_REASON_BLESTACK_INVALID", "12": "CGMBLES_REASON_NEW_AUTOCAL_SESSION_STARTED_SUCCESS", "13": "CGMBLES_REASON_AUTOCAL_SESSION_IN_PROGRESS", "15": "CGMBLES_REASON_SENSOR_ERROR", "21": "CGMBLES_REASON_STALE_START_CMD", "22": "CGMBLES_REASON_STALE_STOP_CMD", "23": "CGMBLES_REASON_USER_CHANGED_SENSOR_TYPE", "24": "CGMBLES_REASON_INVALID_START_SESSION"} |

## 219 · CgmStateChangeGx

Clase: `cgm_scanner_state` · estado: `provisional_reference`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| currentScannerState | Estado del scanner MCG según catálogo219; no desconexión física ni estado de disponibilidad Control-IQ. | documented_source_field | — | [] | null |
| previousScannerState | Estado previo del scanner en219. | documented_source_field | — | [] | null |
| scannerFaultCount | Propiedad fuente de CgmStateChangeGx; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| scanningEvent | Propiedad fuente de CgmStateChangeGx; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| spareA1 | Campo reservado: sin significado clínico asignado. | reserved_uninterpreted | — | [] | null |
| spareA2 | Campo reservado: sin significado clínico asignado. | reserved_uninterpreted | — | [] | null |
| spareB5 | Campo reservado: sin significado clínico asignado. | reserved_uninterpreted | — | [] | null |
| spareB6 | Campo reservado: sin significado clínico asignado. | reserved_uninterpreted | — | [] | null |

## 229 · LID_AA_USER_MODE_CHANGE

Clase: `mode_change` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| currentUserMode | Modo observado tras transición (normal, sueño, ejercicio, comida próxima) según enum. | documented_source_field | Enum | [] | {"0": "Normal", "1": "Sleeping", "2": "Exercising", "3": "Eating Soon"} |
| previousUserMode | Modo previo de la transición; no prolongarlo por huecos o cambios de reloj. | documented_source_field | Enum | [] | {"0": "Normal", "1": "Sleeping", "2": "Exercising", "3": "Eating Soon"} |
| requestedAction | Acción solicitada; por sí sola no prueba modo resultante. | documented_source_field | Enum | [] | {"0": "No User Request", "1": "Start Sleep", "2": "Stop Sleep", "3": "Start Exercise", "4": "Stop Exercise", "5": "Stop All", "6": "Start Eating Soon", "7": "Stop Eating Soon"} |
| sleepStartedByGui | Propiedad fuente de LID_AA_USER_MODE_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Boolean | [] | null |
| activeSleepSchedule | Propiedad fuente de LID_AA_USER_MODE_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | Bitmask | [] | {"0": "Sleep Schedule 1 is Active", "1": "Sleep Schedule 2 is Active", "2": "Sleep Schedule 3 is Active", "3": "Sleep Schedule 4 is Active"} |
| exerciseStoppedByTimer | Propiedad fuente de LID_AA_USER_MODE_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Boolean | [] | null |
| exerciseChoice | Propiedad fuente de LID_AA_USER_MODE_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | Enum | [] | {"0": "Continuous", "1": "Timed"} |
| exerciseTime | Propiedad fuente de LID_AA_USER_MODE_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | minutes | [] | null |
| eatingSoonStoppedByTimer | Propiedad fuente de LID_AA_USER_MODE_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Boolean | [] | null |

## 230 · LID_AA_PCM_CHANGE

Clase: `control_mode_change` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| currentPcm | Estado de control de bomba posterior al evento230; nombres no resueltos se conservan sin inferir desconexión física. | documented_source_field | Enum | [] | {"0": "No Control", "1": "Open Loop", "2": "Pining", "3": "Closed Loop"} |
| previousPcm | Estado de control previo en230; distinto de modo de usuario y estado del sensor. | documented_source_field | Enum | [] | {"0": "No Control", "1": "Open Loop", "2": "Pining", "3": "Closed Loop"} |
| pumpSuspended | Indicador de suspensión en el registro; no inferir una causa si no hay evidencia. | documented_source_field | Boolean | [] | null |
| calculationAvailable | Propiedad fuente de LID_AA_PCM_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Boolean | [] | null |
| cgmAvailable | Indicador de disponibilidad MCG en ese registro; no acredita conexión física del catéter. | documented_source_field | Boolean | [] | null |
| closedLoopPreferred | Propiedad fuente de LID_AA_PCM_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Boolean | [] | null |
| sufficientClosedLoopParams | Propiedad fuente de LID_AA_PCM_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Boolean | [] | null |

## 256 · LID_CGM_DATA_GXB

Clase: `cgm` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| glucoseValueStatus | Calificador de lectura: numérica, high, low u otro no resuelto. | documented_source_field | Enum | [] | {"0": "currentGlucoseDisplayValue contains the glucose reading", "1": "The glucose reading is high, currentGlucoseDisplayValue set to 0", "2": "The glucose reading is low, currentGlucoseDisplayValue set to 0"} |
| cgmDataType | Lista de posiciones de bits sobre el tipo de dato MCG (p.ej. backfill), no otra lectura que sumar. | documented_source_field | Bitmask | [] | {"0": "Five Minute Reading (FMR)", "1": "BackFill", "2": "Immediate Match Value", "3": "Calibration", "4": "None"} |
| rate | Campo original de tendencia: el catálogo declara mg/dL/min pero escala/factor efectivo no validados; no normalizar por suposición. | documented_source_field | mg/dL/min | [] | null |
| algorithmState | Estado del algoritmo del sensor (calentamiento, lectura válida/inválida, parada, etc.), no estado Control-IQ de la bomba. | documented_source_field | Enum | [] | null |
| rssi | Potencia de señal recibida en dBm según catálogo; no identifica por sí sola causa de pérdida de lecturas. | documented_source_field | dBm | [] | null |
| currentGlucoseDisplayValue | Valor MCG mostrado si glucoseValueStatus=0; con High/Low no interpretar cero fuente como cero mg/dL. | documented_source_field | mg/dL | [{"name": "currentGlucoseDisplayValue", "unit": "mg/dL", "source_field": "currentGlucoseDisplayValue", "factor": 1}] | null |
| egvTimeStamp | Segundos fuente desde2008-01-01 que generan measurement_local_timestamp sin zona inferida. | documented_source_field | sec | [] | null |
| egvInfoBitmask | Lista de posiciones de bits de calidad/estado de muestra; conserva etiquetas del catálogo incluso incompletas. | documented_source_field | Bitmask | [] | {"0": "Five Minute Reading (FMR)", "1": "Backfill", "2": "Immediate match value", "3": "CRR (EGV is result of calibration, bit:14 was set to 1)", "4": "NO_EGV message", "5": "Valid timestamp", "6": "Valid EGV (valid range)", "7": "Valid algState (algState is 6, 7, or 14)", "8": "EGV was successfully added to CGM subsystem array (e.g.", "11": "Sensor Type (this should be 1 for this G6 log)*", "12": "Sensor Type (this should be 1 for this G6 log)*", "13": "Sensor Type (this should be 1 for this G6 log)*"} |
| interval | Propiedad fuente de LID_CGM_DATA_GXB; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| reservedD15 | Campo reservado: sin significado clínico asignado. | reserved_uninterpreted | — | [] | null |

## 279 · LID_BASAL_DELIVERY

Clase: `basal_rate` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| commandedRateSource | Origen de tasa indicada: suspensión/perfil/temporal/algoritmo según enum. | documented_source_field | Enum | [] | {"0": "Suspended", "1": "Profile", "2": "Temp Rate", "3": "Algorithm", "4": "Temp Rate and Algorithm"} |
| reservedA2 | Campo reservado: sin significado clínico asignado. | reserved_uninterpreted | — | [] | null |
| commandedRate | Tasa basal indicada por la bomba, no cantidad suministrada. | documented_source_field | milliunits/hr | [{"name": "commandedRate", "unit": "U/h", "source_field": "commandedRate", "factor": 0.001}] | null |
| profileBasalRate | Tasa del perfil observada en el evento279; no usar una instantánea actual en su lugar. | documented_source_field | milliunits/hr | [{"name": "profileBasalRate", "unit": "U/h", "source_field": "profileBasalRate", "factor": 0.001}] | null |
| algorithmRate | Tasa del algoritmo reportada, no dosis adicional a la tasa indicada. | documented_source_field | milliunits/hr | [{"name": "algorithmRate", "unit": "U/h", "source_field": "algorithmRate", "factor": 0.001}] | null |
| tempRate | Tasa temporal reportada; no sumar al resto de tasas. | documented_source_field | milliunits/hr | [{"name": "tempRate", "unit": "U/h", "source_field": "tempRate", "factor": 0.001}] | null |

## 280 · LID_BOLUS_DELIVERY

Clase: `bolus_delivery` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| bolusId | Identificador de asociación de fases de un bolo, condicionado por dispositivo y ventana temporal; puede repetirse. | documented_source_field | — | [] | null |
| bolusDeliveryStatus | Fase de entrega API280: 1 inicio, 0 final. Un inicio con total cero no es una dosis terminada cero. | documented_source_field | Enum | [] | {"0": "Bolus Completed", "1": "Bolus Started"} |
| bolusType | Lista de posiciones de bits, no un entero bitmask a reinterpretar. Now/Later/Correction/Carb/Override describen el tipo. | documented_source_field | Bitmask | [] | {"0": "Now", "1": "Later", "2": "Override", "3": "Correction", "4": "Carb", "5": "Eating Soon Mode", "6": "Queued"} |
| bolusSource | Origen declarado del bolo (bomba, algoritmo, Bluetooth u otro enum). No implica por sí solo motivo clínico. | documented_source_field | Enum | [] | {"0": "Pump Button", "1": "Pump GUI", "2": "Reserved", "3": "Reserved", "4": "Reserved", "5": "Remote", "6": "Reserved", "7": "Algorithm", "8": "BLE", "9": "Eating Soon Bolus", "10": "Reserved", "11": "BLE with AID Recommendation"} |
| remoteId | Propiedad fuente de LID_BOLUS_DELIVERY; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| requestedNow | Cantidad inmediata solicitada, distinta de cantidad finalmente suministrada. | documented_source_field | milliunits | [{"name": "requestedNow", "unit": "U", "source_field": "requestedNow", "factor": 0.001}] | null |
| requestedLater | Cantidad extendida solicitada; no confirma entrega ni extremos reales. | documented_source_field | milliunits | [{"name": "requestedLater", "unit": "U", "source_field": "requestedLater", "factor": 0.001}] | null |
| correction | Componente de corrección solicitado en el sobre280; no una entrega independiente. | documented_source_field | milliunits | [{"name": "correction", "unit": "U", "source_field": "correction", "factor": 0.001}] | null |
| extendedDurationRequested | Duración solicitada del extendido en minutos; no utilizar como fin real observado. | documented_source_field | minutes | [] | null |
| deliveredTotal | Total acumulado del bolo, no otro componente para sumar. La interpretación principal se usa cuando status=0. | documented_source_field | milliunits | [{"name": "deliveredTotal", "unit": "U", "source_field": "deliveredTotal", "factor": 0.001}] | null |

## 307 · LID_VERSIONS_A

Clase: `device_version` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| armPartNumber | Propiedad fuente de LID_VERSIONS_A; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| armSwVersion | Propiedad fuente de LID_VERSIONS_A; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| blePartNumber | Propiedad fuente de LID_VERSIONS_A; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| bleSwVersion | Propiedad fuente de LID_VERSIONS_A; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |

## 313 · LID_AA_DAILY_STATUS

Clase: `daily_status` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| pumpControlState | Propiedad fuente de LID_AA_DAILY_STATUS; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "PCM No Control (No cartridge installed)", "1": "PCM Open Loop", "2": "PCM Pining", "3": "PCM Closed Loop"} |
| usermode | Propiedad fuente de LID_AA_DAILY_STATUS; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "Normal", "1": "Sleeping", "2": "Exercising"} |
| sensorType | Tipo de MCG según enum; no configuración histórica completa ni identificador físico universal. | documented_source_field | enum | [] | {"0": "CGM_TYPE_NONE", "1": "CGM_TYPE_DEXCOM_G6", "2": "CGM_TYPE_LIBRE2", "3": "CGM_TYPE_DEXCOM_G7", "4": "CGM_TYPE_LIBRE3"} |
| weightUnit | Propiedad fuente de LID_AA_DAILY_STATUS; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | Enum | [] | {"0": "Weight Unit Not Set", "1": "Weight is in Pounds (lbs)", "2": "Weight is in Kilograms (kg)"} |
| weight | Propiedad fuente de LID_AA_DAILY_STATUS; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | lbs or kg | [] | null |
| currentTdIpop | Propiedad fuente de LID_AA_DAILY_STATUS; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | units | [] | null |

## 369 · LID_CGM_ALERT_ACTIVATED_DEX

Clase: `cgm_alert` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| dalertId | Identificador de tipo de alerta del sensor en su espacio de nombres. | documented_source_field | enum | [] | {"0": "Alert_CGM_DEPRECATED_3", "1": "Alert_CGM_FIXED_LOW", "2": "Alert_CGM_USER_HIGH_EGV", "3": "Alert_CGM_USER_LOW_EGV", "4": "Alert_CGM_CALIBRATION_REQUEST", "5": "Alert_CGM_RISE", "6": "Alert_CGM_RAPID_RISE", "7": "Alert_CGM_FALL", "8": "Alert_CGM_RAPID_FALL", "9": "Alert_CGM_CALIB_ERROR", "10": "Alert_CGM_CALIB_HIGH_WEDGE", "11": "Alert_CGM_SENSOR_FAILED", "12": "Alert_CGM_SENSOR_EXPIRING", "13": "Alert_CGM_SENSOR_EXPIRED", "14": "Alert_CGM_OUT_OF_RANGE", "15": "Alert_CGM_DEPRECATED", "16": "Alert_CGM_CALIB_START_FIRST", "17": "Alert_CGM_CALIB_START_SECOND", "18": "Alert_CGM_CALIB_REQUIRED", "19": "Alert_CGM_LOW_TX_BATTERY", "20": "Alert_CGM_TRANSMITTER_ERROR", "21": "Alert_CGM_DEPRECATED_2", "22": "Alert_CGM_SENSOR_EXPIRING_SOON", "23": "Alert_CGM_DEPRECATED_4", "24": "Alert_CGM_URGENT_LOW_SOON", "25": "Alert_CGM_SENSOR_REUSE", "26": "Alert_CGM_SENSOR_TEMP", "27": "Alert_CGM_CONNECTION_ERROR", "28": "Alert_CGM_CHECK_SENSOR", "29": "Alert_CGM_EGV_UNUSABLE", "30": "Alert_CGM_UNUSED1", "31": "Alert_CGM_GRACE_PERIOD_START", "32": "Alert_CGM_GRACE_PERIOD_EXPIRING_SOON", "33": "NUM_CGM_ALERTS"} |
| sensorType | Tipo de MCG según enum; no configuración histórica completa ni identificador físico universal. | documented_source_field | enum | [] | {"0": "Invalid", "1": "CGM_TYPE_DEXCOM_G6", "3": "CGM_TYPE_DEXCOM_G7"} |
| faultLocatorData | Dato técnico de localización de fallo preservado; significado/unidad clínica no documentados. | documented_source_field | — | [] | null |
| param1 | Parámetro interno dependiente de tipo de alerta; sin significado/unidad generales documentados. | documented_source_field | — | [] | null |
| param2 | Parámetro interno dependiente de tipo de alerta; sin significado/unidad generales documentados. | documented_source_field | — | [] | null |

## 370 · LID_CGM_ALERT_CLEARED_DEX

Clase: `cgm_alert_cleared` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| dalertId | Identificador de tipo de alerta del sensor en su espacio de nombres. | documented_source_field | enum | [] | {"0": "Alert_CGM_DEPRECATED_3", "1": "Alert_CGM_FIXED_LOW", "2": "Alert_CGM_USER_HIGH_EGV", "3": "Alert_CGM_USER_LOW_EGV", "4": "Alert_CGM_CALIBRATION_REQUEST", "5": "Alert_CGM_RISE", "6": "Alert_CGM_RAPID_RISE", "7": "Alert_CGM_FALL", "8": "Alert_CGM_RAPID_FALL", "9": "Alert_CGM_CALIB_ERROR", "10": "Alert_CGM_CALIB_HIGH_WEDGE", "11": "Alert_CGM_SENSOR_FAILED", "12": "Alert_CGM_SENSOR_EXPIRING", "13": "Alert_CGM_SENSOR_EXPIRED", "14": "Alert_CGM_OUT_OF_RANGE", "15": "Alert_CGM_DEPRECATED", "16": "Alert_CGM_CALIB_START_FIRST", "17": "Alert_CGM_CALIB_START_SECOND", "18": "Alert_CGM_CALIB_REQUIRED", "19": "Alert_CGM_LOW_TX_BATTERY", "20": "Alert_CGM_TRANSMITTER_ERROR", "21": "Alert_CGM_DEPRECATED_2", "22": "Alert_CGM_SENSOR_EXPIRING_SOON", "23": "Alert_CGM_DEPRECATED_4", "24": "Alert_CGM_URGENT_LOW_SOON", "25": "Alert_CGM_SENSOR_REUSE", "26": "Alert_CGM_SENSOR_TEMP", "27": "Alert_CGM_CONNECTION_ERROR", "28": "Alert_CGM_CHECK_SENSOR", "29": "Alert_CGM_EGV_UNUSABLE", "30": "Alert_CGM_UNUSED1", "31": "Alert_CGM_GRACE_PERIOD_START", "32": "Alert_CGM_GRACE_PERIOD_EXPIRING_SOON", "33": "NUM_CGM_ALERTS"} |
| sensorType | Tipo de MCG según enum; no configuración histórica completa ni identificador físico universal. | documented_source_field | enum | [] | {"0": "Invalid", "1": "CGM_TYPE_DEXCOM_G6", "3": "CGM_TYPE_DEXCOM_G7"} |

## 371 · LID_CGM_ALERT_ACK_DEX

Clase: `cgm_alert_acknowledged` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| dalertId | Identificador de tipo de alerta del sensor en su espacio de nombres. | documented_source_field | enum | [] | {"0": "Alert_CGM_DEPRECATED_3", "1": "Alert_CGM_FIXED_LOW", "2": "Alert_CGM_USER_HIGH_EGV", "3": "Alert_CGM_USER_LOW_EGV", "4": "Alert_CGM_CALIBRATION_REQUEST", "5": "Alert_CGM_RISE", "6": "Alert_CGM_RAPID_RISE", "7": "Alert_CGM_FALL", "8": "Alert_CGM_RAPID_FALL", "9": "Alert_CGM_CALIB_ERROR", "10": "Alert_CGM_CALIB_HIGH_WEDGE", "11": "Alert_CGM_SENSOR_FAILED", "12": "Alert_CGM_SENSOR_EXPIRING", "13": "Alert_CGM_SENSOR_EXPIRED", "14": "Alert_CGM_OUT_OF_RANGE", "15": "Alert_CGM_DEPRECATED", "16": "Alert_CGM_CALIB_START_FIRST", "17": "Alert_CGM_CALIB_START_SECOND", "18": "Alert_CGM_CALIB_REQUIRED", "19": "Alert_CGM_LOW_TX_BATTERY", "20": "Alert_CGM_TRANSMITTER_ERROR", "21": "Alert_CGM_DEPRECATED_2", "22": "Alert_CGM_SENSOR_EXPIRING_SOON", "23": "Alert_CGM_DEPRECATED_4", "24": "Alert_CGM_URGENT_LOW_SOON", "25": "Alert_CGM_SENSOR_REUSE", "26": "Alert_CGM_SENSOR_TEMP", "27": "Alert_CGM_CONNECTION_ERROR", "28": "Alert_CGM_CHECK_SENSOR", "29": "Alert_CGM_EGV_UNUSABLE", "30": "Alert_CGM_UNUSED1", "31": "Alert_CGM_GRACE_PERIOD_START", "32": "Alert_CGM_GRACE_PERIOD_EXPIRING_SOON", "33": "NUM_CGM_ALERTS"} |
| sensorType | Tipo de MCG según enum; no configuración histórica completa ni identificador físico universal. | documented_source_field | enum | [] | {"0": "Invalid", "1": "CGM_TYPE_DEXCOM_G6", "3": "CGM_TYPE_DEXCOM_G7"} |
| ackSource | Origen del reconocimiento según enum; no demuestra resolución. | documented_source_field | enum | [] | {"0": "Alert Acknowledged by User", "1": "Alert Acknowledged by Software"} |

## 372 · LID_CGM_DATA_FSL2

Clase: `cgm` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| glucoseValueStatus | Calificador de lectura: numérica, high, low u otro no resuelto. | documented_source_field | Enum | [] | {"0": "Precise Value", "1": "Special High", "2": "Special Low"} |
| cgmDataType | Lista de posiciones de bits sobre el tipo de dato MCG (p.ej. backfill), no otra lectura que sumar. | documented_source_field | Bitmask | [] | {"0": "Five Minute Reading (FMR)", "1": "Backfill", "4": "None", "5": "One Minute Reading (OMR)"} |
| rate | Campo original de tendencia: el catálogo declara mg/dL/min pero escala/factor efectivo no validados; no normalizar por suposición. | documented_source_field | mg/dL/min | [] | null |
| algorithmState | Estado del algoritmo del sensor (calentamiento, lectura válida/inválida, parada, etc.), no estado Control-IQ de la bomba. | documented_source_field | Enum | [] | {"2": "Warmup", "100": "OK State", "101": "RF Error State", "102": "Sensor Signal Low State", "103": "Temp High State", "104": "Temp Low State", "105": "Invalid Data State", "106": "Other DQ State", "107": "EGV Unusable Condition"} |
| rssi | Potencia de señal recibida en dBm según catálogo; no identifica por sí sola causa de pérdida de lecturas. | documented_source_field | dBm | [] | null |
| currentGlucoseDisplayValue | Valor MCG mostrado si glucoseValueStatus=0; con High/Low no interpretar cero fuente como cero mg/dL. | documented_source_field | mg/dL | [{"name": "currentGlucoseDisplayValue", "unit": "mg/dL", "source_field": "currentGlucoseDisplayValue", "factor": 1}] | null |
| egvTimeStamp | Segundos fuente desde2008-01-01 que generan measurement_local_timestamp sin zona inferida. | documented_source_field | Seconds | [] | null |
| egvInfoBitmask | Lista de posiciones de bits de calidad/estado de muestra; conserva etiquetas del catálogo incluso incompletas. | documented_source_field | Bitmask | [] | {"0": "Five Minute Reading (FMR)", "1": "Backfill", "4": "NO_EGV message", "5": "Valid timestamp", "6": "Valid EGV (valid range)", "7": "Valid algState (algState is 100)", "8": "EGV was successfully added to CGM subsystem array (e.g., not a duplicate)", "9": "OMR reading type", "11": "Sensor Type (this should be 2 for this FSL2 log)", "12": "Sensor Type (this should be 2 for this FSL2 log)", "13": "Sensor Type (this should be 2 for this FSL2 log)"} |
| interval | Propiedad fuente de LID_CGM_DATA_FSL2; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| reservedD15 | Campo reservado: sin significado clínico asignado. | reserved_uninterpreted | — | [] | null |

## 394 · LID_CGM_JOIN_SESSION_G7

Clase: `cgm_session_join` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| cgmTimestamp | Propiedad fuente de LID_CGM_JOIN_SESSION_G7; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Seconds | [] | null |
| sessionSignature | Identificador/firma de sesión reportada; no token de autenticación ni prueba de sustitución física por sí solo. | documented_source_field | Seconds | [] | null |

## 399 · LID_CGM_DATA_G7

Clase: `cgm` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| glucoseValueStatus | Calificador de lectura: numérica, high, low u otro no resuelto. | documented_source_field | Enum | [] | {"0": "Precise Value", "1": "Special High", "2": "Special Low", "6": "Do Not Show, Do Not Store"} |
| cgmDataType | Lista de posiciones de bits sobre el tipo de dato MCG (p.ej. backfill), no otra lectura que sumar. | documented_source_field | Bitmask | [] | {"0": "FMR", "1": "Backfill", "2": "IMM No longer applies", "3": "Calibration", "4": "None"} |
| rate | Campo original de tendencia: el catálogo declara mg/dL/min pero escala/factor efectivo no validados; no normalizar por suposición. | documented_source_field | mg/dL/min | [] | null |
| algorithmState | Estado del algoritmo del sensor (calentamiento, lectura válida/inválida, parada, etc.), no estado Control-IQ de la bomba. | documented_source_field | Enum | [] | {"2": "Warmup", "30": "Default Electronics Wakeup", "31": "Detecting Deployment", "32": "Reportable Period Valid EGV", "33": "Reportable Period Invalid EGV", "34": "Session Stopped (End of Session)", "35": "Session Stopped (Algorithm Detected Failure)", "36": "Session Stopped (Manual Stop)", "37": "Session Stopped (Transmitter Failure)", "38": "Session Stopped (SIV Failure)", "39": "Session Stopped (Out of Range / Environmental Conditions Detected)"} |
| rssi | Potencia de señal recibida en dBm según catálogo; no identifica por sí sola causa de pérdida de lecturas. | documented_source_field | dBm | [] | null |
| currentGlucoseDisplayValue | Valor MCG mostrado si glucoseValueStatus=0; con High/Low no interpretar cero fuente como cero mg/dL. | documented_source_field | mg/dL | [{"name": "currentGlucoseDisplayValue", "unit": "mg/dL", "source_field": "currentGlucoseDisplayValue", "factor": 1}] | null |
| egvTimeStamp | Segundos fuente desde2008-01-01 que generan measurement_local_timestamp sin zona inferida. | documented_source_field | sec | [] | null |
| egvInfoBitmask | Lista de posiciones de bits de calidad/estado de muestra; conserva etiquetas del catálogo incluso incompletas. | documented_source_field | Bitmask | [] | {"0": "Five Minute Reading (FMR)", "1": "Backfill", "2": "Immediate match value", "3": "CRR (EGV is result of calibration, bit:14 was set to 1)", "4": "NO_EGV message", "5": "Valid timestamp", "6": "Valid EGV (valid range)", "7": "Valid algState (algState is 32)", "8": "EGV was successfully added to CGM subsystem array (e.g.", "9": "Reserved", "10": "Reserved", "11": "Sensor Type (this should be 3 for this G7 log)", "12": "Sensor Type (this should be 3 for this G7 log)", "13": "Sensor Type (this should be 3 for this G7 log)"} |
| interval | Propiedad fuente de LID_CGM_DATA_G7; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| reservedD15 | Campo reservado: sin significado clínico asignado. | reserved_uninterpreted | — | [] | null |

## 404 · LID_CGM_START_SESSION_FSL2

Clase: `cgm_session_start` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| sessionStartTime | Propiedad fuente de LID_CGM_START_SESSION_FSL2; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionDuration | Duración de sesión en días según catálogo447; conservar como dato fuente. | documented_source_field | days | [] | null |

## 405 · LID_CGM_STOP_SESSION_FSL2

Clase: `cgm_session_stop` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| sessionStartTime | Propiedad fuente de LID_CGM_STOP_SESSION_FSL2; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionStopTime | Propiedad fuente de LID_CGM_STOP_SESSION_FSL2; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionDuration | Duración de sesión en días según catálogo447; conservar como dato fuente. | documented_source_field | days | [] | null |
| sessionStopReason | Código de motivo de fin de sesión: enum no documentado en este catálogo; no inventar explicación. | documented_source_field | enum | [] | null |

## 406 · LID_CGM_JOIN_SESSION_FSL2

Clase: `cgm_session_join` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| sessionStartTime | Propiedad fuente de LID_CGM_JOIN_SESSION_FSL2; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionJoinTime | Propiedad fuente de LID_CGM_JOIN_SESSION_FSL2; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionDuration | Duración de sesión en días según catálogo447; conservar como dato fuente. | documented_source_field | days | [] | null |
| sessionJoinReason | Propiedad fuente de LID_CGM_JOIN_SESSION_FSL2; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | enum | [] | null |

## 434 · AamAnnunciation

Clase: `notification_annunciation` · estado: `provisional_reference`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| aarmType | Tipo/espacio de nombres del anuncio434; no duplicar su alarma/alerta original. | documented_source_field | — | [] | null |
| aarmid | Identificador reportado del anuncio; su espacio depende de aarmType. | documented_source_field | — | [] | null |
| annunPattern | Patrón de anuncio de notificación; no una nueva activación de alarma. | documented_source_field | — | [] | null |
| annunVolume | Volumen configurado del anuncio de notificación, no gravedad clínica. | documented_source_field | — | [] | null |
| mainPriority | Propiedad fuente de AamAnnunciation; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| priorityRank | Propiedad fuente de AamAnnunciation; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |

## 447 · LID_CGM_STOP_SESSION_G7

Clase: `cgm_session_stop` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| currentTransmitterTime | Propiedad fuente de LID_CGM_STOP_SESSION_G7; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionStartTime | Propiedad fuente de LID_CGM_STOP_SESSION_G7; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionStopTime | Propiedad fuente de LID_CGM_STOP_SESSION_G7; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionDuration | Duración de sesión en días según catálogo447; conservar como dato fuente. | documented_source_field | days | [] | null |
| sessionStopReason | Código de motivo de fin de sesión: enum no documentado en este catálogo; no inventar explicación. | documented_source_field | enum | [] | null |
| stopSessionCode | Código interno de parada de sesión, preservado sin interpretación documentada. | documented_source_field | enum | [] | null |

## 460 · LID_CGM_ALERT_ACTIVATED_ABT

Clase: `cgm_alert` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| dalertId | Identificador de tipo de alerta del sensor en su espacio de nombres. | documented_source_field | enum | [] | {"0": "Alert_CGM_DEPRECATED_3", "1": "Alert_CGM_FIXED_LOW", "2": "Alert_CGM_USER_HIGH_EGV", "3": "Alert_CGM_USER_LOW_EGV", "4": "Alert_CGM_CALIBRATION_REQUEST", "5": "Alert_CGM_RISE", "6": "Alert_CGM_RAPID_RISE", "7": "Alert_CGM_FALL", "8": "Alert_CGM_RAPID_FALL", "9": "Alert_CGM_CALIB_ERROR", "10": "Alert_CGM_CALIB_HIGH_WEDGE", "11": "Alert_CGM_SENSOR_FAILED", "12": "Alert_CGM_SENSOR_EXPIRING", "13": "Alert_CGM_SENSOR_EXPIRED", "14": "Alert_CGM_OUT_OF_RANGE", "15": "Alert_CGM_DEPRECATED", "16": "Alert_CGM_CALIB_START_FIRST", "17": "Alert_CGM_CALIB_START_SECOND", "18": "Alert_CGM_CALIB_REQUIRED", "19": "Alert_CGM_LOW_TX_BATTERY", "20": "Alert_CGM_TRANSMITTER_ERROR", "21": "Alert_CGM_DEPRECATED_2", "22": "Alert_CGM_SENSOR_EXPIRING_SOON", "23": "Alert_CGM_DEPRECATED_4", "24": "Alert_CGM_URGENT_LOW_SOON", "25": "Alert_CGM_SENSOR_REUSE", "26": "Alert_CGM_SENSOR_TEMP", "27": "Alert_CGM_CONNECTION_ERROR", "28": "Alert_CGM_CHECK_SENSOR", "29": "Alert_CGM_EGV_UNUSABLE", "30": "Alert_CGM_UNUSED1", "31": "Alert_CGM_GRACE_PERIOD_START", "32": "Alert_CGM_GRACE_PERIOD_EXPIRING_SOON", "33": "NUM_CGM_ALERTS"} |
| sensorType | Tipo de MCG según enum; no configuración histórica completa ni identificador físico universal. | documented_source_field | enum | [] | {"0": "Invalid", "2": "CGM_TYPE_LIBRE2", "4": "CGM_TYPE_LIBRE3"} |
| faultLocatorData | Dato técnico de localización de fallo preservado; significado/unidad clínica no documentados. | documented_source_field | — | [] | null |
| param1 | Parámetro interno dependiente de tipo de alerta; sin significado/unidad generales documentados. | documented_source_field | — | [] | null |
| param2 | Parámetro interno dependiente de tipo de alerta; sin significado/unidad generales documentados. | documented_source_field | — | [] | null |

## 461 · LID_CGM_ALERT_CLEARED_ABT

Clase: `cgm_alert_cleared` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| dalertId | Identificador de tipo de alerta del sensor en su espacio de nombres. | documented_source_field | enum | [] | {"0": "Alert_CGM_DEPRECATED_3", "1": "Alert_CGM_FIXED_LOW", "2": "Alert_CGM_USER_HIGH_EGV", "3": "Alert_CGM_USER_LOW_EGV", "4": "Alert_CGM_CALIBRATION_REQUEST", "5": "Alert_CGM_RISE", "6": "Alert_CGM_RAPID_RISE", "7": "Alert_CGM_FALL", "8": "Alert_CGM_RAPID_FALL", "9": "Alert_CGM_CALIB_ERROR", "10": "Alert_CGM_CALIB_HIGH_WEDGE", "11": "Alert_CGM_SENSOR_FAILED", "12": "Alert_CGM_SENSOR_EXPIRING", "13": "Alert_CGM_SENSOR_EXPIRED", "14": "Alert_CGM_OUT_OF_RANGE", "15": "Alert_CGM_DEPRECATED", "16": "Alert_CGM_CALIB_START_FIRST", "17": "Alert_CGM_CALIB_START_SECOND", "18": "Alert_CGM_CALIB_REQUIRED", "19": "Alert_CGM_LOW_TX_BATTERY", "20": "Alert_CGM_TRANSMITTER_ERROR", "21": "Alert_CGM_DEPRECATED_2", "22": "Alert_CGM_SENSOR_EXPIRING_SOON", "23": "Alert_CGM_DEPRECATED_4", "24": "Alert_CGM_URGENT_LOW_SOON", "25": "Alert_CGM_SENSOR_REUSE", "26": "Alert_CGM_SENSOR_TEMP", "27": "Alert_CGM_CONNECTION_ERROR", "28": "Alert_CGM_CHECK_SENSOR", "29": "Alert_CGM_EGV_UNUSABLE", "30": "Alert_CGM_UNUSED1", "31": "Alert_CGM_GRACE_PERIOD_START", "32": "Alert_CGM_GRACE_PERIOD_EXPIRING_SOON", "33": "NUM_CGM_ALERTS"} |
| sensorType | Tipo de MCG según enum; no configuración histórica completa ni identificador físico universal. | documented_source_field | enum | [] | {"0": "Invalid", "2": "CGM_TYPE_LIBRE2", "4": "CGM_TYPE_LIBRE3"} |

## 477 · LID_CGM_JOIN_SESSION_FSL3

Clase: `cgm_session_join` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| sessionStartTime | Propiedad fuente de LID_CGM_JOIN_SESSION_FSL3; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Seconds | [] | null |
| sessionJoinTime | Propiedad fuente de LID_CGM_JOIN_SESSION_FSL3; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Seconds | [] | null |
| sessionDuration | Duración de sesión en días según catálogo447; conservar como dato fuente. | documented_source_field | Days | [] | null |
| sessionJoinReason | Propiedad fuente de LID_CGM_JOIN_SESSION_FSL3; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Enum | [] | null |
| sessionDurationSecs | Propiedad fuente de LID_CGM_JOIN_SESSION_FSL3; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Seconds | [] | null |

## 480 · LID_CGM_DATA_FSL3

Clase: `cgm` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| glucoseValueStatus | Calificador de lectura: numérica, high, low u otro no resuelto. | documented_source_field | Enum | [] | {"0": "Precise Value", "1": "Special High", "2": "Special Low"} |
| cgmDataType | Lista de posiciones de bits sobre el tipo de dato MCG (p.ej. backfill), no otra lectura que sumar. | documented_source_field | Bitmask | [] | {"0": "Five Minute Reading (FMR)", "1": "Backfill", "4": "None", "5": "One Minute Reading (OMR)"} |
| rate | Campo original de tendencia: el catálogo declara mg/dL/min pero escala/factor efectivo no validados; no normalizar por suposición. | documented_source_field | mg/dL/min | [] | null |
| algorithmState | Estado del algoritmo del sensor (calentamiento, lectura válida/inválida, parada, etc.), no estado Control-IQ de la bomba. | documented_source_field | Enum | [] | {"100": "OK State"} |
| rssi | Potencia de señal recibida en dBm según catálogo; no identifica por sí sola causa de pérdida de lecturas. | documented_source_field | dBm | [] | null |
| currentGlucoseDisplayValue | Valor MCG mostrado si glucoseValueStatus=0; con High/Low no interpretar cero fuente como cero mg/dL. | documented_source_field | mg/dL | [{"name": "currentGlucoseDisplayValue", "unit": "mg/dL", "source_field": "currentGlucoseDisplayValue", "factor": 1}] | null |
| egvTimeStamp | Segundos fuente desde2008-01-01 que generan measurement_local_timestamp sin zona inferida. | documented_source_field | Seconds | [] | null |
| egvInfoBitmask | Lista de posiciones de bits de calidad/estado de muestra; conserva etiquetas del catálogo incluso incompletas. | documented_source_field | Bitmask | [] | {"0": "Five Minute Reading (FMR)", "1": "Backfill", "4": "NO_EGV message", "5": "Valid timestamp", "6": "Valid EGV (valid range)", "7": "Valid algState (algState is 100)", "8": "EGV was successfully added to CGM subsystem array (e.g., not a duplicate)", "9": "OMR reading type", "11": "Sensor Type (this should be 4 for this FSL3 log)", "12": "Sensor Type (this should be 4 for this FSL3 log)", "13": "Sensor Type (this should be 4 for this FSL3 log)"} |
| interval | Propiedad fuente de LID_CGM_DATA_FSL3; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| reservedD15 | Campo reservado: sin significado clínico asignado. | reserved_uninterpreted | — | [] | null |

## 486 · LID_CGM_STOP_SESSION_FSL3

Clase: `cgm_session_stop` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| sessionStartTime | Propiedad fuente de LID_CGM_STOP_SESSION_FSL3; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionStopTime | Propiedad fuente de LID_CGM_STOP_SESSION_FSL3; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | sec | [] | null |
| sessionDuration | Duración de sesión en días según catálogo447; conservar como dato fuente. | documented_source_field | days | [] | null |
| sessionStopReason | Código de motivo de fin de sesión: enum no documentado en este catálogo; no inventar explicación. | documented_source_field | enum | [] | null |

## 558 · LID_SYNC_DOSE_START

Clase: `sync_dose_started` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| doseId | Propiedad fuente de LID_SYNC_DOSE_START; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| doseSource | Propiedad fuente de LID_SYNC_DOSE_START; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | Enum | [] | {"0": "Suspended 1 = Profile 2 = Profile + Temporary Basal Rate 3 = Algorithm 4 = Algorithm + Temporary Control Rate"} |
| tempAdjustmentPercent | Propiedad fuente de LID_SYNC_DOSE_START; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | % (100.0 = 100%) | [] | null |
| syncDoseSizeRequested | Propiedad fuente de LID_SYNC_DOSE_START; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | units | [{"name": "syncDoseSizeRequested", "unit": "U", "source_field": "syncDoseSizeRequested", "factor": 1}] | null |
| currentBasalRate | Propiedad fuente de LID_SYNC_DOSE_START; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | milliunits/hr | [{"name": "currentBasalRate", "unit": "U/h", "source_field": "currentBasalRate", "factor": 0.001}] | null |
| profileBasalRate | Tasa del perfil observada en el evento279; no usar una instantánea actual en su lugar. | documented_source_field | milliunits/hr | [] | null |
| activeInsulin | Propiedad fuente de LID_SYNC_DOSE_START; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | units | [] | null |

## 559 · LID_SYNC_DOSE_COMPLETE

Clase: `sync_dose_completed` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| doseId | Propiedad fuente de LID_SYNC_DOSE_COMPLETE; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| doseSource | Propiedad fuente de LID_SYNC_DOSE_COMPLETE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | Enum | [] | {"0": "Suspended 1 = Profile 2 = Profile + Temporary Basal Rate 3 = Algorithm 4 = Algorithm + Temporary Control Rate"} |
| tempAdjustmentPercent | Propiedad fuente de LID_SYNC_DOSE_COMPLETE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | percent | [] | null |
| syncDoseSizeRequested | Propiedad fuente de LID_SYNC_DOSE_COMPLETE; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| syncDoseSizeDelivered | Propiedad fuente de LID_SYNC_DOSE_COMPLETE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | units | [{"name": "syncDoseSizeDelivered", "unit": "U", "source_field": "syncDoseSizeDelivered", "factor": 1}] | null |
| currentBasalRate | Propiedad fuente de LID_SYNC_DOSE_COMPLETE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | milliunits/hr | [{"name": "currentBasalRate", "unit": "U/h", "source_field": "currentBasalRate", "factor": 0.001}] | null |
| activeInsulin | Propiedad fuente de LID_SYNC_DOSE_COMPLETE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | units | [] | null |

## 562 · LID_ANT_DAILY_STATUS1

Clase: `daily_status` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| closedLoopPreferred | Propiedad fuente de LID_ANT_DAILY_STATUS1; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | Boolean | [] | null |
| totalDailyInsulinUnits | Propiedad fuente de LID_ANT_DAILY_STATUS1; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | units | [] | null |
| glycemicGoal | Propiedad fuente de LID_ANT_DAILY_STATUS1; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "Relaxed", "1": "Balanced", "2": "Tightest"} |
| priorTherapy | Propiedad fuente de LID_ANT_DAILY_STATUS1; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "Previous Pumping Experience", "1": "Multiple Daily Injections", "2": "Prior Therapy Not Set"} |
| sleepEatSegmentStartTime0 | Propiedad fuente de LID_ANT_DAILY_STATUS1; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | minutes | [] | null |
| sleepEatSegmentStartTime1 | Propiedad fuente de LID_ANT_DAILY_STATUS1; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | minutes | [] | null |
| sleepEatSegmentStartTime2 | Propiedad fuente de LID_ANT_DAILY_STATUS1; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | minutes | [] | null |
| sleepEatSegmentStartTime3 | Propiedad fuente de LID_ANT_DAILY_STATUS1; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | minutes | [] | null |
| sleepEatSegmentType0 | Propiedad fuente de LID_ANT_DAILY_STATUS1; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "None", "1": "Less", "2": "Standard", "3": "More", "4": "Max", "5": "Sleep", "6": "Not Defined"} |
| sleepEatSegmentType1 | Propiedad fuente de LID_ANT_DAILY_STATUS1; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "None", "1": "Less", "2": "Standard", "3": "More", "4": "Max", "5": "Sleep", "6": "Not Defined"} |
| sleepEatSegmentType2 | Propiedad fuente de LID_ANT_DAILY_STATUS1; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "None", "1": "Less", "2": "Standard", "3": "More", "4": "Max", "5": "Sleep", "6": "Not Defined"} |
| sleepEatSegmentType3 | Propiedad fuente de LID_ANT_DAILY_STATUS1; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "None", "1": "Less", "2": "Standard", "3": "More", "4": "Max", "5": "Sleep", "6": "Not Defined"} |

## 563 · LID_ANT_DAILY_STATUS2

Clase: `daily_status` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| pumpControlState | Propiedad fuente de LID_ANT_DAILY_STATUS2; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "PCM No Control (No cartridge installed)", "1": "PCM Open Loop", "2": "PCM Pining", "3": "PCM Closed Loop"} |
| sensorType | Tipo de MCG según enum; no configuración histórica completa ni identificador físico universal. | documented_source_field | enum | [] | {"0": "CGM_TYPE_NONE", "1": "CGM_TYPE_DEXCOM_G6", "3": "CGM_TYPE_DEXCOM_G7", "4": "CGM_TYPE_LIBRE3"} |

## 564 · LID_TEMP_ADJUSTMENT_COMPLETED

Clase: `temporary_adjustment_end` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| stopReason | Propiedad fuente de LID_TEMP_ADJUSTMENT_COMPLETED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "User Aborted", "1": "Terminated by Alarm", "3": "Completed", "8": "User aborted ble", "10": "Terminated by pump control mode change (unable to convert)", "11": "Terminated by closed loop preferred change"} |
| tempRateId | Propiedad fuente de LID_TEMP_ADJUSTMENT_COMPLETED; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |
| timeLeft | Propiedad fuente de LID_TEMP_ADJUSTMENT_COMPLETED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | ms | [] | null |

## 565 · LID_TEMP_ADJUSTMENT_ACTIVATED

Clase: `temporary_adjustment_start` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| requestedPercent | Propiedad fuente de LID_TEMP_ADJUSTMENT_ACTIVATED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | % | [] | null |
| tempBasalPercent | Propiedad fuente de LID_TEMP_ADJUSTMENT_ACTIVATED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | % | [] | null |
| duration | Duración de opción de bolo en minutos según catálogo; no probar fin físico por sumar esta duración. | documented_source_field | ms | [] | null |
| requestedAdjustmentType | Propiedad fuente de LID_TEMP_ADJUSTMENT_ACTIVATED; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "Temporary Basal Rate (from GUI)", "1": "Unused (OBE)", "2": "Temporary Basal Rate (from BLE)", "3": "Temporary Control Rate (from BLE)"} |
| tempRateId | Propiedad fuente de LID_TEMP_ADJUSTMENT_ACTIVATED; no hay descripción semántica adicional validada. Consultar metadatos originales. | unresolved | — | [] | null |

## 566 · LID_ANT_SLEEP_EAT_SCHED_SETTING_CHANGE

Clase: `schedule_settings` · estado: `catalogued`

| Propiedad | Significado | Estado | Unidad fuente | Conversión normalizada | Enum/posiciones de bits |
|---|---|---|---|---|---|
| sleepEatSegmentStartTime0 | Propiedad fuente de LID_ANT_SLEEP_EAT_SCHED_SETTING_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | minutes | [] | null |
| sleepEatSegmentStartTime1 | Propiedad fuente de LID_ANT_SLEEP_EAT_SCHED_SETTING_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | minutes | [] | null |
| sleepEatSegmentStartTime2 | Propiedad fuente de LID_ANT_SLEEP_EAT_SCHED_SETTING_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | minutes | [] | null |
| sleepEatSegmentStartTime3 | Propiedad fuente de LID_ANT_SLEEP_EAT_SCHED_SETTING_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_units_only | minutes | [] | null |
| sleepEatSegmentType0 | Propiedad fuente de LID_ANT_SLEEP_EAT_SCHED_SETTING_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "None", "1": "Less", "2": "Standard", "3": "More", "4": "Max", "5": "Sleep", "6": "Not Defined"} |
| sleepEatSegmentType1 | Propiedad fuente de LID_ANT_SLEEP_EAT_SCHED_SETTING_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "None", "1": "Less", "2": "Standard", "3": "More", "4": "Max", "5": "Sleep", "6": "Not Defined"} |
| sleepEatSegmentType2 | Propiedad fuente de LID_ANT_SLEEP_EAT_SCHED_SETTING_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "None", "1": "Less", "2": "Standard", "3": "More", "4": "Max", "5": "Sleep", "6": "Not Defined"} |
| sleepEatSegmentType3 | Propiedad fuente de LID_ANT_SLEEP_EAT_SCHED_SETTING_CHANGE; no hay descripción semántica adicional validada. Consultar metadatos originales. | catalog_enum_only | enum | [] | {"0": "None", "1": "Less", "2": "Standard", "3": "More", "4": "Max", "5": "Sleep", "6": "Not Defined"} |
