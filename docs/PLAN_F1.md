# PLAN_F1.md — Plan de implementación Fase F1

**Fase**: F1 — Módulo de precios y tarifa  
**Referencia**: SPEC.md §8, §3 (RF-01), §5.1, §5.6, §6  
**Objetivo**: Implementar `ClienteOmie` + `ModeloTarifa` + sensores de precio + coordinador + flujo de configuración inicial.  
**Criterio de salida**: Precio del tramo y precio efectivo coinciden con OMIE + facturación esperada durante 3 días seguidos.  

---

## 1. Archivos a crear/modificar

### 1.1 Estructura base del repositorio

```
optimizador-bateria-omie/
├── custom_components/
│   └── optimizador_bateria_omie/
│       ├── __init__.py              # Inicialización del componente
│       ├── manifest.json            # Metadatos HACS (nombre, versión, dependencias, reqs)
│       ├── const.py                 # Constantes del componente (dominio, version, valores por defecto)
│       ├── flujo_configuracion.py   # Flujo de configuración inicial (F1: parámetros OMIE/tarifa)
│       ├── coordinador.py           # Coordinador central (gestión de actualizaciones)
│       ├── cliente_omie.py           # ClienteOmie (fuentes OMIE, REData, cache, normalización)
│       ├── tarifa.py                 # ModeloTarifa (peajes+cargos, precio efectivo, clasificación)
│       ├── entidades.py              # Sensores de precio
│       ├── servicios.yaml            # Servicios (vacío en F1, placeholder para F2+)
│       ├── translations/
│       │   └── es.json               # Traducciones UI (español)
│       └── tests/
│           ├── __init__.py
│           ├── test_cliente_omie.py  # Tests ClienteOmie con fixtures
│           ├── test_tarifa.py        # Tests ModeloTarifa con escenarios
│           ├── test_entidades.py     # Tests de los sensores de precio
│           └── conftest.py           # Fixtures comunes
├── hacs.json                          # Configuración para HACS
├── README.md                          # Descripción general del proyecto
└── docs/
    ├── PLAN_F1.md                   # Este archivo
    └── FASES.md                     # Estado general (crear tras F1)
```

### 1.2 Archivos existentes a modificar
- Ninguno (esta es la primera fase; el repositorio está vacío o solo tiene SPEC.md, AGENTS.md, PROMPTS.md).

---

## 2. Decisiones de diseño

### 2.1 Arquitectura del componente
- **Pattern**: Usar `DataUpdateCoordinator` de Home Assistant para gestionar las actualizaciones de datos (precios OMIE).
- **Cache**: `ClienteOmie` implementará cache en disco (JSON por fecha) en el directorio de datos de HA.
- **Fuentes**: Prioridad **integración OMIE existente** (`omie.get_prices_for_date`) > REData > ESIOS (opcional). `ClienteOmie` intentará en cascada con fallback automático.
- **Normalización**: Todos los precios se normalizarán a tramos de 15 min (96 tramos/día), manejando días con 92/100 tramos (cambio horario).
- **Huso horario**: HA está configurado con CET/CEST, por lo que se usará `hass.helpers.now()` para hora local sin conversión manual.

### 2.2 ClienteOmie
- **Método principal**: `async def obtener_precios_del_dia(fecha: date) -> list[Ranura]` donde `Ranura = NamedTuple(fecha_hora_utc: datetime, precio_eur_kwh: float, fuente: str, fecha_publicacion: datetime | None)`.
- **Cache**: Cada llamada a `obtener_precios_del_dia` escribirá en disco un JSON con clave `fecha.isoformat()`. TTL de 24h.
- **Refresco**: Programado a las ~13:45 CET.
- **Reintentos**: Backoff exponencial (1s, 2s, 4s, 8s, 16s) con máximo 5 intentos por fuente.
- **Fuentes** (prioridad):
  - **Integración OMIE**: `hass.services.call('omie', 'get_prices_for_date', {'date': fecha_iso})` como fuente primaria.
  - **REData**: `https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real` (fallback).
  - **ESIOS**: Opcional, requiere token configurable.

