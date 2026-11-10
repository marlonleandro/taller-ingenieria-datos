# Taller integrador — De sensores IoT al dashboard

**Fundamentos de Arquitectura Cloud y Contenedores** · *Maestría en Ingeniería de Datos*

Laboratorio reproducible que recorre el ciclo completo de un producto de datos —
**fuentes → ingesta → landing → Bronze → Silver → Gold → consumo** — sobre telemetría
industrial sintética, con capas de **calidad**, **observabilidad** y **FinOps**.

| Dato | Valor |
|---|---|
| Caso | *Andes Mining*: 48 equipos industriales, 6 zonas, 30 días |
| Volumen base | **180 000 lecturas** (181 800 en Bronze con reenvíos simulados) |
| Origen de datos | **100 % sintético** (semilla fija `20261109`) |
| Entorno | Python local · sin cuenta cloud · sin cargos |
| Ejecución completa | **~20–40 s** (medido: 22 s) en un equipo de gama media |
| Espacio en disco | ~4 MB de fuentes + ~19 MB de artefactos generados |

> **Pregunta guía:** ¿cómo convertimos telemetría industrial imperfecta en indicadores
> confiables y económicos que puedan escalar de miles a millones de registros diarios?

---

## 1. Contenido del paquete

| Archivo / carpeta | Qué es | ¿Debe distribuirse? |
|---|---|---|
| [Taller_Integrador_IoT_Cloud.ipynb](./Taller_Integrador_IoT_Cloud.ipynb) | **Notebook del taller**: 26 celdas (14 markdown + 12 código), 9 secciones, ya ejecutado con salidas | Sí |
| [generar_datos.py](./generar_datos.py) | Generador de las fuentes sintéticas (30 archivos + 2 maestros) | Sí |
| [datos_fuente/](./datos_fuente) | Fuentes: 30 × `iot_2026-10-*.csv.gz`, `catalogo_equipos.csv`, `mantenimientos.csv` | Sí (o regenerarlas) |
| [ARQUITECTURA_CLOUD.md](./ARQUITECTURA_CLOUD.md) | Propuesta de evolución a la nube: arquitectura lógica, alternativas por proveedor, IaaS/PaaS/Serverless, controles, extensión opcional en S3 | Sí |
| [data_lake/](./data_lake) | Salidas del pipeline (`landing`, `bronze`, `silver`, `gold`) | No — se regenera al ejecutar |
| [reportes/](./reportes) | Reportes y dashboard: `calidad_pipeline.csv`, `metricas_pipeline.json`, `finops_escenarios.csv`, `dashboard_iot.png` | No — se regeneran al ejecutar |
| `dashboard_iot.png` (raíz) | Captura del panel para diapositivas. La versión viva la regenera el notebook en `reportes/` | Sí |

> **Para distribuir el taller** solo hacen falta el notebook, `generar_datos.py`, `datos_fuente/` y
> `ARQUITECTURA_CLOUD.md`. Todo lo demás es reproducible ejecutando el notebook.
>
> ⚠️ Ojo con `.gitignore`: sus reglas `*.csv` y `*.parquet` **excluyen** `datos_fuente/catalogo_equipos.csv`
> y `datos_fuente/mantenimientos.csv`, que son entradas obligatorias. Si vas a versionar o compartir el
> taller, verifica que esos dos archivos viajen con el paquete.

**El notebook es autocontenido:** genera, limpia, agrega, grafica y mide. No descarga nada
ni se conecta a ningún servicio.

---

## 2. Requisitos

