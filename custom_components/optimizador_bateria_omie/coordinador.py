"""Coordinador de datos para la integración Optimizador Batería OMIE."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from custom_components.optimizador_bateria_omie.cliente_omie import (
    ClienteOmie,
    Ranura,
)
from custom_components.optimizador_bateria_omie.tarifa import ModeloTarifa

_LOGGER = logging.getLogger(__name__)


@dataclass
class DatosOmie:
    """Datos de precios OMIE."""

    precios_hoy: list[Ranura]
    precios_manana: list[Ranura] | None
    clasificaciones_hoy: list[str]
    clasificaciones_manana: list[str] | None
    estadisticas_hoy: dict
    estadisticas_manana: dict | None
    fuente: str
    ts_actualizacion: datetime


class CoordinadorDatosOmie(DataUpdateCoordinator):
    """Coordinador para actualizar datos de precios OMIE."""

    def __init__(
        self,
        hass,
        cliente_omie: ClienteOmie,
        modelo_tarifa: ModeloTarifa,
        config_entry: ConfigEntry | None = None,
    ):
        """Inicializa el coordinador."""
        super().__init__(
            hass,
            _LOGGER,
            name="Optimizador Batería OMIE",
            update_interval=timedelta(minutes=15),
            config_entry=config_entry,
        )
        self.cliente_omie = cliente_omie
        self.modelo_tarifa = modelo_tarifa
        self._datos: DatosOmie | None = None
        
        # Inicializar con datos vacíos
        self._datos = DatosOmie(
            precios_hoy=[],
            precios_manana=None,
            clasificaciones_hoy=[],
            clasificaciones_manana=None,
            estadisticas_hoy={"min": 0, "max": 0, "mediana": 0},
            estadisticas_manana=None,
            fuente="inicializando",
            ts_actualizacion=datetime.now(tz=UTC),
        )

    async def _async_update_data(self):
        """Actualiza los datos de precios."""
        _LOGGER.info("Actualizando datos de precios OMIE...")
        try:
            # Obtener precios de hoy y mañana
            hoy = datetime.now(tz=UTC).date()
            manana = hoy + timedelta(days=1)
            _LOGGER.info(f"Obteniendo precios para hoy: {hoy} y mañana: {manana}")

            # Obtener precios
            precios_hoy = await self.cliente_omie.obtener_precios_del_dia(hoy)
            _LOGGER.info(f"Precios hoy obtenidos: {len(precios_hoy)} ranuras")
            if precios_hoy:
                _LOGGER.info(f"Primera ranura: {precios_hoy[0].fecha_hora_utc.isoformat()} - {precios_hoy[0].precio_eur_kwh}€/kWh")
                _LOGGER.info(f"Última ranura: {precios_hoy[-1].fecha_hora_utc.isoformat()} - {precios_hoy[-1].precio_eur_kwh}€/kWh")
            else:
                _LOGGER.warning("No se obtuvieron precios para hoy, los sensores no estarán disponibles")
            
            # Los precios de mañana no siempre están publicados: cualquier
            # fallo se ignora y se clasifica solo el día en curso.
            try:
                precios_manana = await self.cliente_omie.obtener_precios_del_dia(manana)
            except Exception:  # noqa: BLE001
                precios_manana = None

            # Calcular precios efectivos y clasificaciones
            precios_efectivos_hoy = [
                self.modelo_tarifa.obtener_precio_efectivo(r.precio_eur_kwh, r.fecha_hora_utc)
                for r in precios_hoy
            ]
            clasificaciones_hoy = self.modelo_tarifa.clasificar_por_percentiles(
                precios_efectivos_hoy
            )

            if precios_manana:
                precios_efectivos_manana = [
                    self.modelo_tarifa.obtener_precio_efectivo(
                        r.precio_eur_kwh, r.fecha_hora_utc
                    )
                    for r in precios_manana
                ]
                clasificaciones_manana = self.modelo_tarifa.clasificar_por_percentiles(
                    precios_efectivos_manana
                )
            else:
                precios_efectivos_manana = None
                clasificaciones_manana = None

            # Calcular estadísticas
            estadisticas_hoy = self.modelo_tarifa.obtener_estadisticas(precios_efectivos_hoy)
            
            if precios_efectivos_manana:
                estadisticas_manana = self.modelo_tarifa.obtener_estadisticas(
                    precios_efectivos_manana
                )
            else:
                estadisticas_manana = None

            # Crear objeto DatosOmie
            self._datos = DatosOmie(
                precios_hoy=precios_hoy,
                precios_manana=precios_manana,
                clasificaciones_hoy=clasificaciones_hoy,
                clasificaciones_manana=clasificaciones_manana,
                estadisticas_hoy=estadisticas_hoy,
                estadisticas_manana=estadisticas_manana,
                fuente=precios_hoy[0].fuente if precios_hoy else "desconocida",
                ts_actualizacion=datetime.now(tz=UTC),
            )
            _LOGGER.info(f"Datos actualizados correctamente. Fuente: {self._datos.fuente}, tramos: {len(self._datos.precios_hoy)}")

        except Exception as e:
            _LOGGER.exception("Error al actualizar datos")
            # Crear datos vacíos para evitar que los sensores fallen
            self._datos = DatosOmie(
                precios_hoy=[],
                precios_manana=None,
                clasificaciones_hoy=[],
                clasificaciones_manana=None,
                estadisticas_hoy={"min": 0, "max": 0, "mediana": 0},
                estadisticas_manana=None,
                fuente="desconocida",
                ts_actualizacion=datetime.now(tz=UTC),
            )
            raise UpdateFailed(f"Error al actualizar datos: {e}")

    @property
    def datos(self) -> DatosOmie | None:
        """Devuelve los datos actuales del coordinador."""
        return self._datos

    def _buscar_ranura(self, ranuras: list[Ranura], ahora: datetime) -> Ranura | None:
        """Busca la ranura que contiene el instante dado."""
        for ranura in ranuras:
            fin_ranura = (
                ranura.fecha_hora_fin_utc
                if ranura.fecha_hora_fin_utc
                else ranura.fecha_hora_utc + timedelta(minutes=15)
            )
            if ranura.fecha_hora_utc <= ahora < fin_ranura:
                return ranura
        return None

    def obtener_precio_actual(self) -> float | None:
        """Obtiene el precio actual."""
        if not self._datos or not self._datos.precios_hoy:
            _LOGGER.debug("No hay datos de precios hoy")
            return None

        ahora = datetime.now(tz=UTC)
        _LOGGER.debug(f"Buscando precio actual para hora UTC: {ahora.isoformat()}")
        _LOGGER.debug(
            f"Rango de ranuras: {self._datos.precios_hoy[0].fecha_hora_utc.isoformat()}"
            f" a {self._datos.precios_hoy[-1].fecha_hora_utc.isoformat()}"
        )

        ranura = self._buscar_ranura(self._datos.precios_hoy, ahora)
        # Entre las 00:00 y las 02:00 locales (CEST) la ranura actual
        # pertenece al día local siguiente, que ya está en precios_manana.
        if ranura is None and self._datos.precios_manana:
            ranura = self._buscar_ranura(self._datos.precios_manana, ahora)

        if ranura is not None:
            _LOGGER.debug(f"Ranura actual: {ranura.fecha_hora_utc.isoformat()} - {ranura.precio_eur_kwh}€/kWh")
            return ranura.precio_eur_kwh

        _LOGGER.warning(f"No se encontró ranura actual para hora UTC: {ahora.isoformat()}")
        _LOGGER.warning(
            f"Fecha de primera ranura: {self._datos.precios_hoy[0].fecha_hora_utc.isoformat()}"
        )
        _LOGGER.warning(
            f"Fecha de última ranura: {self._datos.precios_hoy[-1].fecha_hora_utc.isoformat()}"
        )
        return None

    def obtener_precio_efectivo_actual(self) -> float | None:
        """Obtiene el precio efectivo actual."""
        precio_actual = self.obtener_precio_actual()
        if precio_actual is None:
            return None

        ahora = datetime.now(tz=UTC)
        return self.modelo_tarifa.obtener_precio_efectivo(precio_actual, ahora)

    def obtener_ranura_actual(self) -> Ranura | None:
        """Obtiene la ranura actual."""
        if not self._datos or not self._datos.precios_hoy:
            return None

        ahora = datetime.now(tz=UTC)
        ranura = self._buscar_ranura(self._datos.precios_hoy, ahora)
        # Entre las 00:00 y las 02:00 locales (CEST) la ranura actual
        # pertenece al día local siguiente, que ya está en precios_manana.
        if ranura is None and self._datos.precios_manana:
            ranura = self._buscar_ranura(self._datos.precios_manana, ahora)
        return ranura

    def obtener_clasificacion_actual(self) -> str | None:
        """Obtiene la clasificación actual."""
        if not self._datos or not self._datos.clasificaciones_hoy:
            return None

        ahora = datetime.now(tz=UTC)
        # La clasificación está en la misma posición que el tramo horario
        minuto_actual = ahora.hour * 60 + ahora.minute
        tramo = minuto_actual // 15
        
        if tramo < len(self._datos.clasificaciones_hoy):
            return self._datos.clasificaciones_hoy[tramo]
        
        return None

    def obtener_estadisticas_actual(self) -> dict | None:
        """Obtiene las estadísticas actuales."""
        if not self._datos:
            return None

        return self._datos.estadisticas_hoy