### 2.3 ModeloTarifa
- **Clase**: `ModeloTarifa` con método `obtener_precio_efectivo(ranura: Ranura, es_fin_de_semana: bool, es_festivo: bool) -> float`.
- **Períodos**: Lógica de clasificación según SPEC.md §5.6:
  - **Laborables**: Punta (10:00-14:00, 18:00-22:00), Llano (08:00-10:00, 14:00-18:00, 22:00-24:00), Valle (00:00-08:00).
  - **Sábados, domingos, festivos**: Valle todo el día.
- **Cargos**: Sumar al spot peaje + cargo según periodo.
- **Impuestos**: Aplicar `(1 + impuesto_electrico) * (1 + IVA)` si `aplicar_impuestos_precio=true`.
- **Clasificación**: Método `clasificar_ranura(ranura: Ranura) -> str` (valle/llano/punta) basado en percentiles.
- **Festivos nacionales**: Lista en `const.py` con 9 fechas oficiales:
  - `01-01` (Año Nuevo), `06-01` (Reyes), `01-05` (Trabajo), `15-08` (Asunción), `12-10` (Fiesta Nacional), `01-11` (Todos Santos), `06-12` (Constitución), `08-12` (Inmaculada), `25-12` (Navidad).

### 2.4 CoordinadorDatosOmie
- **Intervalo de actualización**: Cada 15 minutos.
- **Eventos**: Escuchar a las 13:45 CET para refrescar precios del día D+1.
- **Datos gestionados**: Precios de hoy y mañana, curva completa, estadísticas.

### 2.5 Entidades de Home Assistant
- **Sensor `sensor.ob_precio_actual`** (unique_id: `ob_precio_actual`):
  - `state`: Precio del tramo actual en €/kWh (4 decimales).
  - `attributes`: `curva_hoy`, `curva_manana`, `fuente`, `ts_actualizacion`.
- **Sensor `sensor.ob_precio_efectivo`** (unique_id: `ob_precio_efectivo`):
  - `state`: Precio efectivo de compra (spot + peajes + cargos + impuestos).
  - `attributes`: `desglose` (spot, peaje, cargo, impuestos), `tramo`.
- **Sensor `sensor.ob_precio_clasificacion`** (unique_id: `ob_precio_clasificacion`):
  - `state`: Clasificación del tramo actual (valle/llano/punta).
  - `attributes`: `curva_clasificacion`, `percentiles` (p25, p50, p75).
- **Sensor `sensor.ob_precio_estadisticas`** (unique_id: `ob_precio_estadisticas`):
  - `state`: Precio medio del día en €/kWh.
  - `attributes`: `min`, `max`, `mediana`.

### 2.6 Flujo de configuración (F1)
- **Parámetros**: `omie.fuente`, `omie.esios_token`, `tarifa.potencia_contratada_kw`, `tarifa.impuesto_electrico_pct`, `tarifa.iva_pct`, `tarifa.aplicar_impuestos_precio`, `tarifa.energia.punta/llano/valle`.
- **Valores por defecto**: Según SPEC.md §7.

### 2.7 Dependencias
- **Permitidas**: `pysolarmanv5` (para F2), `voluptuous` (validación).
- **Nuevas para F1**: Ninguna (usando integración OMIE existente).
- **Manifest**: Solo `voluptuous>=0.15.0`.

---

## 3. Implementación detallada por archivo

### 3.1 `manifest.json`
```json
{
  "domain": "optimizador_bateria_omie",
  "name": "Optimizador Batería OMIE",
  "documentation": "https://github.com/acarr/optimizador-bateria-omie",
  "issue_tracker": "https://github.com/acarr/optimizador-bateria-omie/issues",
  "dependencies": [],
  "codeowners": ["@acarr"],
  "requirements": ["voluptuous>=0.15.0"],
  "homeassistant": "2025.1.0",
  "ios_app": false,
  "single_config_flow": true,
  "version": "0.1.0"
}
```

