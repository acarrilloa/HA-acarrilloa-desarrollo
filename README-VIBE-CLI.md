# omie-battery-optimizer — Guía de arranque con Vibe CLI

Paquete listo para que Devstral (vía Vibe CLI) implemente el custom component de HA descrito en `SPEC.md`, siguiendo las reglas de `AGENTS.md` y los prompts por fase de `PROMPTS.md`.

## 1. Preparar el proyecto

Crea la carpeta del proyecto y coloca los tres archivos:

```bash
mkdir -p ~/omie-battery-optimizer && cd ~/omie-battery-optimizer
# copia aquí: SPEC.md, AGENTS.md y PROMPTS.md
git init
```

## 2. Configurar el modelo (una vez)

### Opción A — Devstral local con LM Studio

1. Descarga el modelo en LM Studio (p. ej. `Devstral-Small-2-24B`) y activa el servidor local: la API OpenAI-compatible queda en `http://localhost:1234/v1`.
   - Nota de hardware: con una GPU de 8 GB (RX 6600) usa un quant reducido con offload a CPU o contextos cortos; para sesiones largas rinde mejor un quant pequeño + contexto ~32k.
2. Añade el provider en `~/.vibe/config.toml` y actívalo:

```toml
[[providers]]
name = "lmstudio"
api_base = "http://localhost:1234/v1"
api_style = "openai"
backend = "generic"

[[models]]
name = "devstral-small"        # el nombre exacto del modelo en LM Studio
provider = "lmstudio"
alias = "devstral-local"

active_model = "devstral-local"
```

Para ejecutar 100 % offline, añade además en `config.toml`:

```toml
enable_telemetry = false
enable_auto_update = false
```

### Opción B — Modelos alojados

Configura tu API key de Mistral (`vibe` te lo pedirá en el primer arranque) y elige modelo con `/model` dentro de la sesión. Esta opción da mejor calidad en contextos largos (la SPEC completa son ~430 líneas).

## 3. Flujo de trabajo por fase (modo interactivo)

```bash
cd ~/omie-battery-optimizer
vibe
```

- La primera vez, el CLI pedirá confirmar la carpeta como *trusted*.
- Lanza cada fase pegando el prompt correspondiente de `PROMPTS.md`, o de forma más corta:

```text
Lee @SPEC.md y @AGENTS.md completos. Ejecuta la fase F1 según la sección "F1" de @PROMPTS.md. Antes de escribir código, crea docs/PLAN_F1.md y espera mi confirmación.
```

- Cambia `F1` por `F2`…`F6` en cada fase. Al reanudar otro día: `vibe --continue`.

### Atajos útiles dentro de la sesión

| Atajo | Uso |
|---|---|
| `Shift+Tab` | Cambiar de agente: `plan` (solo lectura, ideal para revisar el PLAN_FX.md), `accept-edits`, `auto-approve` |
| `!pytest -q` | Ejecutar tests sin salir del agente |
| `!ruff check .` | Verificar estilo |
| `Escape` | Cortar una operación en curso |

### Modo programático (opcional, para pasos mecánicos)

```bash
vibe --prompt "Ejecuta pytest y ruff y corrige lo que falle sin cambiar funcionalidad" --max-turns 20 --trust
```

Con modelo local usa `--max-turns` generoso; con `auto-approve` por defecto, revisa siempre el diff antes de aceptar (`git diff`).

## 4. Ritmo recomendado por fase

1. Arranca con el agente `plan`, revisa `docs/PLAN_FX.md` que propone el agente.
2. Cambia a `accept-edits` para implementar; revisa el diff de cada commit.
3. Verifica tests y lint; lee `docs/RESULTADO_FX.md`.
4. **Antes de avanzar de fase**, completa en el mundo real lo que pide la fase (validación de precios 3 días en F1, probe de registros en F2, semana de dry-run en F3…). Los criterios de salida están en `SPEC.md` §8.
5. No pases a F4 (escrituras reales al inversor) sin haber validado el mapa de registros con `probe_registers` y sin revisar `SPEC.md` §9.

## 5. Datos ya incluidos y pendientes

**Ya en la SPEC:**
- Inversor Deye SUN-6K-SG05LP1-EU-AM2-P y batería Docan 51,2 V 300 Ah (15,36 kWh).
- Datalogger Solarman: IP `192.168.1.76`, serie `3178171873` (config flow en F2).
- Tarifa 2.0TD: peajes y cargos de energía (punta 0,097553 / llano 0,029267 / valle 0,003292 €/kWh), costes fijos de potencia y **potencia contratada 5,75 kW** como restricción dura del plan.
- Remuneración de excedentes: **al mismo precio que la compra** (contrato con mayorista) — arbitraje simétrico activo.

**Pendientes de aportar durante el proceso:**
- Entidad de clima de HA y festivos locales (F3/F5).
- Resultado del probe de registros (comparación con pantalla/APP del Deye) — desbloquea F4.
