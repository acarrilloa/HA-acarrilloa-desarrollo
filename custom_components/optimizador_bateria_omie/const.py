"""Constantes para el componente Optimizador Batería OMIE."""

DOMAIN = "optimizador_bateria_omie"

# Versión
VERSION = "1.0.0"

# Configuración por defecto
DEFAULT_FUENTE_PRIORITARIA = "omie"
DEFAULT_USAR_CACHE = True
DEFAULT_DIAS_CACHE = 7

# Sensores
SENSOR_PRECIO_ACTUAL = "ob_precio_actual"
SENSOR_PRECIO_EFECTIVO = "ob_precio_efectivo"
SENSOR_PRECIO_CLASIFICACION = "ob_precio_clasificacion"
SENSOR_PRECIO_ESTADISTICAS = "ob_precio_estadisticas"

# Atributos
ATTR_MIN = "min"
ATTR_MAX = "max"
ATTR_MEDIANA = "mediana"
ATTR_FUENTE = "fuente"
ATTR_TS_ACTUALIZACION = "ts_actualizacion"

# Festivos nacionales España (dd-mm)
FESTIVOS_ESPANA = {
    (1, 1),   # Año Nuevo
    (1, 6),   # Día de Reyes
    (5, 1),   # Fiesta del Trabajo
    (8, 15),  # Asunción de la Virgen
    (10, 12), # Fiesta Nacional de España
    (11, 1),  # Todos los Santos
    (12, 6),  # Día de la Constitución
    (12, 8),  # Inmaculada Concepción
    (12, 25), # Navidad
}