### 3.2 `const.py`
```python
DOMINIO = "optimizador_bateria_omie"
VERSION = "0.1.0"
INTERVALO_ACTUALIZACION = timedelta(minutes=15)
FUENTE_OMIE_POR_DEFECTO = "omie"
POTENCIA_TARIFA_KW_POR_DEFECTO = 5.75
IMPUESTO_ELECTRICO_PCT_POR_DEFECTO = 5.1127
IVA_PCT_POR_DEFECTO = 21
DIR_CACHE = "custom_components/optimizador_bateria_omie/.data"
PATRON_ARCHIVO_DATOS = "precios_{fecha}.json"
FESTIVOS_NACIONALES = ["01-01", "06-01", "01-05", "15-08", "12-10", "01-11", "06-12", "08-12", "25-12"]
```

### 3.3 `cliente_omie.py`
- **Clase `ClienteOmie`**:
  - `__init__(hass, fuente, esios_token=None)`: Inicializa con referencia a `hass`.
  - `async def obtener_precios_del_dia(fecha)`: Obtiene precios para la fecha dada.
  - `async def _obtener_de_integracion_omie(fecha)`: Usa `hass.services.call('omie', 'get_prices_for_date', {...})`.
  - `async def _obtener_de_redata(fecha)`: Petición HTTP a REData (fallback).
  - `async def _obtener_de_esios(fecha)`: Petición HTTP a ESIOS (si token disponible).
  - `async def _normalizar_a_15min(ranuras)`: Normaliza a 96 tramos.
  - `async def _escribir_cache(fecha, ranuras)`: Escribe en cache.
  - `async def _leer_cache(fecha)`: Lee de cache.
- **Errores**: `ErrorFuenteOmie`, `ErrorIntegracionNoDisponible`, `ErrorTimeoutOmie`.

### 3.4 `tarifa.py`
- **Clase `ModeloTarifa`**:
  - `__init__(peajes_energia, cargos_energia, peajes_potencia, impuestos)`: Configuración.
  - `obtener_periodo(tramo_utc, es_festivo)`: Devuelve "punta", "llano", "valle".
  - `obtener_precio_efectivo(precio_spot, tramo_utc, es_festivo)`: Calcula precio efectivo.
  - `clasificar_por_percentiles(precios_dia)`: Clasifica tramos por percentiles.
  - `obtener_estadisticas(precios_dia)`: Devuelve min/max/mediana.

### 3.5 `coordinador.py`
- **Clase `CoordinadorDatosOmie`** (hereda de `DataUpdateCoordinator`):
  - `async def _async_update_data()`: Actualiza precios de hoy y mañana.
  - `async def refrescar_precios_manana()`: Refresco a las 13:45 CET.
  - `obtener_ranura_actual()`: Devuelve la `Ranura` del tramo actual.

### 3.6 `flujo_configuracion.py`
- Flujo inicial para configuración de OMIE y tarifa.
- Schema con `voluptuous`.

### 3.7 `entidades.py`
- Implementar 4 sensores heredando de `SensorEntity`:
  - `SensorPrecioActual` (`sensor.ob_precio_actual`)
  - `SensorPrecioEfectivo` (`sensor.ob_precio_efectivo`)
  - `SensorPrecioClasificacion` (`sensor.ob_precio_clasificacion`)
  - `SensorPrecioEstadisticas` (`sensor.ob_precio_estadisticas`)

---

## 4. Tests

### 4.1 Fixtures (`conftest.py`)
- `fixture_respuesta_integracion_omie`: Respuesta simulada de `omie.get_prices_for_date`.
- `fixture_respuesta_integracion_omie_horario`: Respuesta para día con 92/100 tramos.
- `fixture_respuesta_redata`: Respuesta JSON de REData.
- `mock_hass`: Mock de HA con servicio `omie.get_prices_for_date` simulado.

### 4.2 `test_cliente_omie.py`
- `test_obtener_precios_del_dia_integracion`: Verificar llamada a `omie.get_prices_for_date`.
- `test_obtener_precios_del_dia_fallback`: Verificar fallback a REData.
- `test_obtener_precios_del_dia_cache`: Verificar cache.
- `test_normalizar_a_15min`: Verificar normalización.
- `test_normalizar_a_15min_horario`: Verificar manejo de días con cambio horario.
- `test_integracion_no_disponible`: Verificar manejo de error.

