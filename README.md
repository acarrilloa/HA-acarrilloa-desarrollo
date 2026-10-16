# Optimizador Batería OMIE

![Versión](https://img.shields.io/badge/versión-0.6.5-blue) ![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.10.01+-41BDF5) ![Python](https://img.shields.io/badge/Python-3.14+-3776AB)

**Custom component para Home Assistant** que optimiza la carga/descarga de baterías usando precios del mercado eláctrico español con resolución de 15 minutos (MTU15) y la tarifa eláctrica 2.0TD.

## Características

### Fase F1 (Implementada) …
- **Obtención de precios OMIE**: Usa la integración OMIE existente (`omie.get_prices_for_date`) como fuente primaria, con fallback a REData y ESIOS
- **Precio efectivo**: Cálculo del precio real de compra incluyendo peajes, cargos e impuestos según la tarifa 2.0TD
- **Clasificación de tramos**: Identifica automáticamente períodos punta, llano y valle (laborables) o valle todo el día (festivos, fines de semana)
- **Sensores disponibles**:
  - `sensor.ob_precio_actual`: Precio del tramo actual en €/kWh
  - `sensor.ob_precio_efectivo`: Precio efectivo con peajes, cargos e impuestos
  - `sensor.ob_precio_clasificacion`: Clasificación del tramo actual (valle/llano/punta)
  - `sensor.ob_precio_estadisticas`: Estadísticas del día (mínimo, máximo, mediana)

### Fases futuras 🚧
- **F2**: Integración con Solarman para telemetría del inversor Deye
- **F3**: Predicción de consumo (estadística) + Planificador greedy
- **F4**: Control real del inversor con salvaguardas
- **F5**: Predicción ML + Optimización con programación lineal
- **F6**: Dashboard Lovelace + Notificaciones + Informes

## Requisitos

- **Home Assistant**: 2026.10.1 o superior
- **Python**: 3.14 o superior
- **Integración OMIE**: Recomendada (pero no obligatoria, hay fallback a REData)

## Instalación

### Mátodo 1: HACS (recomendado)

1. Añadir este repositorio como repositorio personalizado en HACS:
   - Ve a **HACS > Integraciones > Tres puntos (â‹®) > Repositorios personalizados**
   - Añade URL: `https://github.com/acarrilloa/optimizador-bateria-omie`
   - Selecciona categoría: **Integración**
   - Haz clic en **Añadir**

2. Reinicia Home Assistant

3. Instala el componente:
   - Ve a **HACS > Integraciones**
   - Busca **"Optimizador Batería OMIE"**
   - Haz clic en **INSTALAR**

4. Configura la integración:
   - Ve a **Configuración > Dispositivos y servicios**
   - Haz clic en **AÑADIR INTEGRACIÓN**
   - Busca **"Optimizador Batería OMIE"**
   - Selecciona la fuente de precios (recomendado: **Integración OMIE**)
   - Configura parámetros de tarifa si es necesario

### Mátodo 2: Manual

1. Copia la carpeta `custom_components/optimizador_bateria_omie/` a tu directorio `custom_components/` de Home Assistant

2. Reinicia Home Assistant

3. Añade la integración:
   - Ve a **Configuración > Dispositivos y servicios**
   - Haz clic en **AÑADIR INTEGRACIÓN**
   - Busca **"Optimizador Batería OMIE"**

## Configuración

### Parámetros disponibles

#### Fuente de precios (OMIE)
| Parámetro | Tipo | Valor por defecto | Descripción |
|---|---|---|---|
| `fuente` | selección | `omie` | Fuente de precios: `omie`, `redata`, `esios` |
| `esios_token` | texto | - | Token de API para ESIOS (opcional) |

#### Tarifa eláctrica
| Parámetro | Tipo | Valor por defecto | Descripción |
|---|---|---|---|
| `potencia_contratada_kw` | número | 5.75 | Potencia contratada en kW |
| `impuesto_electrico_pct` | número | 5.1127 | Impuesto eláctrico (%) |
| `iva_pct` | número | 21.0 | IVA (%) |
| `aplicar_impuestos_precio` | booleano | true | Aplicar impuestos al precio |
| `margen_potencia_w` | número | 300 | Margen de seguridad en W |

### Festivos nacionales

El componente incluye automáticamente los festivos oficiales para precios de electricidad en España:
- 01-01 (Año Nuevo)
- 06-01 (Día de Reyes)
- 01-05 (Fiesta del Trabajo)
- 15-08 (Asunción de la Virgen)
- 12-10 (Fiesta Nacional de España)
- 01-11 (Todos los Santos)
- 06-12 (Día de la Constitución)
- 08-12 (Inmaculada Concepción)
- 25-12 (Navidad)

## Sensores

### `sensor.ob_precio_actual`
- **Estado**: Precio del tramo actual en €/kWh
- **Atributos**:
  - `curva_hoy`: Lista de precios del día actual (JSON)
  - `curva_manana`: Lista de precios del día siguiente (JSON, opcional)
  - `fuente`: Origen de los datos (`omie`, `redata`, `esios`)
  - `ts_actualizacion`: Fecha de última actualización

### `sensor.ob_precio_efectivo`
- **Estado**: Precio efectivo de compra en €/kWh (incluye spot + peajes + cargos + impuestos)
- **Atributos**:
  - `desglose`: Desglose del precio (spot, peaje, cargo, impuestos)
  - `tramo`: Clasificación del tramo (valle/llano/punta)

### `sensor.ob_precio_clasificacion`
- **Estado**: Clasificación del tramo actual (valle/llano/punta)
- **Atributos**:
  - `curva_clasificacion`: Lista de clasificaciones de todos los tramos
  - `percentiles`: Percentiles p25, p50, p75

### `sensor.ob_precio_estadisticas`
- **Estado**: Precio medio del día en €/kWh
- **Atributos**:
  - `min`: Precio mínimo
  - `max`: Precio máximo
  - `mediana`: Precio mediano

## Tarifa 2.0TD (España)

El componente aplica automáticamente los peajes y cargos de la tarifa 2.0TD:

### Períodos de energía (€/kWh)
| Período | Peaje | Cargo | Total |
|---|---|---|---|
| Punta | 0.033261 | 0.064292 | 0.097553 |
| Llano | 0.016409 | 0.012858 | 0.029267 |
| Valle | 0.000077 | 0.003215 | 0.003292 |

### Horarios (días laborables)
| Período | Horario |
|---|---|
| Punta | 10:00-14:00, 18:00-22:00 |
| Llano | 08:00-10:00, 14:00-18:00, 22:00-24:00 |
| Valle | 00:00-08:00 |

**Fines de semana y festivos**: Valle todo el día.

## Ejemplo de automations

### Notificación cuando el precio está bajo

```yaml
automation:
  - alias: "Aviso precio bajo"
    trigger:
      - platform: template
        value_template: >
          {{ state('sensor.ob_precio_efectivo') | float < 0.10 }}
    action:
      - service: notify.notify
        data:
          message: "Precio bajo: {{ state('sensor.ob_precio_efectivo') }} €/kWh"
          title: "OMIE - Precio bajo"
```

### Acciones basadas en clasificación

```yaml
automation:
  - alias: "Modo batería según precio"
    trigger:
      - platform: state
        entity_id: sensor.ob_precio_clasificacion
    action:
      - choose:
          - conditions:
              - condition: state
                entity_id: sensor.ob_precio_clasificacion
                state: "valle"
            sequence:
              - service: switch.turn_on
                entity_id: switch.carga_bateria
        default:
          - service: switch.turn_off
            entity_id: switch.carga_bateria
```

## Solución de problemas

### La integración no aparece
- Verifica que la carpeta está en `custom_components/optimizador_bateria_omie/`
- Reinicia Home Assistant
- Verifica que el archivo `manifest.json` está correcto

### Los sensores muestran "unavailable"
- Verifica que la integración OMIE está instalada (o configura REData/ESIOS)
- Verifica la conexión a internet
- Consulta los logs de Home Assistant

### Los precios no coinciden con OMIE
- El componente usa la integración OMIE existente como fuente primaria
- Los precios pueden tener un retraso de hasta 24 horas (cache)
- Verifica que la integración OMIE está configurada correctamente

## Desarrollo

### Estructura del proyecto

```
optimizador-bateria-omie/
â”œâ”€â”€ custom_components/
â”‚   â””â”€â”€ optimizador_bateria_omie/
â”‚       â”œâ”€â”€ __init__.py              # Entry point
â”‚       â”œâ”€â”€ manifest.json            # Metadatos HACS
â”‚       â”œâ”€â”€ const.py                 # Constantes
â”‚       â”œâ”€â”€ cliente_omie.py           # Cliente OMIE
â”‚       â”œâ”€â”€ tarifa.py                # Modelo de tarifa
â”‚       â”œâ”€â”€ coordinador.py           # Coordinador
â”‚       â”œâ”€â”€ entidades.py             # Sensores
â”‚       â”œâ”€â”€ flujo_configuracion.py   # Config flow
â”‚       â””â”€â”€ tests/                   # Tests
â”œâ”€â”€ hacs.json                         # Configuración HACS
â””â”€â”€ README.md                         # Documentación
```

### Ejecutar tests

```bash
# Instalar dependencias
pip install -r custom_components/optimizador_bateria_omie/requirements.txt

# Ejecutar tests
pytest custom_components/optimizador_bateria_omie/tests/ -v

# Verificar estilo
ruff check custom_components/optimizador_bateria_omie/
```

## Licencia

MIT License - Copyright (c) 2026

## Agradecimientos

- [OMIE](https://www.omie.es) - Mercado Ibérico de la Electricidad
- [Red Eláctrica de España](https://www.ree.es) - Datos del sistema eláctrico
- [Home Assistant](https://www.home-assistant.io) - Plataforma de automatización
