"""Cliente para obtener precios de OMIE."""

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import aiohttp

try:
    import pytz
    HAS_PYTZ = True
except ImportError:
    HAS_PYTZ = False

from custom_components.optimizador_bateria_omie.const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfiguracionOmie:
    """Configuración del cliente OMIE."""

    def __init__(
        self,
        fuente_prioritaria: str = "omie",
        usar_cache: bool = True,
        dias_cache: int = 7,
    ):
        self.fuente_prioritaria = fuente_prioritaria
        self.usar_cache = usar_cache
        self.dias_cache = dias_cache


class Ranura:
    """Representa un tramo horario de precios."""

    def __init__(
        self,
        fecha_hora_utc: datetime,
        precio_eur_kwh: float,
        fuente: str,
        fecha_publicacion: datetime,
        fecha_hora_fin_utc: datetime = None,
    ):
        self.fecha_hora_utc = fecha_hora_utc
        self.precio_eur_kwh = precio_eur_kwh
        self.fuente = fuente
        self.fecha_publicacion = fecha_publicacion
        self.fecha_hora_fin_utc = fecha_hora_fin_utc

    def __eq__(self, other):
        """Comparación para tests."""
        if not isinstance(other, Ranura):
            return False
        return (
            self.fecha_hora_utc == other.fecha_hora_utc
            and self.precio_eur_kwh == other.precio_eur_kwh
            and self.fuente == other.fuente
        )


class ErrorFuenteOmie(Exception):
    """Error al obtener datos de una fuente OMIE."""

    pass


class ErrorIntegracionNoDisponible(Exception):
    """Error cuando la integración OMIE no está disponible."""

    pass


