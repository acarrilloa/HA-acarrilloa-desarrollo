# PROMPTS.md — Prompts por fase para Vibe CLI

Cada fase se lanza en una sesión del agente con estos prompts. Cópialos tal cual (o referéncialos con `@PROMPTS.md` como se explica en el README). Todos parten de que el agente lee `@SPEC.md` y `@AGENTS.md`.

---

## F1 — Módulo de precios y tarifa

```text
Lee @SPEC.md y @AGENTS.md completos antes de empezar.

Ejecuta la fase F1 del roadmap (SPEC.md §8): módulo de precios.

Alcance de esta sesión:
1. Crea el scaffold del repositorio según SPEC.md §11 (custom component omie_battery_optimizer, hacs.json, README, tests/).
2. Implementa OmieClient (omie_client.py) con las fuentes de RF-01 (SPEC.md §3): API pública OMIE (api.omie.es, mercado diario con resolución de 15 min, publicación ~13:45 CET con reintento/backoff) como principal, y REData/apidatos (time_trunc=quarter) como fallback, con cacheo en disco conforme a SPEC.md §5.1.
3. Implementa TariffModel (tariff.py) conforme a SPEC.md §5.6: peajes+cargos por periodo de consumo (punta/llano/valle; sábados, domingos y festivos nacionales en valle todo el día), cargos de potencia como coste fijo (solo informes), impuesto eléctrico e IVA configurables, y cálculo de precio efectivo de compra por tramo.
4. Crea el DataUpdateCoordinator, config flow inicial y las entidades de precio de SPEC.md §6: sensor.omb_precio_actual (con atributos curva_hoy/curva_mañana), sensor.omb_precio_efectivo, sensor.omb_precio_clasificacion (valle/llano/punta por percentiles) y estadísticas mín/máx/mediana.
5. Tests con fixtures de JSON (incluye un día con 92/100 tramos por cambio horario) y mocks; añade tests del TariffModel con días laborables, fin de semana y festivo; pytest en verde y ruff limpio.

Antes de escribir código: crea docs/PLAN_F1.md con archivos, decisiones y riesgos, y espera mi confirmación. Recuerda que dry_run=true por defecto y que en esta fase no se escribe nada en el inversor.
```

---

## F2 — Cliente Solarman y calibración de registros

```text
Lee @SPEC.md y @AGENTS.md completos antes de empezar.

Ejecuta la fase F2 del roadmap (SPEC.md §8): telemetría Solarman y calibración de registros.

Alcance de esta sesión:
1. Implementa SolarmanClient (solarman_client.py): wrapper async sobre pysolarmanv5 (IP, puerto 8899, serie del datalogger, todo configurable vía config flow; nada hardcodeado), reconexión automática, semáforo para serializar escrituras y bloque ≤ 16 registros por petición.
2. Crea registers.yaml con el perfil `deye-sun-6k-sg05lp1-am2` y las DOS familias candidatas de SPEC.md §5.3 (A y B) como perfiles alternativos con nombre.
3. Implementa el servicio `omie_battery_optimizer.probe_registers` (lectura + comparación con valor esperado del HMI/APP) y el flujo de validación: las escrituras quedan bloqueadas hasta que un probe sea exitoso.
4. Implementa el simulador fake del inversor (clase que implementa el mapa de registros) para tests del executor sin hardware.
5. Entidades de telemetría en HA según registers.yaml (SOC, potencias, temperatura, consumo, PV, red), con la opción telemetry_source: solarman_modbus | ha_entities.

Datos del datalogger (ya confirmados en SPEC.md): IP fija 192.168.1.76, serie 3178171873. Inclúyelos como valores por defecto del config flow (editables), nunca hardcodeados en el código.

Antes de escribir código: crea docs/PLAN_F2.md y espera mi confirmación.
```

---

## F3 — Predicción v1 (estadística) y planificador greedy en dry-run

```text
Lee @SPEC.md y @AGENTS.md completos antes de empezar.

Ejecuta la fase F3 del roadmap (SPEC.md §8): predicción estadística y planificador greedy en dry-run.

Alcance de esta sesión:
1. Implementa ConsumptionForecaster v1 (forecaster.py): perfil estadístico por tramo×tipo de día (laborable/festivo/vacaciones) con mediana y bandas p10/p90 sobre el histórico de consumo a 15 min (ventana de 28 días). Fallback a persistencia (mismo día de la semana anterior) cuando no hay datos suficientes. La recogida del histórico debe funcionar tanto desde statistics de HA como desde la telemetría propia.
2. Implementa Planner v1 (planner.py): estrategia greedy en dos capas conforme a SPEC.md §5.5, valorando compra y venta con el precio efectivo del TariffModel de F1 — con valorar_venta_como_compra=true la venta se valora al mismo precio que la compra del tramo (contrato con mayorista, SPEC.md §5.6). Restricción dura: importación total (consumo + carga batería) ≤ 5,75 kW con margen de 0,3 kW. Salida: plan por tramos con acción (AUTOCONSUMO/CARGA_RED/VENTA_RED/MANTENER), potencia, SOC previsto, coste_sin_plan vs coste_con_plan y ahorro estimado.
3. Publica sensor.omb_plan (con el plan completo en atributos), sensor.omb_prediccion_consumo y sensor.omb_ahorro_hoy (estimado).
4. Crea las entidades number/switch de parámetros de SPEC.md §6 (incluida number.omb_potencia_max_red, defecto 5750 W) y el servicio regenerate_plan; los cambios recalculan el plan en ≤ 60 s.
5. Tests del planner con los escenarios de SPEC.md §10 (valle/punta, precio negativo, SOC 0/50/100, venta deshabilitada) con seed fija, incluyendo un test de que nunca se supera la potencia contratada y otro del umbral de rentabilidad del arbitraje (p_punta − p_valle > margen + pérdida por η).

En esta fase el plan SOLO se publica: prohibida cualquier escritura al inversor (dry_run=true). Antes de escribir código: docs/PLAN_F3.md y espera confirmación.
```

