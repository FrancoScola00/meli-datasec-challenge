# MeLi DataSec Challenge — Prevención de Fugas (Leak Prevention)

> 🌐 [English](README.md) · **Español**

Cuatro desafíos para el track Sr Cybersecurity Analyst (Leak Prevention). El foco es
**corrección verificada ejecutando** y una **postura explícita de leak-prevention**
(cómo se manejan los datos sensibles), no solo una respuesta que funcione.

| # | Entregable | Qué es | Verificado |
|---|-----------|--------|-----------|
| 1 | `solution_minesweeper.py` | Cuenta minas vecinas | ✅ pytest 12/12 (local) |
| 2 | `solution_best_in_genre.py` | Serie mejor puntuada de un género (API paginada) | ✅ pytest 9/9 mock + ✅ API en vivo |
| 3 | `applicant_query.sql` | Clientes con >3 eventos 'failure' (MySQL 8) | ✅ corrido en MySQL 8.4.9 real |
| 4 | `challenge4/` | Motor de clasificación con LLM + redacción de PII | ✅ pytest 16/16 + eval offline + ✅ demo en vivo |

## Estructura del repositorio
```
solution_minesweeper.py     solution_best_in_genre.py     applicant_query.sql
challenge4/                  # Clasificador LLM (módulo + CLI + eval + demos + DESIGN.md)
tests/                       # suites pytest + seed_and_check.sql + verify_c3.ps1
.claude/skills/              # 3 skills de Claude Code reutilizables
requirements.txt  .python-version  Makefile  run.ps1  conftest.py
```

## Inicio rápido

### Windows (PowerShell)
```powershell
.\run.ps1 install      # crea .venv (Python 3.12) e instala dependencias pineadas
.\run.ps1 test         # corre toda la suite de pytest
.\run.ps1 c1           # demo del Challenge 1
.\run.ps1 c2 Action    # Challenge 2 contra la API en vivo -> "Game of Thrones"
.\run.ps1 c3-verify    # levanta un MySQL 8 descartable, carga el seed y corre la query
.\run.ps1 c4-demo      # clasificación LLM en vivo (necesita OPENROUTER_API_KEY; ver C4)
.\run.ps1 c4-batch     # batch en vivo sobre challenge4/samples.txt
```
Si la execution policy bloquea `.\run.ps1`:
`powershell -ExecutionPolicy Bypass -File .\run.ps1 test`.

### Linux / macOS
```bash
make install   # venv python3.12 + dependencias pineadas
make test
make c2        # API en vivo
make c3-verify # requiere un MySQL 8 corriendo con usuario root
```

### Desde cero en una máquina limpia
1. Instalá **Python 3.12** (ver `.python-version`). En Windows: `winget install Python.Python.3.12`.
2. `run.ps1 install` (o `make install`) para construir `.venv` desde `requirements.txt` (pineado).
3. `run.ps1 test` para verificar todo offline. La llamada en vivo de C2 y la demo en vivo
   de C4 son los únicos pasos que tocan la red; ambos tienen tests mockeados offline.

## Desafíos

### 1 — Minesweeper (`solution_minesweeper.py`, Python 3.12)
`count_neighbouring_mines(board: list) -> list`. Devuelve una matriz **nueva** (no muta
el input); las minas pasan a `9`, las celdas vacías al conteo de sus 8 vecinos. Maneja
bordes, esquinas, `[]`, 1×1, fila/columna única. La validación opcional solo lanza error
con input malformado y no cambia el resultado para inputs válidos.

### 2 — Best in genre (`solution_best_in_genre.py`, Python 3.12)
`bestInGenre(genre: str) -> str`. Recorre todas las páginas de
`jsonmock.hackerrank.com/api/tvseries`, splitea el campo `genre` (separado por comas) y
trimea cada parte, matchea sin distinguir mayúsculas, convierte `imdb_rating` a float de
forma defensiva, y desempata por orden alfabético. **Solo librería estándar** (`urllib`)
para minimizar la superficie de supply-chain; timeout + reintentos con backoff en el HTTP.