class ClienteOmie:
    """Cliente para obtener precios de OMIE."""

    def __init__(self, hass, config: ConfiguracionOmie):
        self.hass = hass
        self.config = config
        # Usar custom_components/optimizador_bateria_omie/cache
        self._dir_cache = Path(hass.config.config_dir) / "custom_components" / DOMAIN / "cache"

        # Asegurar que el directorio de cache existe
        if self.config.usar_cache:
            self._dir_cache.mkdir(parents=True, exist_ok=True)

    async def _obtener_desde_integracion_omie(self, fecha: date) -> list:
        """Obtiene precios usando la integración OMIE."""
        _LOGGER.info(f"Obteniendo precios de OMIE para fecha: {fecha}")
        fecha_str = fecha.strftime("%Y-%m-%d")
        
        # 1. Primero intentar leer de los nuevos sensores específicos
        # sensor.omie_precios_de_es_hoy para hoy
        if fecha == date.today():
            sensor_entity_id = "sensor.omie_precios_de_es_hoy"
            state = self.hass.states.get(sensor_entity_id)
            if state is not None:
                _LOGGER.info(f"Sensor {sensor_entity_id} encontrado, estado: {state.state}")
                if state.attributes is not None:
                    # Buscar el atributo 'precios' que contiene la lista
                    for attr_name in ["precios", "prices", "data", "price_list"]:
                        if attr_name in state.attributes:
                            datos = state.attributes[attr_name]
                            _LOGGER.info(f"Datos obtenidos de {sensor_entity_id}.{attr_name}: tipo={type(datos)}, longitud={len(datos) if datos else 0}")
                            if isinstance(datos, list) and len(datos) > 0:
                                _LOGGER.info(f"Primer elemento: {datos[0]}")
                            return datos
        
        # sensor.omie_precios_de_es_manana para mañana
        if fecha == date.today() + timedelta(days=1):
            sensor_entity_id = "sensor.omie_precios_de_es_manana"
            state = self.hass.states.get(sensor_entity_id)
            if state is not None:
                _LOGGER.info(f"Sensor {sensor_entity_id} encontrado, estado: {state.state}")
                if state.attributes is not None:
                    for attr_name in ["precios", "prices", "data", "price_list"]:
                        if attr_name in state.attributes:
                            datos = state.attributes[attr_name]
                            _LOGGER.info(f"Datos obtenidos de {sensor_entity_id}.{attr_name}: tipo={type(datos)}, longitud={len(datos) if datos else 0}")
                            if isinstance(datos, list) and len(datos) > 0:
                                _LOGGER.info(f"Primer elemento: {datos[0]}")
                            return datos
        
        # 2. Intentar leer del sensor general de precios al contado
        sensor_entity_id = "sensor.omie_precio_al_contado_en_espana"
        state = self.hass.states.get(sensor_entity_id)
        
        if state is not None:
            _LOGGER.info(f"Sensor {sensor_entity_id} encontrado, estado: {state.state}")
            if state.attributes is not None:
                _LOGGER.info(f"Atributos disponibles: {list(state.attributes.keys())}")
                for attr_name in ["precios", "prices", "data", "price_list", "hourly_prices"]:
                    if attr_name in state.attributes:
                        datos = state.attributes[attr_name]
                        _LOGGER.info(f"Datos obtenidos de {sensor_entity_id}.{attr_name}: tipo={type(datos)}, longitud={len(datos) if datos else 0}")
                        if isinstance(datos, list) and len(datos) > 0:
                            _LOGGER.info(f"Primer elemento: {datos[0]}")
                        return datos
        
        # 3. Si no hay datos en sensores, intentar llamar al servicio omie.get_prices_for_date
        try:
            service_data = {"date": fecha_str}
            _LOGGER.info(f"Llamando a servicio omie.get_prices_for_date con {service_data}")
            
            try:
                response = await self.hass.services.async_call(
                    domain="omie",
                    service="get_prices_for_date",
                    service_data=service_data,
                    blocking=True,
                    return_response=True,
                )
            except Exception as e:
                _LOGGER.error(f"Error al llamar al servicio omie.get_prices_for_date: {e}")
                raise ErrorIntegracionNoDisponible(f"Servicio no disponible: {e}")
            
            _LOGGER.info(f"Respuesta del servicio OMIE: tipo={type(response)}")
            
            if response is None:
                _LOGGER.warning("El servicio devolvió None")
                raise ErrorIntegracionNoDisponible("Servicio devolvió None")
            
            # Si la respuesta es una lista, devolverla directamente
            if isinstance(response, list):
                _LOGGER.info(f"Respuesta es una lista con {len(response)} elementos")
                if response:
                    _LOGGER.info(f"Primer elemento: {response[0]}")
                return response
            
            # Si la respuesta es un diccionario, intentar extraer los datos
            if isinstance(response, dict):
                _LOGGER.info(f"Respuesta es un diccionario: {list(response.keys())}")
                # El servicio OMIE devuelve {'es': [...], 'pt': [...], ...}
                # Extraer los precios para España
                if "es" in response:
                    _LOGGER.info("Extrayendo datos de la clave 'es' (España)")
                    return response["es"]
                elif "data" in response:
                    _LOGGER.info("Extrayendo datos de 'data'")
                    return response["data"]
                elif "prices" in response:
                    _LOGGER.info("Extrayendo datos de 'prices'")
                    return response["prices"]
                else:
                    _LOGGER.error(f"Diccionario no contiene claves esperadas. Claves disponibles: {list(response.keys())}")
                    raise ErrorIntegracionNoDisponible(f"Formato de respuesta inesperado: {response}")
            
            # Si es otro tipo, convertir a lista
            _LOGGER.warning(f"Tipo de respuesta inesperado: {type(response)}, valor: {response}")
            return [response]
            
        except Exception as e:
            _LOGGER.error(f"Error al obtener datos del servicio OMIE: {e}")
            raise ErrorIntegracionNoDisponible(f"Servicio OMIE no disponible: {e}")

    async def _obtener_desde_redata(self, fecha: date) -> list:
        """Obtiene precios desde REData (fallback)."""
        url = f"https://api.preciodelaluz.es/v1/prices?date={fecha.strftime('%Y-%m-%d')}"
        
        _LOGGER.info(f"Obteniendo precios de REData para {fecha}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise ErrorFuenteOmie(f"REData devuelve status {response.status}")
                data = await response.json()
                _LOGGER.info(f"REData devolvió: tipo={type(data)}, keys={data.keys() if isinstance(data, dict) else 'N/A'}")
                
                # Manejar diferentes formatos de respuesta
                if isinstance(data, dict):
                    if "data" in data:
                        datos = data["data"]
                        _LOGGER.info(f"Datos de REData: {len(datos) if isinstance(datos, list) else type(datos)}")
                        return datos
                    elif isinstance(data, list):
                        return data
                    else:
                        _LOGGER.error(f"Formato de REData inesperado: {data}")
                        return []
                elif isinstance(data, list):
                    return data
                else:
                    _LOGGER.error(f"Tipo de respuesta de REData inesperado: {type(data)}")
                    return []

    async def _obtener_desde_esios(self, fecha: date) -> list:
        """Obtiene precios desde ESIOS (fallback alternativo)."""
        # Implementación placeholder para ESIOS
        return []

    def _normalizar_a_15min(self, datos: list, fecha: date) -> list:
        """Normaliza datos a tramos de 15 minutos (96 tramos por día).
        
        Formato esperado de omie.get_prices_for_date:
        [
            {"start": "2026-10-06T00:00:00+02:00", "end": "2026-10-06T00:15:00+02:00", "price": 0.20831},
            {"start": "2026-10-06T00:15:00+02:00", "end": "2026-10-06T00:30:00+02:00", "price": 0.20731},
            ...
        ]
        """
        _LOGGER.debug(f"Normalizando datos para {fecha}. Tipo: {type(datos)}, Valor: {datos}")
        ranuras = []
        
        # Datos_por_tramo: diccionario {tramo: precio}
        datos_por_tramo = {}
        
        # Si datos no es una lista, convertirlo
        if datos is None:
            _LOGGER.warning("Datos es None, devolviendo lista vacía")
            return ranuras
        
        if not isinstance(datos, list):
            _LOGGER.warning(f"Datos no es una lista, es {type(datos)}. Intentando convertir...")
            if isinstance(datos, dict):
                # Si es un diccionario, intentar extraer la lista de precios
                # Formato OMIE: {'es': [...], 'pt': [...]}
                if "es" in datos:
                    datos = datos["es"]
                    _LOGGER.info("Datos extraídos de la clave 'es'")
                elif "data" in datos:
                    datos = datos["data"]
                elif "prices" in datos:
                    datos = datos["prices"]
                else:
                    _LOGGER.error(f"Diccionario no contiene claves esperadas. Claves disponibles: {list(datos.keys())}")
                    return ranuras
            else:
                _LOGGER.error(f"Tipo de datos no soportado: {type(datos)}")
                return ranuras
        
        if datos:
            _LOGGER.debug(f"Primer dato: {datos[0] if isinstance(datos, list) else datos}")
        
        # Intentar diferentes formatos de entrada
        for item in datos:
            # Formato OMIE (start, end, price con timezone)
            if isinstance(item, dict) and "start" in item and "price" in item:
                start_str = item.get("start", "")
                try:
                    # Parsear el start con timezone
                    start_dt = datetime.fromisoformat(start_str)
                    # Convertir a UTC
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                    else:
                        start_dt = start_dt.astimezone(timezone.utc)
                    
                    hora = start_dt.hour
                    minuto = start_dt.minute
                    precio = float(item.get("price", 0.0))
                    tramo = hora * 4 + (minuto // 15)
                    datos_por_tramo[tramo] = precio
                    continue
                except Exception as e:
                    _LOGGER.warning(f"Error parseando start {start_str}: {e}")
            
            # Formato 1: lista de dicts con hour, minute, price
            if isinstance(item, dict):
                hora = item.get("hour", 0)
                minuto = item.get("minute", 0)
                precio = item.get("price", 0.0)
                tramo = hora * 4 + (minuto // 15)
                datos_por_tramo[tramo] = precio
                continue
            
            # Formato 2: lista de dicts con datetime y price
            if isinstance(item, dict) and "datetime" in item:
                dt = item.get("datetime")
                if isinstance(dt, str):
                    # Parsear datetime string
                    try:
                        dt_obj = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                        if dt_obj.tzinfo is None:
                            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
                        else:
                            dt_obj = dt_obj.astimezone(timezone.utc)
                        hora = dt_obj.hour
                        minuto = dt_obj.minute
                        precio = item.get("price", 0.0)
                        tramo = hora * 4 + (minuto // 15)
                        datos_por_tramo[tramo] = precio
                    except Exception:
                        continue
                elif isinstance(dt, datetime):
                    dt_obj = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                    hora = dt_obj.hour
                    minuto = dt_obj.minute
                    precio = item.get("price", 0.0)
                    tramo = hora * 4 + (minuto // 15)
                    datos_por_tramo[tramo] = precio
                continue
            
            # Formato 3: lista de strings (JSON)
            if isinstance(item, str):
                try:
                    import json
                    parsed = json.loads(item)
                    if isinstance(parsed, dict):
                        # Intentar formato OMIE en string
                        if "start" in parsed and "price" in parsed:
                            start_str = parsed.get("start", "")
                            start_dt = datetime.fromisoformat(start_str)
                            if start_dt.tzinfo is None:
                                start_dt = start_dt.replace(tzinfo=timezone.utc)
                            else:
                                start_dt = start_dt.astimezone(timezone.utc)
                            hora = start_dt.hour
                            minuto = start_dt.minute
                            precio = float(parsed.get("price", 0.0))
                            tramo = hora * 4 + (minuto // 15)
                            datos_por_tramo[tramo] = precio
                        else:
                            hora = parsed.get("hour", 0)
                            minuto = parsed.get("minute", 0)
                            precio = parsed.get("price", 0.0)
                            tramo = hora * 4 + (minuto // 15)
                            datos_por_tramo[tramo] = precio
                except Exception:
                    continue
        
        # Crear 96 tramos (24 horas * 4 tramos de 15 min)
        # Si tenemos datos con start/end, usamos esos timestamps directamente
        if datos and isinstance(datos, list) and len(datos) > 0 and isinstance(datos[0], dict) and "start" in datos[0]:
            _LOGGER.debug(f"Procesando formato OMIE con start/end")
            for item in datos:
                start_str = item.get("start", "")
                try:
                    start_dt = datetime.fromisoformat(start_str)
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                    else:
                        start_dt = start_dt.astimezone(timezone.utc)
                    
                    precio = float(item.get("price", 0.0))
                    _LOGGER.debug(f"Creando ranura: {start_dt.isoformat()} - {precio}")
                    
                    # Obtener el end time si está disponible
                    end_str = item.get("end", "")
                    try:
                        end_dt = datetime.fromisoformat(end_str)
                        if end_dt.tzinfo is None:
                            end_dt = end_dt.replace(tzinfo=timezone.utc)
                        else:
                            end_dt = end_dt.astimezone(timezone.utc)
                    except Exception:
                        end_dt = start_dt + timedelta(minutes=15)
                    
                    ranura = Ranura(
                        fecha_hora_utc=start_dt,
                        precio_eur_kwh=precio,
                        fuente="omie",
                        fecha_publicacion=datetime.now(tz=timezone.utc),
                        fecha_hora_fin_utc=end_dt,
                    )
                    ranuras.append(ranura)
                except Exception as e:
                    _LOGGER.warning(f"Error creando ranura desde {start_str}: {e}")
                    continue
            
            # Si tenemos menos de 96 tramos, rellenar con 0.0
            if len(ranuras) < 96:
                _LOGGER.warning(f"Solo se obtuvieron {len(ranuras)} tramos, rellenando a 96")
                # Obtener la fecha del primer tramo para rellenar
                base_date = ranuras[0].fecha_hora_utc.date() if ranuras else fecha
                for tramo in range(len(ranuras), 96):
                    hora = tramo // 4
                    minuto = (tramo % 4) * 15
                    fecha_hora_utc = datetime(
                        base_date.year, base_date.month, base_date.day, hora, minuto, tzinfo=timezone.utc
                    )
                    ranura = Ranura(
                        fecha_hora_utc=fecha_hora_utc,
                        precio_eur_kwh=0.0,
                        fuente="omie",
                        fecha_publicacion=datetime.now(tz=timezone.utc),
                        fecha_hora_fin_utc=fecha_hora_utc + timedelta(minutes=15),
                    )
                    ranuras.append(ranura)
            
            return ranuras
        
        # Formatos antiguos (sin start/end)
        if not ranuras:  # Solo si no tenemos ranuras del formato OMIE
            for tramo in range(96):
                hora = tramo // 4
                minuto = (tramo % 4) * 15
                
                precio = datos_por_tramo.get(tramo, None)
                if precio is None:
                    precio = 0.0
                
                fecha_hora_utc = datetime(
                    fecha.year, fecha.month, fecha.day, hora, minuto, tzinfo=timezone.utc
                )
                
                ranura = Ranura(
                    fecha_hora_utc=fecha_hora_utc,
                    precio_eur_kwh=float(precio),
                    fuente="omie",
                    fecha_publicacion=datetime.now(tz=timezone.utc),
                    fecha_hora_fin_utc=fecha_hora_utc + timedelta(minutes=15),
                )
                ranuras.append(ranura)
        
        return ranuras

    async def obtener_precios_del_dia(self, fecha: date) -> list:
        """Obtiene los precios para un día específico."""
        def _read_cache():
            """Operación bloqueante: leer cache."""
            cache_file = self._dir_cache / f"{fecha.strftime('%Y-%m-%d')}.json"
            if cache_file.exists():
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return None

        def _write_cache(ranuras: list):
            """Operación bloqueante: escribir cache."""
            cache_file = self._dir_cache / f"{fecha.strftime('%Y-%m-%d')}.json"
            cache_data = [
                {
                    "fecha_hora_utc": r.fecha_hora_utc.isoformat(),
                    "precio_eur_kwh": r.precio_eur_kwh,
                    "fuente": r.fuente,
                    "fecha_publicacion": r.fecha_publicacion.isoformat(),
                    "fecha_hora_fin_utc": r.fecha_hora_fin_utc.isoformat() if r.fecha_hora_fin_utc else None,
                }
                for r in ranuras
            ]
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

        # Verificar cache
        if self.config.usar_cache:
            try:
                cached_data = await self.hass.async_add_executor_job(_read_cache)
                if cached_data is not None:
                    return [
                        Ranura(
                            fecha_hora_utc=datetime.fromisoformat(d["fecha_hora_utc"]),
                            precio_eur_kwh=d["precio_eur_kwh"],
                            fuente=d["fuente"],
                            fecha_publicacion=datetime.fromisoformat(d["fecha_publicacion"]),
                            fecha_hora_fin_utc=datetime.fromisoformat(d["fecha_hora_fin_utc"]) if d.get("fecha_hora_fin_utc") else None,
                        )
                        for d in cached_data
                    ]
            except Exception as e:
                _LOGGER.warning(f"Error leyendo cache: {e}")

        # Obtener datos de la fuente prioritaria
        try:
            datos = None
            fuente = None
            
            # Intentar obtener de la integración OMIE
            if self.config.fuente_prioritaria == "omie" and "omie" in self.hass.config.components:
                try:
                    datos = await self._obtener_desde_integracion_omie(fecha)
                    fuente = "omie"
                    _LOGGER.info(f"Datos obtenidos de OMIE: tipo={type(datos)}, longitud={len(datos) if datos else 0}")
                except ErrorIntegracionNoDisponible as e:
                    _LOGGER.warning(f"Integración OMIE no disponible: {e}")
                    datos = None
                except Exception as e:
                    _LOGGER.warning(f"Error al obtener datos de OMIE: {e}")
                    _LOGGER.warning(f"Tipo de error: {type(e)}")
                    
                    # Mensajes conocidos de error
                    if "have not been published yet" in str(e):
                        _LOGGER.warning("Los precios no están publicados aún, usando fallback REData")
                        datos = None
                    else:
                        datos = None
            
            # Si no se obtuvieron datos de OMIE o OMIE no es la fuente prioritaria, usar fallback
            if datos is None:
                try:
                    datos = await self._obtener_desde_redata(fecha)
                    fuente = "redata"
                    _LOGGER.info(f"Datos obtenidos de REData: tipo={type(datos)}, longitud={len(datos) if datos else 0}")
                except Exception as e:
                    _LOGGER.warning(f"Error al obtener datos de REData: {e}")
                    datos = None
                
                if datos is None:
                    try:
                        datos = await self._obtener_desde_esios(fecha)
                        fuente = "esios"
                        _LOGGER.info(f"Datos obtenidos de ESIOS: tipo={type(datos)}, longitud={len(datos) if datos else 0}")
                    except Exception as e:
                        _LOGGER.warning(f"Error al obtener datos de ESIOS: {e}")
                        datos = None
            
            if datos is None:
                raise ErrorFuenteOmie("Todas las fuentes fallaron")
        except ErrorFuenteOmie:
            raise ErrorFuenteOmie("Todas las fuentes fallaron")

        # Normalizar datos a 96 tramos
        _LOGGER.info(f"Normalizando datos para {fecha}. Tipo: {type(datos)}, Longitud: {len(datos) if datos else 0}")
        ranuras = self._normalizar_a_15min(datos, fecha)
        _LOGGER.info(f"Normalización completada: {len(ranuras)} ranuras")
        
        # Actualizar fuente en todas las ranuras
        for ranura in ranuras:
            ranura.fuente = fuente

        # Guardar en cache
        if self.config.usar_cache:
            try:
                await self.hass.async_add_executor_job(_write_cache, ranuras)
            except Exception as e:
                _LOGGER.warning(f"Error escribiendo cache: {e}")

        return ranuras