* **Python 3.11+** con `pandas`, `numpy`, `matplotlib`, `ipykernel` (Jupyter/VS Code).
* **Opcional:** `pyarrow` — solo habilita la exportación comparativa a Parquet de la sección 8.
* 1 núcleo y 1 GB de RAM bastan.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install pandas numpy matplotlib ipykernel pyarrow
```

Versiones con las que se validó: Python 3.11.9 · pandas 3.0.3 · numpy 2.4.6 · matplotlib 3.11.1 · pyarrow 25.0.1.

---

## 3. Puesta en marcha

### Opción A — Usar las fuentes incluidas (recomendada en clase)

```powershell
# 1. Abrir el notebook y seleccionar el kernel del entorno virtual
code Taller_Integrador_IoT_Cloud.ipynb
# 2. Run All
```

La celda 2 tiene `REGENERAR = False`: si `data_lake/` está vacío, el pipeline se reconstruye solo.

### Opción B — Regenerar las fuentes desde cero

```powershell
mkdir datos_fuente          # el script NO crea la carpeta
python generar_datos.py     # ~5 s → 30 archivos CSV.gz + 2 maestros
```

> ⚠️ **Obligatorio:** si regeneras las fuentes, **borra antes `data_lake/`**.
> Ver [§8](#8-solución-de-problemas) — el control de integridad de Landing lo exige.

### Opción C — Empezar limpio

```powershell
Remove-Item -Recurse -Force data_lake, reportes
```

---

## 4. Flujo del pipeline

```text
FUENTES            30 CSV.gz (6 000 lecturas/día) + catálogo + mantenimientos
   │               anomalías inyectadas a propósito
   ▼
INGESTA            copia idempotente + verificación SHA-256 + manifest_ingesta.csv
   ▼
LANDING            copia inmutable del original (evidencia auditable)
   ▼
BRONZE             consolidación SIN descartar nada + columna de linaje (archivo_fuente)
   ▼
SILVER             tipado · deduplicación · reglas de calidad · cuarentena · enriquecimiento
   ▼
GOLD               KPIs por día/zona/tipo + ranking de equipos por riesgo
   ▼
CONSUMO            SQLite (datamart) + panel gráfico de 4 vistas
   ├─ OBSERVABILIDAD   métricas por etapa, SLO y latencia de ingesta
   └─ FINOPS           costos simulados y escenario optimizado