### 3 — Fallas de publicidad (`applicant_query.sql`, MySQL 8.x)
Joins `customers → campaigns → events`, filtra `status='failure'`, agrupa por cliente
(`GROUP BY c.id, c.first_name, c.last_name`, seguro para ONLY_FULL_GROUP_BY), mantiene
`HAVING COUNT(*) > 3`, ordena por `failures DESC, customer ASC`. Salida verificada:
```
+-----------------+----------+
| customer        | failures |
+-----------------+----------+
| Whitney Ferrero |        6 |
+-----------------+----------+
```
`tests/verify_c3.ps1` reproduce esto en una instancia MySQL 8 descartable (no es un
archivo graded).

### 4 — Motor de clasificación con LLM (`challenge4/`)
Clasifica texto por `sensitivity` / `category` / `risk_score` / `confidence` /
`rationale`, con `needs_review` para abstención. Ver `challenge4/DESIGN.md` para el
detalle de las decisiones de diseño.
```powershell
# eval offline (sin red, determinista) - golden set + respuestas grabadas
.\.venv\Scripts\python.exe challenge4\eval\evaluate.py

# demo en vivo - narra el pipeline: redacta PII -> manda solo texto redactado -> clasifica
Copy-Item challenge4\.env.example challenge4\.env   # despues pone tu key de OpenRouter
.\run.ps1 c4-demo
.\.venv\Scripts\python.exe challenge4\demo_live.py --text "tu propio texto aca"

# batch en vivo sobre challenge4/samples.txt - imprime una tabla + resumen
.\run.ps1 c4-batch

# CLI machine-readable (un JSON por linea; --file / stdin para batch)
.\.venv\Scripts\python.exe challenge4\classify_cli.py --file challenge4\samples.txt
```

## Razonamiento de seguridad por desafío (leak prevention)
- **C1** — sin datos sensibles; la preocupación es la corrección y **no mutar el estado
  del que llama** (evitar side effects sorpresivos).
- **C2** — habla con un servicio externo. No mandamos secretos, usamos timeout y
  reintentos acotados, y parseamos defensivo para que datos sucios/ausentes no rompan ni
  engañen. Solo stdlib mantiene mínima la superficie de dependencias.
- **C3** — el dato es PII de clientes (nombres, logs de eventos). La query lee lo mínimo
  necesario y expone solo un agregado (nombre + cantidad de fallas). Índices sugeridos
  (`events.campaign_id`, `events.status`, `campaigns.customer_id`) la hacen eficiente a
  escala sin ampliar la exposición.
- **C4** — el ejercicio central de leak-prevention: la PII se **redacta localmente antes**
  de que el texto llegue al LLM de un tercero, solo se loggea texto redactado, la muestra
  se trata como dato no confiable (defensa anti prompt-injection), la salida se valida, y
  el motor **falla cerrado** (fail-closed). Los secretos vienen solo del entorno (`.env`
  está gitignored; `.env.example` documenta el formato).

## Nota sobre Herramientas / MCP
El código entregable **no depende de ningún MCP** ni de runtime no estándar. Durante el
desarrollo se usó el `WebFetch` integrado para confirmar el shape de la API de C2; los
servidores MCP conectados de `claude.ai` (Gmail/Calendar/Drive) se **evitaron a propósito**
(tocan datos sensibles y no aportan acá). `git`/`gh` (CLI, no MCP) se usaron para publicar.

## Estado de verificación (honesto)
- **Verificado localmente:** todas las suites pytest (C1 12, C2 9 mock, C4 16), guardas de
  firma, import sin side effects, eval offline de C4, y C3 contra MySQL 8.4.9 real.
- **Verificado contra servicio externo:** la llamada en vivo de C2 devolvió `Game of
  Thrones` para `Action`; la demo en vivo de C4 corrió end-to-end con un modelo free
  (`nvidia/nemotron-nano-9b-v2:free`), redactando la PII antes de la llamada y devolviendo
  un label `RESTRICTED`.
- **No verificado exhaustivamente:** la precisión real de C4 a escala y el recall del
  redactor de PII por regex frente a formatos adversarios — requieren un set etiquetado
  más grande y pruebas de carga.
