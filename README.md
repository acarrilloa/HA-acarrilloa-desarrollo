# Optimizador BaterÃ­a OMIE

![VersiÃ³n](https://img.shields.io/badge/versiÃ³n-0.1.0-blue) ![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.1.0+-41BDF5) ![Python](https://img.shields.io/badge/Python-3.13+-3776AB)

**Custom component para Home Assistant** que optimiza la carga/descarga de baterÃ­as usando precios del mercado elÃ©ctrico espaÃ±ol con resoluciÃ³n de 15 minutos (MTU15) y la tarifa elÃ©ctrica 2.0TD.

## CaracterÃ­sticas

### Fase F1 (Implementada) âœ…
- **ObtenciÃ³n de precios OMIE**: Usa la integraciÃ³n OMIE existente (`omie.get_prices_for_date`) como fuente primaria, con fallback a REData y ESIOS
- **Precio efectivo**: CÃ¡lculo del precio real de compra incluyendo peajes, cargos e impuestos segÃºn la tarifa 2.0TD
- **ClasificaciÃ³n de tramos**: Identifica automÃ¡ticamente perÃ­odos punta, llano y valle (laborables) o valle todo el dÃ­a (festivos, fines de semana)
- **Sensores disponibles**:
  - `sensor.ob_precio_actual`: Precio del tramo actual en â‚¬/kWh
  - `sensor.ob_precio_efectivo`: Precio efectivo con peajes, cargos e impuestos
  - `sensor.ob_precio_clasificacion`: ClasificaciÃ³n del tramo actual (valle/llano/punta)
  - `sensor.ob_precio_estadisticas`: EstadÃ­sticas del dÃ­a (mÃ­nimo, mÃ¡ximo, mediana)

### Fases futuras ðŸš§
- **F2**: IntegraciÃ³n con Solarman para telemetrÃ­a del inversor Deye
- **F3**: PredicciÃ³n de consumo (estadÃ­stica) + Planificador greedy
- **F4**: Control real del inversor con salvaguardas
- **F5**: PredicciÃ³n ML + OptimizaciÃ³n con programaciÃ³n lineal
- **F6**: Dashboard Lovelace + Notificaciones + Informes

## Requisitos

- **Home Assistant**: 2026.10.1 o superior
- **Python**: 3.14 o superior
- **IntegraciÃ³n OMIE**: Recomendada (pero no obligatoria, hay fallback a REData)

## InstalaciÃ³n

### MÃ©todo 1: HACS (recomendado)

1. AÃ±adir este repositorio como repositorio personalizado en HACS:
   - Ve a **HACS > Integraciones > Tres puntos (â‹®) > Repositorios personalizados**
   - AÃ±ade URL: `https://github.com/acarrilloa/optimizador-bateria-omie`
   - Selecciona categorÃ­a: **IntegraciÃ³n**
   - Haz clic en **AÃ±adir**

2. Reinicia Home Assistant

3. Instala el componente:
   - Ve a **HACS > Integraciones**
   - Busca **"Optimizador BaterÃ­a OMIE"**
   - Haz clic en **INSTALAR**

4. Configura la integraciÃ³n:
   - Ve a **ConfiguraciÃ³n > Dispositivos y servicios**
   - Haz clic en **AÃ‘ADIR INTEGRACIÃ“N**
   - Busca **"Optimizador BaterÃ­a OMIE"**
   - Selecciona la fuente de precios (recomendado: **IntegraciÃ³n OMIE**)
   - Configura parÃ¡metros de tarifa si es necesario

### MÃ©todo 2: Manual

1. Copia la carpeta `custom_components/optimizador_bateria_omie/` a tu directorio `custom_components/` de Home Assistant

2. Reinicia Home Assistant

3. AÃ±ade la integraciÃ³n:
   - Ve a **ConfiguraciÃ³n > Dispositivos y servicios**
   - Haz clic en **AÃ‘ADIR INTEGRACIÃ“N**
   - Busca **"Optimizador BaterÃ­a OMIE"**

## ConfiguraciÃ³n

### ParÃ¡metros disponibles

#### Fuente de precios (OMIE)
| ParÃ¡metro | Tipo | Valor por defecto | DescripciÃ³n |
|---|---|---|---|
| `fuente` | selecciÃ³n | `omie` | Fuente de precios: `omie`, `redata`, `esios` |
| `esios_token` | texto | - | Token de API para ESIOS (opcional) |

#### Tarifa elÃ©ctrica
| ParÃ¡metro | Tipo | Valor por defecto | DescripciÃ³n |
|---|---|---|---|
| `potencia_contratada_kw` | nÃºmero | 5.75 | Potencia contratada en kW |
| `impuesto_electrico_pct` | nÃºmero | 5.1127 | Impuesto elÃ©ctrico (%) |
| `iva_pct` | nÃºmero | 21.0 | IVA (%) |
| `aplicar_impuestos_precio` | booleano | true | Aplicar impuestos al precio |
| `margen_potencia_w` | nÃºmero | 300 | Margen de seguridad en W |

### Festivos nacionales

El componente incluye automÃ¡ticamente los festivos oficiales para precios de electricidad en EspaÃ±a:
- 01-01 (AÃ±o Nuevo)
- 06-01 (DÃ­a de Reyes)
- 01-05 (Fiesta del Trabajo)
- 15-08 (AsunciÃ³n de la Virgen)
- 12-10 (Fiesta Nacional de EspaÃ±a)
- 01-11 (Todos los Santos)
- 06-12 (DÃ­a de la ConstituciÃ³n)
- 08-12 (Inmaculada ConcepciÃ³n)
- 25-12 (Navidad)

## Sensores

### `sensor.ob_precio_actual`
- **Estado**: Precio del tramo actual en â‚¬/kWh
- **Atributos**:
  - `curva_hoy`: Lista de precios del dÃ­a actual (JSON)
  - `curva_manana`: Lista de precios del dÃ­a siguiente (JSON, opcional)
  - `fuente`: Origen de los datos (`omie`, `redata`, `esios`)
  - `ts_actualizacion`: Fecha de Ãºltima actualizaciÃ³n

### `sensor.ob_precio_efectivo`
- **Estado**: Precio efectivo de compra en â‚¬/kWh (incluye spot + peajes + cargos + impuestos)
- **Atributos**:
  - `desglose`: Desglose del precio (spot, peaje, cargo, impuestos)
  - `tramo`: ClasificaciÃ³n del tramo (valle/llano/punta)

### `sensor.ob_precio_clasificacion`
- **Estado**: ClasificaciÃ³n del tramo actual (valle/llano/punta)
- **Atributos**:
  - `curva_clasificacion`: Lista de clasificaciones de todos los tramos
  - `percentiles`: Percentiles p25, p50, p75

### `sensor.ob_precio_estadisticas`
- **Estado**: Precio medio del dÃ­a en â‚¬/kWh
- **Atributos**:
  - `min`: Precio mÃ­nimo
  - `max`: Precio mÃ¡ximo
  - `mediana`: Precio mediano

## Tarifa 2.0TD (EspaÃ±a)

El componente aplica automÃ¡ticamente los peajes y cargos de la tarifa 2.0TD:

### PerÃ­odos de energÃ­a (â‚¬/kWh)
| PerÃ­odo | Peaje | Cargo | Total |
|---|---|---|---|
| Punta | 0.033261 | 0.064292 | 0.097553 |
| Llano | 0.016409 | 0.012858 | 0.029267 |
| Valle | 0.000077 | 0.003215 | 0.003292 |

### Horarios (dÃ­as laborables)
| PerÃ­odo | Horario |
|---|---|
| Punta | 10:00-14:00, 18:00-22:00 |
| Llano | 08:00-10:00, 14:00-18:00, 22:00-24:00 |
| Valle | 00:00-08:00 |

**Fines de semana y festivos**: Valle todo el dÃ­a.

## Ejemplo de automations

### NotificaciÃ³n cuando el precio estÃ¡ bajo

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
          message: "Precio bajo: {{ state('sensor.ob_precio_efectivo') }} â‚¬/kWh"
          title: "OMIE - Precio bajo"
```

### Acciones basadas en clasificaciÃ³n

```yaml
automation:
  - alias: "Modo baterÃ­a segÃºn precio"
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

## SoluciÃ³n de problemas

### La integraciÃ³n no aparece
- Verifica que la carpeta estÃ© en `custom_components/optimizador_bateria_omie/`
- Reinicia Home Assistant
- Verifica que el archivo `manifest.json` estÃ© correcto

### Los sensores muestran "unavailable"
- Verifica que la integraciÃ³n OMIE estÃ© instalada (o configura REData/ESIOS)
- Verifica la conexiÃ³n a internet
- Consulta los logs de Home Assistant

### Los precios no coinciden con OMIE
- El componente usa la integraciÃ³n OMIE existente como fuente primaria
- Los precios pueden tener un retraso de hasta 24 horas (cache)
- Verifica que la integraciÃ³n OMIE estÃ© configurada correctamente

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
â”œâ”€â”€ hacs.json                         # ConfiguraciÃ³n HACS
â””â”€â”€ README.md                         # DocumentaciÃ³n
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

- [OMIE](https://www.omie.es) - Mercado IbÃ©rico de la Electricidad
- [Red ElÃ©ctrica de EspaÃ±a](https://www.ree.es) - Datos del sistema elÃ©ctrico
- [Home Assistant](https://www.home-assistant.io) - Plataforma de automatizaciÃ³n
