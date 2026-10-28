## Proyecto 2 — Fase 1.1: Datos nuevos desde cero

### Objetivo

Reconstruir el pipeline de la Red Metropolitana de Transporte a partir de nueve fuentes de datos, utilizando ingestas Batch, Streaming con Apache Kafka y CDC, almacenamiento Bronze en Parquet, PostgreSQL para Staging, Prefect para orquestación y dbt para las transformaciones Silver y Gold.

### Requisitos previos

- Python con las dependencias del proyecto instaladas y el entorno virtual activado.
- Docker Desktop y Docker Compose.
- Los nueve archivos originales en `datos_red/`.
- El archivo `.env` configurado para los servicios exclusivos del Proyecto 2.
- El perfil dbt disponible en `dbt_red_metropolitana/config/profiles.yml`.

### Ejecución completa desde cero

Desde la raíz del repositorio, ejecutar:

```powershell
python .\scripts\orquestacion\ejecutar_desde_cero.py --desde-cero --confirmar-borrado-p2
```

El programa valida la configuración Docker Compose y los recursos asociados al Proyecto 2 antes de reinicializarlos. Solicita escribir `REINICIAR PROYECTO 2` como confirmación adicional.

**Advertencia:** esta operación elimina los datos generados en Bronze y los volúmenes Kafka/PostgreSQL del Proyecto 2. No elimina los nueve archivos originales ni debe utilizarse con recursos compartidos de otros proyectos.

Para ejecutar el pipeline reutilizando las cargas existentes:

```powershell
python .\scripts\orquestacion\ejecutar_desde_cero.py
```

### Reconciliación de datos

| Fuente | Registros esperados | Registros cargados | Diferencia |
|---|---:|---:|---:|
| TM estaciones | 104 | 104 | 0 |
| TU paradas | 328 | 328 | 0 |
| MR estaciones | 22 | 22 | 0 |
| AM estaciones | 14 | 14 | 0 |
| Transmetro | 713,786 | 713,786 | 0 |
| Transurbano | 1,635,788 | 1,635,788 | 0 |
| MetroRiel | 590,844 | 590,844 | 0 |
| Aerómetro | 387,053 | 387,053 | 0 |
| CDC padrón | 77,636 | 77,636 | 0 |
| **Total** | **3,405,575** | **3,405,575** | **0** |

### Tiempos de ejecución

En la reconstrucción desde estado limpio, se observaron los siguientes tiempos:

| Etapa | Segundos |
|---|---:|
| Ingesta Batch | 4.03 |
| Ingesta CDC Bronze | 0.37 |
| Publicación Transmetro | 1.50 |
| Consumo Transmetro | 7.52 |
| Publicación Aerómetro | 0.96 |
| Consumo Aerómetro | 3.98 |
| Prefect: Staging, CDC y modelos dbt | 240.27 |

Los tiempos completos del coordinador se encuentran en `docs/reportes_fase1/tiempos_etapas.csv`. Las duraciones internas de Prefect se registran por separado y no deben sumarse nuevamente a su duración total.

### Validación final

- Nueve fuentes reconciliadas sin diferencias.
- 3,405,575 registros preservados en Bronze.
- Integridad del contenido Streaming verificada.
- 25 modelos dbt ejecutados satisfactoriamente.
- 89 pruebas dbt aprobadas.
- Aplicación del CDC y generación de las capas Staging, Silver y Gold completadas.

### Evidencias

- `docs/reportes_fase1/reconciliacion_bronze.csv`
- `docs/reportes_fase1/reconciliacion_bronze.json`
- `docs/reportes_fase1/tiempos_etapas.csv`
- `docs/metricas_prefect/`
- `docs/evidencias/fase1/`

**Resultado:** ejecución integral satisfactoria desde el estado limpio de los datos generados del Proyecto 2, con las dependencias y fuentes originales previamente preparadas.