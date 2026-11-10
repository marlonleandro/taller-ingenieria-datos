# Propuesta de evolución a Cloud

## 1. Arquitectura lógica de producción

```text
Gateways IoT ──► Broker de eventos ──────► Landing raw (object storage)
                        │                          │
                        ▼                          ▼
               validación técnica               Bronze
                        │                          ▼
                        └─────────────► Jobs ETL/ELT → Silver → Gold
                                                           │
                                                           ▼
                                            SQL analítico / BI / alertas

Transversal: IAM + cifrado + catálogo/linaje + IaC + monitoreo + presupuestos FinOps
```

**Batch y streaming pueden coexistir.** El sistema de eventos gestiona datos recientes, mientras un batch regular reconcilia datos tardíos. El almacenamiento object storage permite desacoplar persistencia y motores de procesamiento; no evita por sí solo errores de calidad ni garantiza exactamente una ejecución.

## 2. Alternativas por proveedor (no equivalencias perfectas)

| Capa | Azure | AWS | Google Cloud |
|---|---|---|---|
| Eventos | Event Hubs | Kinesis Data Streams | Pub/Sub |
| Orquestación / ingesta batch | Data Factory / Fabric Data Factory | Glue / Step Functions | Workflows / Cloud Composer |
| Lago de datos | ADLS Gen2 | S3 | Cloud Storage |
| Procesamiento | Databricks / Fabric Spark | Glue / EMR | Dataflow / Dataproc |
| SQL analítico | Fabric Warehouse / Synapse | Athena / Redshift | BigQuery |
| Observabilidad | Azure Monitor | CloudWatch | Cloud Monitoring |
| IaC | Terraform / Bicep | Terraform / CloudFormation | Terraform / Infra Manager |

**Advertencia:** Azure Fabric, AWS Glue, BigQuery, etc. tienen modelos de costo, IAM y operación diferentes. No basta reemplazar nombres; hay que diseñar el producto de datos, acceso, linaje, SLA y presupuesto.

## 3. Pregunta IaaS / PaaS / Serverless

- **IaaS:** VMs para procesos heredados o dependencias muy particulares; más control, más parcheo/operación.
- **PaaS/servicios gestionados:** menor carga operativa para ingesta, procesamiento o SQL; menos control de la plataforma y restricciones del servicio.
- **Serverless/event-driven:** ideal para disparar ingestas ligeras o microjobs irregulares; evaluar límites de ejecución, picos y costo por invocación.
- **Kubernetes:** indicado para workloads empaquetados que requieren orquestación; no es un prerrequisito universal del lakehouse.

## 4. Controles esenciales en una propuesta empresarial

- Datos: esquemas versionados, contratos, deduplicación e idempotencia, replay, dead-letter/quarantine.
- Seguridad: identidad, claves rotadas, redes privadas si corresponde, cifrado y clasificación.
- Operación: disponibilidad de fuentes, frescura, retrasos, tasa de errores, costos y alertas accionables.
- FinOps: etiquetas por dominio/producto, showback, retención, particionado, formato columnar y optimización de cómputo.

## 5. Extensión opcional real sobre AWS S3 (requiere cuenta y permisos)

Esta extensión **NO** se ejecuta por defecto. Ejemplo para el docente que ya tenga credenciales configuradas externamente (perfil/rol):

```python
import boto3
from pathlib import Path
bucket = "REEMPLAZAR_POR_BUCKET_PROPIO"
s3 = boto3.client("s3")
for path in Path("data_lake/landing").glob("iot_*.csv.gz"):
    s3.upload_file(str(path), bucket, f"andesdata/landing/{path.name}")
```

Use identidad/rol de mínimo privilegio; **nunca** escribir claves en el notebook. Configurar presupuesto antes de usar recursos cloud. El ejemplo sólo sube archivos; **no** crea un pipeline cloud ni configura seguridad del bucket.

## 6. Fuentes oficiales recomendadas

- Microsoft Learn, Data Lake architecture: https://learn.microsoft.com/en-us/azure/architecture/data-guide/scenarios/data-lake
- Docker docs: https://docs.docker.com/get-started/docker-overview/
- Kubernetes docs: https://kubernetes.io/docs/home/
- OpenTelemetry docs: https://opentelemetry.io/docs/
- FinOps Framework: https://www.finops.org/framework/
- AWS Well-Architected: https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html
