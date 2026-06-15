# Informe Tecnico

## Resumen del proyecto

`clinical-triage-simulator` es un sistema academico de simulacion discreta para un servicio de urgencias. El proyecto combina:

- simulacion de eventos discretos
- enriquecimiento clinico estructurado a partir de texto libre
- algoritmos de planificacion para priorizacion de pacientes
- comparacion experimental reproducible entre algoritmos

## Configuracion LLM validada para la entrega final

La configuracion validada para el informe final utilizo exclusivamente:

- proveedor real: `Ollama`
- modelo: `llama3.2:3b`
- ejecucion local
- cache de enriquecimiento para reproducibilidad
- ejecucion final con `--fail-on-llm-fallback`

Durante la corrida final validada:

- no ocurrio fallback a `mock`
- el conteo total de fallback fue `0`
- el enriquecimiento LLM de la corrida validada dependio solo de Ollama

`mock` se mantuvo unicamente como mecanismo controlado para pruebas y para escenarios de respaldo durante desarrollo. `Mistral` sigue siendo un proveedor alternativo soportado por el software, pero no se utilizo en la validacion final reportada. OpenAI y Gemini no forman parte del conjunto final de proveedores soportados para la entrega.

## Fuente de datos final

La validacion final se documento sobre la fuente local `MIMIC-IV-ED Demo`.

La configuracion reproducible del experimento final reportado fue:

- proveedor: `Ollama`
- modelo: `llama3.2:3b`
- fuente de datos: `MIMIC-IV-ED Demo`
- corridas totales: `150`
- exitos totales de Ollama: `3200`
- fallback total: `0`

## Capacidades implementadas

- API FastAPI para salud, simulacion individual, comparacion experimental y exportes
- modelos de dominio para pacientes, recursos, trazas y resultados
- simulador discreto con llegadas, deterioro, despacho continuo, rondas medicas no instantaneas y liberacion de recursos
- algoritmos `fifo`, `greedy`, `astar`, `cpsat` y `simulated_annealing`
- enriquecimiento clinico estructurado con validacion de esquema
- configuracion avanzada de recursos para experimentos de cuello de botella
- trazabilidad por paciente y filtros de timeline
- comparacion experimental con metricas agregadas y ranking balanceado

## Reproducibilidad

La reproducibilidad final depende de:

- semillas fijas
- configuracion explicita de escenarios
- cache LLM reutilizable
- validacion sin fallback mediante `--fail-on-llm-fallback`

Por tanto, los resultados finales usados en el informe corresponden a una configuracion local Ollama-only y no deben mezclarse con ejecuciones donde se haya activado fallback a `mock`.
