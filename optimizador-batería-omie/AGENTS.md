# AGENTS.md — Reglas de trabajo para el agente de código

Este archivo rige cómo debe trabajar el agente (Devstral) en este repositorio. Ante cualquier duda, `SPEC.md` es la **fuente única de verdad** del proyecto.

## 1. Reglas de ingeniería

- **Plataforma**: custom component de Home Assistant 2025.x+, Python ≥ 3.13. Todo el código HA debe ser `async` (`asyncio`); las llamadas bloqueantes (pysolarmanv5, entrenamiento ML) deben ejecutarse con `hass.async_add_executor_job`.
- **Tipado y estilo**: type hints completos, docstrings de módulo y funciones públicas, `ruff check` limpio en todo momento. Nombres de código en **inglés**; textos de UI y documentación en **español** (`translations/es.json`).
- **Registros Modbus**: las direcciones viven **solo** en `registers.yaml`. Prohibido hardcodear direcciones en el código. Prohibido inventar direcciones: si una no está en el mapa, generar un `TODO` y seguir.
- **Escrituras al inversor** (reglas duras, no negociables):
  1. Si `seguridad.dry_run` es `true`, el Executor **nunca** escribe en el inversor; solo publica el plan.
  2. Antes de habilitar escrituras, exigir que el mapa de registros esté **validado** (`probe_registers` ejecutado con éxito).
  3. Rechazar siempre: corriente > límite del perfil, SOC objetivo fuera de `[10, 100]`, escritura con el inversor en alarma/fault.
  4. Máximo **16 registros por petición Modbus** (limitación del datalogger).
  5. Después de cada escritura, relectura de verificación (write-verify); 3 fallos consecutivos → estado `fallback` y escrituras deshabilitadas hasta intervención humana.
- **Secrets**: IP, serie del datalogger, tokens ESIOS… solo vía config flow / `.storage` de HA. Nunca commitear secretos; `.gitignore` preparado.
- **Dependencias**: pedir confirmación antes de añadir cualquier paquete nuevo. Permitidos sin preguntar: `pysolarmanv5`, `voluptuous`, `scikit-learn` (solo F5), `pulp` (solo F5). Prohibidos: `torch`, `tensorflow`,anything que compile nativo.
- **Tests**: cada fase termina con `pytest` en verde y sin llamadas de red ni hardware (todo con mocks/fixtures). Crear el simulador fake del inversor en F2 y reutilizarlo.

## 2. Proceso por fase

1. **Planificar antes de codificar**: crear `docs/PLAN_FX.md` con la lista de archivos a crear/modificar, decisiones de diseño y riesgos. **Esperar confirmación del usuario** antes de implementar.
2. **Implementar** con commits pequeños y descriptivos (un commit por unidad lógica).
3. **Verificar**: ejecutar `pytest -q` y `ruff check .`; corregir hasta verde.
4. **Cerrar**: actualizar `docs/FASES.md` (estado, pendientes, decisiones) y escribir `docs/RESULTADO_FX.md` con un resumen de 10-15 líneas: qué se implementó, qué falta, qué necesita el usuario (datos, validación en hardware).
5. **No empezar la siguiente fase** sin confirmación explícita del usuario. Las fases y sus criterios de salida están en `SPEC.md` §8.

## 3. Comunicación

- Idioma: **español** en todas las respuestas y documentos.
- Si un prompt del usuario contradice a `SPEC.md`, señalarlo y no continuar con la contradicción sin aclaración.
- Si falta un dato (IP del datalogger, serie, entidad de clima…), **no inventarlo**: dejar `TODO` documentado y seguir con lo que sí se puede avanzar.
- Al terminar cada sesión, listar explícitamente: archivos creados/modificados, comandos para verificar, y pasos que requieren al usuario con acceso al hardware.