```

### Secciones del notebook

| § | Sección | Qué hace | Artefacto que produce |
|---|---|---|---|
| 0 | Ruta de aprendizaje | Mapa del pipeline y decisiones del curso | — |
| 1 | Fuentes | Catálogo de equipos + umbrales + mantenimientos | `datos_fuente/*.csv.gz` |
| 2 | Ingesta → Landing | Copia idempotente con verificación de hash; rechaza modificaciones silenciosas | `landing/manifest_ingesta.csv` |
| 3 | Bronze | Concatenación íntegra; **conserva duplicados y errores** + `archivo_fuente` | `bronze/telemetria_bronze.csv.gz` |
| 4 | Silver | Tipado, deduplicación por `evento_id`, validaciones de calidad (5 motivos de rechazo), cuarentena con motivo, alertas, latencia, energía estimada | `silver/telemetria_silver.csv.gz`, `cuarentena`, `duplicados`, `reportes/calidad_pipeline.csv` |
| 5 | Gold | Agregados por día/zona/tipo y ranking de equipos por alertas | `gold/indicadores_diarios.csv`, `gold/ranking_equipos.csv` |
| 6 | Consumo | Datamart SQLite + panel de 4 gráficos | `gold/datamart_iot.sqlite`, `reportes/dashboard_iot.png` |
| 7 | Observabilidad | Métricas de pipeline vs. métricas de negocio; SLO y latencia p95 | `reportes/metricas_pipeline.json` |
| 8 | Cloud native + FinOps | Escenario base vs. optimizado sobre 1 TB/día; matriz de equivalencias cloud; export Parquet opcional | `reportes/finops_escenarios.csv` |
| 9 | Cierre | 6 preguntas de discusión y referencias | — |

### Anomalías inyectadas a propósito

La limpieza solo tiene valor si los datos vienen sucios. El generador incluye:

| Anomalía | Proporción | Dónde se resuelve |
|---|---|---|
| Lecturas "calientes" (temp +18–36 °C, vibración ×1.8–3.1) | ~0,7 % | Silver: alertas de negocio |
| Temperaturas faltantes (`NaN`) | ~0,6 % | Silver: cuarentena (`temperatura_invalida`) |
| Temperaturas físicamente imposibles (−150 °C) | ~0,15 % | Silver: cuarentena (`temperatura_invalida`) |
| Retrasos extremos de ingesta (+45–240 min) | ~3 % | Observabilidad: p95 de latencia |
| Reenvíos duplicados (mismo `evento_id`) | 1 % | Silver: deduplicación |
| Jitter de ±25 s en timestamps | siempre | — |

Las validaciones de Silver cubren además **equipo inexistente**, **fecha ilegible**, **vibración fuera
de rango** y **potencia fuera de rango**. El generador actual no produce esos casos, así que esas reglas
existen pero no se disparan: sirven como ejemplo de controles preventivos y de la necesidad de
**probar las reglas con datos de prueba** antes de confiar en ellas.

---

## 5. Resultados de referencia

Cifras de la corrida validada. Sirven para que el docente compruebe que la ejecución del alumno es correcta.

| Métrica | Valor |
|---|---|
| Filas en Bronze | **181 800** |
| Duplicados rechazados | 1 800 |
| Filas inválidas → cuarentena | 1 361 (todas `temperatura_invalida`) |
| Filas válidas en Silver | **178 639** |
| Válidas sobre Bronze | 98,26 % |
| **Válidas sobre eventos únicos** | **99,24 %** |
| Alertas críticas | 1 331 |
| p95 de latencia de ingesta | 17,47 min |

> **Detalle útil para clase:** las 1 361 filas en cuarentena corresponden todas a `temperatura_invalida`
> (valores `NaN` o −150 °C), porque el generador solo inyecta fallas de temperatura. Las reglas de
> vibración (0–50 mm/s) y potencia (0–1000 kW) están implementadas pero **no se disparan** con estos datos.
> Vale la pena preguntar en clase: *¿cómo probarías que esas reglas funcionan antes de que fallen en producción?*

Tiempos por etapa (varían con la caché de disco; Silver es la más costosa):

| Etapa | Tiempo |
|---|---|
| Landing (copia + hash) | 0,04 s |
| Bronze | ~2,4 s |
| Silver | 5–15 s |
| Gold | ~0,6 s |

### SLO didácticos (sección 7)

| SLO | Objetivo | Resultado |
|---|---|---|
| Archivos recibidos | 100 % | ✅ 30/30 |
| Calidad | ≥ 98 % de eventos únicos válidos | ✅ 99,24 % |
| Frescura | p95 de latencia < 30 min | ✅ 17,47 min |

> La métrica de calidad se calcula **sobre eventos únicos**, no sobre Bronze: contar reenvíos
> como pérdida de calidad castigaría al pipeline por un problema de red. Esa distinción es,
> en sí misma, una lección de observabilidad.

### Simulación FinOps (sección 8)

Plataforma hipotética de **1 TB/día** con 30 días de retención:

| Categoría | Base (USD/mes) | Optimizado (USD/mes) | Ahorro |
|---|---|---|---|
| Ingesta | 36,00 | 36,00 | 0,00 |
| Transformación | 102,00 | 66,30 | 35,70 |
| Almacenamiento | 570,00 | 228,00 | 342,00 |
| Consultas | 100,00 | 45,00 | 55,00 |
| **Total** | **808,00** | **375,30** | **53,6 %** |

Costo por TB de entrada: **USD 26,93 → USD 12,51**.

> Los precios son **supuestos didácticos**, no cotizaciones ni tarifas oficiales de ningún
> proveedor. Lo que se enseña es la *estructura* del cálculo (TB ingeridos, TB-mes almacenados,
> TB escaneados), no los valores.

---

## 6. Alineación con las unidades del curso

| Unidad | Concepto | Dónde se trabaja |
|---|---|---|
| **I** — Contenedores y escalabilidad | Reproducibilidad, empaquetado, escalar por particiones y paralelismo | Secciones 0 y 2, y la discusión de escalamiento |
| **II** — Modelos de servicio, observabilidad e IaC | IaaS/PaaS/Serverless, métricas/logs, SLO, automatización | Sección 7 y [ARQUITECTURA_CLOUD.md](./ARQUITECTURA_CLOUD.md) §3 |
| **III** — Arquitecturas cloud nativas y FinOps | Patrón Medallion, resiliencia, costo por unidad de dato | Secciones 3–6 y 8 |

---

## 7. Guion sugerido (90 minutos)

El notebook corre en ~25 s, así que el tiempo de clase es para **discutir decisiones**, no para esperar.

| Min | Actividad |
|---|---|
| 0–10 | Contexto del caso y pregunta guía; mostrar el diagrama del pipeline (sección 0) |
| 10–25 | Secciones 1–3: fuentes, ingesta idempotente, por qué Landing y Bronze son capas distintas |
| 25–45 | Sección 4: **abrir `cuarentena.csv.gz`** y discutir cada motivo de rechazo. ¿Quién es el dueño de cada uno? |
| 45–60 | Secciones 5–6: del KPI al panel. ¿Qué decisión habilita cada gráfico? |
| 60–75 | Secciones 7–8: SLO y FinOps. ¿Qué cambia si el SLO de frescura baja de 24 h a 1 min? |
| 75–90 | Sección 9 + [ARQUITECTURA_CLOUD.md](./ARQUITECTURA_CLOUD.md): llevarlo a Azure/AWS/GCP |

### Preguntas de cierre (sección 9 del notebook)

1. ¿Por qué conservar Landing si Bronze ya contiene todas las filas?
2. ¿Qué diferencia hay entre *exactly-once en el resultado* y reintentos de entrega?
3. ¿Cómo se gestionan eventos que llegan con 2 horas de retraso en un tablero casi en tiempo real?
4. ¿Qué indicadores se pierden si descartamos datos inválidos sin cuarentena?
5. ¿Cuándo conviene PaaS o serverless en lugar de una flota de VMs/Kubernetes?
6. ¿Qué costo adicional introduce un SLA de frescura de 1 minuto frente a uno de 24 horas?

### Entregables sugeridos

| Entregable | Criterio de revisión |
|---|---|
| Notebook ejecutado | Corre completo sin intervención; cifras consistentes con §5 |
| Diagrama de arquitectura | 5 capas + flujo batch/streaming + controles transversales |
| Tabla de calidad | Qué se rechaza, por qué, cuánto pesa y quién lo corrige |
| Tabla de SLO | 3–4 SLO con métrica, objetivo, ventana y dueño |
| Modelo de costos | Supuestos explícitos + costo por unidad de dato |
| Sustentación (8 min) | Trade-offs defendidos con números del propio pipeline |

---

## 8. Solución de problemas

| Síntoma | Causa y solución |
|---|---|
| `RuntimeError: Landing no coincide con fuente` | Regeneraste `datos_fuente/` con un `data_lake/` anterior. **Es el control de integridad funcionando.** Borra `data_lake/` y vuelve a ejecutar |
| `OSError: Cannot save file into a non-existent directory: ...datos_fuente` | `generar_datos.py` no crea la carpeta. Ejecuta `mkdir datos_fuente` primero |
| `FileNotFoundError: catalogo_equipos.csv` | Faltan las fuentes. Ejecuta `python generar_datos.py` (creando la carpeta antes) |
| `ModuleNotFoundError: pandas` | El kernel de VS Code no es el del `.venv`. Selecciona el intérprete correcto |
| `KeyError` o `AttributeError` en la sección 4 | Celdas ejecutadas fuera de orden. Usa **Restart & Run All** |
| `PermissionError` al borrar `data_lake/` en Windows | Cierra el kernel (mantiene archivos abiertos) y reintenta |
| `Parquet omitido: instala pyarrow...` | Aviso informativo: la exportación Parquet es opcional |
| Los gráficos no aparecen | Verifica que `matplotlib` esté instalado y que el backend inline esté activo (por defecto en Jupyter) |

### Sobre el control de integridad de Landing

La sección 2 compara el SHA-256 del archivo de origen con el ya copiado en Landing y **falla**
si difieren. Es intencional: detecta modificaciones silenciosas de un lote ya procesado.

Consecuencia práctica: `pandas.to_csv(compression="gzip")` incrusta la hora de escritura en la
cabecera gzip, por lo que **regenerar las fuentes cambia el hash aunque los datos sean idénticos**.
Siempre que se regenere `datos_fuente/`, hay que vaciar `data_lake/`.

---

## 9. Qué demuestra y qué no

**Sí demuestra**

* Separación de capas Medallion y por qué cada una existe.
* Ingesta idempotente con verificación de integridad y bitácora.
* Calidad medible: cuarentena con motivo, no borrado silencioso.
* Métricas de pipeline separadas de métricas de negocio.
* Costo por unidad de dato y efecto de las palancas de optimización.

**No demuestra** (y conviene decirlo en clase)

* **Streaming real:** los archivos diarios simulan microingesta batch, no un broker de eventos.
* **Un pipeline cloud:** no se aprovisiona ningún servicio; la nube se explica en [ARQUITECTURA_CLOUD.md](./ARQUITECTURA_CLOUD.md) como alternativa de implementación.
* **Metrología:** los sensores son sintéticos; Silver es confiable *según las reglas del caso*, no calibrado.
* **Energía facturable:** `energia_kwh_estimada` supone intervalos nominales iguales; es una aproximación didáctica.
* **Precios cloud reales:** los USD de la sección 8 son supuestos, no cotizaciones.
* **Garantías de entrega:** la deduplicación resuelve el resultado, no el transporte.

---

## 10. Evolución a la nube

El laboratorio se queda en local a propósito: mismo razonamiento de arquitectura, sin cuentas ni cargos.
La propuesta completa está en [ARQUITECTURA_CLOUD.md](./ARQUITECTURA_CLOUD.md): arquitectura lógica de
producción, alternativas por proveedor (sin asumir equivalencias uno a uno), criterios IaaS/PaaS/Serverless,
controles esenciales y un ejemplo **opcional** de carga a S3 con `boto3` (requiere credenciales propias y
presupuesto configurado; nunca escribir claves en el notebook).

| Etapa | Local (este taller) | Azure | AWS | Google Cloud |
|---|---|---|---|---|
| Ingesta | Archivos diarios + Python | Event Hubs / Data Factory | Kinesis / Glue | Pub/Sub / Dataflow |
| Landing + Lake | Carpetas + CSV.gz | ADLS Gen2 | Amazon S3 | Cloud Storage |
| Transformación | pandas | Databricks / Fabric | Glue / EMR | Dataflow / Dataproc |
| SQL y consumo | SQLite | Synapse / Fabric Warehouse | Athena / Redshift | BigQuery |
| Observabilidad | JSON y KPIs | Azure Monitor | CloudWatch | Cloud Monitoring |
| Automatización | Notebook / tarea programada | Data Factory / Functions | Step Functions / Lambda | Workflows / Cloud Run |

En una plataforma lakehouse real, Silver y Gold suelen publicarse en **Parquet** particionado.
Aquí el notebook usa CSV comprimido para no exigir dependencias adicionales, y deja la
exportación Parquet como paso opcional.

---

## 11. Referencias

* Microsoft Learn — [Data lake / Medallion](https://learn.microsoft.com/en-us/azure/architecture/data-guide/scenarios/data-lake)
* Microsoft Azure Architecture Center — <https://learn.microsoft.com/azure/architecture/>
* AWS Well-Architected Framework — <https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html>
* Google Cloud Architecture Framework — <https://cloud.google.com/architecture/framework>
* FinOps Foundation — <https://www.finops.org/framework/>
* Docker — <https://docs.docker.com/get-started/docker-overview/>
* Kubernetes — <https://kubernetes.io/docs/home/>
* OpenTelemetry — <https://opentelemetry.io/docs/>
* Terraform — <https://developer.hashicorp.com/terraform>
