"""Modelo de tarifa eléctrica española 2.0TD."""

from datetime import UTC, datetime

from custom_components.optimizador_bateria_omie.const import FESTIVOS_ESPANA


class ConfiguracionTarifa:
    """Configuración de la tarifa eléctrica."""

    def __init__(
        self,
        potencia_contratada_kw: float = 5.75,
        impuesto_electrico_pct: float = 0.051127,
        iva_pct: float = 0.21,
        aplicar_impuestos_precio: bool = True,
    ):
        self.potencia_contratada_kw = potencia_contratada_kw
        self.impuesto_electrico_pct = impuesto_electrico_pct
        self.iva_pct = iva_pct
        self.aplicar_impuestos_precio = aplicar_impuestos_precio


class PeriodoTarifa:
    """Define los horarios de los períodos tarifarios 2.0TD."""

    # Horarios para días laborables (Lunes-Viernes), franjas locales CET (UTC+1)
    # convertidas a UTC (SPEC.md §5.6):
    # Punta local: 10:00-14:00 y 18:00-22:00 → 09:00-13:00 y 17:00-21:00 UTC
    # Llano local: 08:00-10:00, 14:00-18:00 y 22:00-24:00 → 07:00-09:00,
    #   13:00-17:00 y 21:00-23:00 UTC
    # Valle local: 00:00-08:00 → 23:00-07:00 UTC (a caballo del día)
    # Sábados, domingos y festivos: valle todo el día
    
    @classmethod
    def es_punta(cls, fecha_hora_utc: datetime) -> bool:
        """Verifica si la hora está en período punta."""
        hour = fecha_hora_utc.hour

        # Punta: 09:00-13:00 y 17:00-21:00 UTC
        return (hour >= 9 and hour < 13) or (hour >= 17 and hour < 21)
    
    @classmethod
    def es_llano(cls, fecha_hora_utc: datetime) -> bool:
        """Verifica si la hora está en período llano."""
        hour = fecha_hora_utc.hour

        # Llano: 07:00-09:00, 13:00-17:00 y 21:00-23:00 UTC
        # (local CET: 08:00-10:00, 14:00-18:00 y 22:00-24:00, SPEC.md §5.6)
        return (
            (hour >= 7 and hour < 9)
            or (hour >= 13 and hour < 17)
            or (hour >= 21 and hour < 23)
        )

    @classmethod
    def es_valle(cls, fecha_hora_utc: datetime) -> bool:
        """Verifica si la hora está en período valle."""
        hour = fecha_hora_utc.hour

        # Valle: 23:00-07:00 UTC (local CET: 00:00-08:00)
        return hour >= 23 or hour < 7


class ModeloTarifa:
    """Modelo de tarifa eléctrica 2.0TD con peajes y cargos."""

    # Peajes de acceso a la red (2.0TD) - €/kWh
    # Fuente: SPEC.md §5.6 (BOE)
    PEAJE_ACCESO_PUNTA = 0.033261  # €/kWh
    PEAJE_ACCESO_LLANO = 0.016409  # €/kWh
    PEAJE_ACCESO_VALLE = 0.000077  # €/kWh

    # Cargos del sistema (2.0TD) - €/kWh
    CARGO_SISTEMA_PUNTA = 0.064292  # €/kWh
    CARGO_SISTEMA_LLANO = 0.012858  # €/kWh
    CARGO_SISTEMA_VALLE = 0.003215  # €/kWh

    def __init__(self, config: ConfiguracionTarifa | None = None):
        self.config = config or ConfiguracionTarifa()

    def obtener_periodo(self, fecha_hora_utc: datetime) -> str:
        """Determina el período tarifario (punta, llano, valle)."""
        fecha_local = fecha_hora_utc.astimezone(UTC)  # Ya está en UTC
        
        # Verificar si es festivo o fin de semana
        if self.es_festivo(fecha_local) or self.es_fin_de_semana(fecha_local):
            return "valle"
        
        # Verificar período según la hora
        if PeriodoTarifa.es_punta(fecha_local):
            return "punta"
        elif PeriodoTarifa.es_llano(fecha_local):
            return "llano"
        else:
            return "valle"

    def obtener_peaje_cargo(self, periodo: str) -> float:
        """Obtiene el peaje + cargo para un período dado (SPEC.md §5.6)."""
        if periodo == "punta":
            return self.PEAJE_ACCESO_PUNTA + self.CARGO_SISTEMA_PUNTA
        elif periodo == "llano":
            return self.PEAJE_ACCESO_LLANO + self.CARGO_SISTEMA_LLANO
        else:  # valle
            return self.PEAJE_ACCESO_VALLE + self.CARGO_SISTEMA_VALLE

    def obtener_precio_efectivo(self, precio_spot: float, fecha_hora_utc: datetime) -> float:
        """Calcula el precio efectivo incluyendo peajes, cargos e impuestos."""
        periodo = self.obtener_periodo(fecha_hora_utc)
        peaje_cargo = self.obtener_peaje_cargo(periodo)
        
        # Precio con peajes y cargos
        precio_con_peajes = precio_spot + peaje_cargo
        
        if self.config.aplicar_impuestos_precio:
            # Aplicar impuesto eléctrico (5.1127%)
            precio_con_impuesto = precio_con_peajes * (1 + self.config.impuesto_electrico_pct)
            # Aplicar IVA (21%)
            precio_efectivo = precio_con_impuesto * (1 + self.config.iva_pct)
        else:
            precio_efectivo = precio_con_peajes
        
        return round(precio_efectivo, 6)

    def clasificar_por_percentiles(self, precios: list[float]) -> list[str]:
        """Clasifica una lista de precios en valle, llano, punta usando percentiles."""
        if not precios or len(precios) < 3:
            return ["valle"] * 96
        
        # Ordenar precios
        precios_ordenados = sorted(precios)
        
        # Calcular percentiles
        n = len(precios_ordenados)
        p33 = int(n * 0.33)
        p66 = int(n * 0.66)
        
        umbral_valle_llano = precios_ordenados[p33]
        umbral_llano_punta = precios_ordenados[p66]
        
        # Clasificar cada precio
        clasificaciones = []
        for precio in precios:
            if precio <= umbral_valle_llano:
                clasificaciones.append("valle")
            elif precio <= umbral_llano_punta:
                clasificaciones.append("llano")
            else:
                clasificaciones.append("punta")
        
        return clasificaciones

    def obtener_estadisticas(self, precios: list[float]) -> dict:
        """Obtiene estadísticas de una lista de precios."""
        if not precios:
            return {"min": 0.0, "max": 0.0, "mediana": 0.0}
        
        precios_ordenados = sorted(precios)
        n = len(precios_ordenados)
        
        min_val = min(precios_ordenados)
        max_val = max(precios_ordenados)
        
        # Calcular mediana
        if n % 2 == 0:
            mediana = (precios_ordenados[n // 2 - 1] + precios_ordenados[n // 2]) / 2
        else:
            mediana = precios_ordenados[n // 2]
        
        return {
            "min": round(min_val, 6),
            "max": round(max_val, 6),
            "mediana": round(mediana, 6),
        }

    def es_festivo(self, fecha: datetime) -> bool:
        """Verifica si una fecha es festivo nacional."""
        mes_dia = (fecha.month, fecha.day)
        return mes_dia in FESTIVOS_ESPANA

    def es_fin_de_semana(self, fecha: datetime) -> bool:
        """Verifica si una fecha es fin de semana (sábado o domingo)."""
        return fecha.weekday() >= 5  # 5=sábado, 6=domingo