### 4.3 `test_tarifa.py`
- `test_obtener_periodo_laborable`: Verificar clasificación en día laborable.
- `test_obtener_periodo_fin_de_semana`: Verificar S-D son valle.
- `test_obtener_periodo_festivo`: Verificar festivos son valle.
- `test_obtener_precio_efectivo`: Verificar cálculo con peajes+cargos+impuestos.
- `test_clasificar_por_percentiles`: Verificar clasificación.
- `test_obtener_estadisticas`: Verificar cálculo de estadísticas.

### 4.4 `test_entidades.py`
- Tests para cada sensor: `test_sensor_precio_actual`, `test_sensor_precio_efectivo`, `test_sensor_clasificacion`, `test_sensor_estadisticas`.

---

## 5. Riesgos y dependencias externas

### 5.1 Riesgos técnicos
| Riesgo | Impacto | Mitigación |
|---|---|---|
| Integración OMIE no responde | Alto | Fallback a REData; cache de 24h. |
| Formato de respuesta cambia | Medio | Tests con fixtures; validación de schema. |
| Días con 92/100 tramos | Medio | Lógica de normalización robusta; tests específicos. |

### 5.2 Dependencias del usuario
- **Validación**: Verificar que precios coinciden con OMIE durante 3 días seguidos.

### 5.3 Dependencias entre fases
- F1 **no depende** de F2-F6.
- F2-F6 **dependen** de F1 (usarán `ClienteOmie` y `ModeloTarifa`).

---

## 6. Pasos de verificación

1. **Lint**: `ruff check .` (debe pasar sin errores).
2. **Tests**: `pytest -q` (todos los tests en verde).
3. **Manual**:
   - Instalar el componente en HA.
   - Configurar vía UI.
   - Verificar que los sensores `sensor.ob_precio_*` se actualizan cada 15 minutos.
   - Verificar que precios coinciden con OMIE.

---

## 7. Criterio de aceptación (SPEC.md §8)

✅ **Requisitos F1**:
- [ ] `ClienteOmie` con integración OMIE + REData + ESIOS (fallback).
- [ ] Cache en disco con TTL y reintentos.
- [ ] Normalización a tramos de 15 min.
- [ ] `ModeloTarifa` con peajes+cargos y precio efectivo.
- [ ] Sensores `ob_precio_*` funcionando con unique_ids en español.
- [ ] Flujo de configuración inicial.
- [ ] Tests con fixtures.
- [ ] `ruff check` y `pytest` en verde.

✅ **Criterio de salida**:
- Precio del tramo y precio efectivo coinciden con OMIE durante 3 días seguidos.

---

## 8. Preguntas abiertas

No hay preguntas abiertas. Todos los datos han sido confirmados.

---

## 9. Datos confirmados por el usuario

✅ **Fuente de precios**: Usar `omie.get_prices_for_date` de la integración OMIE existente como fuente primaria.  
✅ **Formato de respuesta OMIE**: Devuelve tramos de 15 minutos en €/kWh (MTU15).  
✅ **Festivos nacionales**: 9 fechas oficiales (01-01, 06-01, 01-05, 15-08, 12-10, 01-11, 06-12, 08-12, 25-12).  
✅ **Huso horario**: CET/CEST (usar `hass.helpers.now()`).  
✅ **Nombres en español**: Variables, sensores, unique_ids, etc. en español.

---

## 10. Tareas pendientes para el usuario

- [ ] **Validar precios**: Comparar `sensor.ob_precio_actual` y `sensor.ob_precio_efectivo` con OMIE durante 3 días.
- [ ] **Confirmar festivos locales**: Lista adicional a los 9 nacionales si los hay.
- [ ] **Confirmar entidad de clima**: Para F3.

---

## 11. Notas adicionales

- **Dry-run**: En F1 no hay escritura al inversor. `seguridad.dry_run` en flujo de configuración.
- **Modularidad**: Módulos de F1 reutilizables en F2-F6 (ej: `ClienteOmie` para planificador en F3).
- **Documentación**: Docstrings en inglés para funciones públicas (estándar HA), comentarios en español.
- **Integración OMIE**: Asume que la integración `omie` está instalada. Fallback a REData/ESIOS si no lo está.
- **Nombres en español**: Prioridad para todo el código del componente (clases, métodos, variables, constantes, unique_ids).