---

## F4 — Executor: control real con salvaguardas

```text
Lee @SPEC.md y @AGENTS.md completos antes de empezar.

Ejecuta la fase F4 del roadmap (SPEC.md §8): executor con control real.

Alcance de esta sesión:
1. Implementa Executor (executor.py): aplica el plan escribiendo en el inversor en cada cambio de tramo (corriente de carga, límites SOC, flags de carga/venta desde registers.yaml), con TODAS las reglas duras de AGENTS.md §1: write-verify, máximo 12 escrituras/hora, rechazo si dry_run, si el probe no validó el mapa, o si hay alarma/fault.
2. Guard de potencia contratada (SPEC.md §5.6 y §9): si la importación medida (consumo casa + carga batería) supera el 95 % de 5,75 kW, reducir progresivamente la corriente de carga de la batería.
3. Implementa el estado fallback: ante 3 fallos consecutivos, reestablecer el modo autoconsumo nativo del inversor (valores seguros) y deshabilitar escrituras + notificación persistente en HA.
4. Watchdog: replanificar si la desviación SOC real vs previsto supera el 10 %, si llegan precios nuevos o si cambian parámetros.
5. Auditoría JSONL (data/ del componente): cada plan, cada escritura, cada error; nunca se sobreescribe.
6. Servicios force_mode y release_manual conforme a SPEC.md §6.
7. Tests de todo el executor con el simulador fake de F2, incluyendo los fallos inyectados (escritura fallida, lectura de verificación incorrecta, alarma del inversor) y la activación del guard de potencia.

Antes de escribir código: docs/PLAN_F4.md y espera confirmación. La activación real (dry_run=false) SOLO la hará el usuario manualmente; tu código debe asumir dry_run=true siempre en los tests.
```

---

## F5 — Predicción ML y optimización LP

```text
Lee @SPEC.md y @AGENTS.md completos antes de empezar.

Ejecuta la fase F5 del roadmap (SPEC.md §8): forecaster ML y optimización LP.

Alcance de esta sesión:
1. Amplía ConsumptionForecaster con el modelo ML de SPEC.md §5.4 (Gradient Boosting de scikit-learn) con features de calendario (tramo, día de semana, festivo, vacaciones, mes) y clima (temperatura prevista, irradiancia si existe). Mantén el fallback en cascada: ML → perfil estadístico → persistencia.
2. Reentrenamiento semanal nocturno como job de HA; modelo persistido en el directorio de datos; backtesting walk-forward con MAPE expuesto en sensor.omb_forecast_quality.
3. Sustituye el planner greedy por la optimización LP (PuLP) conforme a SPEC.md §5.5, manteniendo el greedy como fallback documentado. Incluye la restricción de importación ≤ 5,75 kW (§5.6) y usa la banda p90 del consumo de forma conservadora para decisiones de venta.
4. Auditoría de ahorro real: comparar cada tramo lo consumido/comprado/vendido real vs plan; sensor.omb_ahorro_hoy pasa de estimado a real.
5. Tests con dataset sintético reproducible (seed fija): objetivo MAPE < 20 % en tramos de alto consumo.

Puedes añadir scikit-learn y pulp como dependencias del manifest según AGENTS.md. Antes de escribir código: docs/PLAN_F5.md y espera confirmación.
```

---

## F6 — Dashboard, notificaciones e informes

```text
Lee @SPEC.md y @AGENTS.md completos antes de empezar.

Ejecuta la fase F6 del roadmap (SPEC.md §8): pulido y usabilidad.

Alcance de esta sesión:
1. Dashboard Lovelace completo: precio del tramo con curva del día (coloreada valle/llano/punta), precio efectivo con desglose (spot/peajes/impuestos), plan de la batería (SOC previsto vs real), predicción de consumo, ahorro acumulado y estado del sistema (fuente de precios, dry_run, últimos errores).
2. Notificaciones de decisiones relevantes: plan diario al publicarse precios de D+1, cambio de modo de la batería, entrada en fallback, activación del guard de potencia contratada, y aviso si el plan prevé comprar/vender fuera de lo habitual.
3. Informe mensual exportable (markdown/CSV) con: energía comprada/vendida/ahorrada, ahorro € vs coste_sin_plan, calidad de predicción y coste fijo de potencia.
4. README de usuario con capturas placeholder, docs/INSTALACION.md paso a paso (HACS manual + config flow) y guía de validación del probe.

Antes de escribir código: docs/PLAN_F6.md y espera confirmación.
```

---

## Prompt de depuración / mantenimiento (uso según necesidad)

```text
Lee @SPEC.md y @AGENTS.md. Revisa docs/FASES.md para ver el estado del proyecto y el error que describo a continuación:

[describe aquí el problema: logs, entidad, tramo horario, comportamiento esperado vs real]

Diagnostica la causa, propón la corrección en docs/FIX.md y espera mi confirmación antes de tocar código. Si la corrección afecta a SPEC.md, propón también el cambio de especificación.
```
