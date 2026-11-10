from pathlib import Path
from datetime import datetime, timezone
from time import perf_counter
import hashlib, json, shutil, sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display

BASE = Path.cwd()
SRC = BASE / "datos_fuente"
SEED = 20261109
REGENERAR = True  # Cambiar a True para volver a generar los 180 000 eventos fuente

T0 = perf_counter()
rng = np.random.default_rng(SEED)
tipos = ["Bomba", "Faja", "Chancadora", "Ventilador", "Camion", "Compresor"]
zonas = ["Planta Norte", "Planta Sur", "Mina Este", "Mina Oeste", "Servicios", "Patio"]
parametros = {"Bomba":(63,3.0,75), "Faja":(52,2.5,42), "Chancadora":(77,5.0,190),
              "Ventilador":(48,2.2,35), "Camion":(82,4.2,150), "Compresor":(72,4.1,115)}
catalogo = pd.DataFrame([
  {"equipo_id":f"EQ-{i+1:03d}","tipo_equipo":tipos[i//8],"zona":zonas[i%6],
   "temperatura_limite_c":parametros[tipos[i//8]][0]+15,
   "vibracion_limite_mms":parametros[tipos[i//8]][1]*1.75,
   "criticidad":("Alta" if tipos[i//8] in ["Chancadora","Compresor"] else "Media")}
  for i in range(48)])
catalogo.to_csv(SRC / "catalogo_equipos.csv", index=False)

mantenimiento = pd.DataFrame([{
 "equipo_id":f"EQ-{i+1:03d}",
 "fecha_mantenimiento":(pd.Timestamp('2026-10-01')+pd.Timedelta(days=int((i*7+5)%30))).strftime('%Y-%m-%d'),
 "tipo_mantenimiento":("Correctivo" if i%5==0 else "Preventivo")}
 for i in range(48)])
mantenimiento.to_csv(SRC/"mantenimientos.csv", index=False)

archivos = list(SRC.glob("iot_*.csv.gz"))
if REGENERAR or len(archivos) != 30:
    for f in archivos: f.unlink()
    registros_por_dia = 48*125  # exactamente 6 000 lecturas por día
    for d in range(30):
        n = registros_por_dia
        eidx = np.repeat(np.arange(48), 125)
        tipo = np.asarray(tipos)[eidx//8]
        # Sensor ~cada 11.5 minutos; jitter de segundos
        segundos = np.tile(np.arange(125),48)*(86400/125) + rng.integers(-25,26,size=n)
        evento = pd.Timestamp('2026-10-01',tz='UTC') + pd.Timedelta(days=d) + pd.to_timedelta(segundos,unit='s')
        temp_base = np.array([parametros[x][0] for x in tipo]); vib_base = np.array([parametros[x][1] for x in tipo]); pot_base = np.array([parametros[x][2] for x in tipo])
        temp = temp_base + 4*np.sin(2*np.pi*np.tile(np.arange(125),48)/125) + rng.normal(0,2.8,n)
        vib = np.maximum(.1,vib_base + rng.normal(0,.55,n))
        potencia = np.maximum(.1,pot_base * rng.normal(1,.075,n))
        # ~0.7% lecturas calientes y vibración anómala
        faults = rng.random(n)<.007
        temp[faults] += rng.uniform(18,36,faults.sum()); vib[faults] *= rng.uniform(1.8,3.1,faults.sum())
        # ~0.6% temperaturas faltantes; ~0.15% temperaturas físicamente imposibles
        temp[rng.random(n)<.006] = np.nan
        temp[rng.random(n)<.0015] = -150
        retraso = rng.exponential(4.5,size=n)
        # porcentaje retrasos extremos sin depender de longitudes variables
        tarde = rng.random(n)<.03
        retraso[tarde] += rng.uniform(45,240,tarde.sum())
        ingesta = evento + pd.to_timedelta(retraso,unit='m')
        evento_idx = np.arange(d*n,(d+1)*n)
        df = pd.DataFrame({"evento_id":[f"EV-{x:09d}" for x in evento_idx],
           "equipo_id":np.array(catalogo['equipo_id'])[eidx],
           "fecha_evento":evento.strftime('%Y-%m-%dT%H:%M:%SZ'),
           "fecha_ingesta":ingesta.strftime('%Y-%m-%dT%H:%M:%SZ'),
           "temperatura_c":np.round(temp,2),"vibracion_mms":np.round(vib,3),
           "potencia_kw":np.round(potencia,2),"origen":"iot_gateway_simulado"})
        # 1% duplicados con el mismo evento_id (simulación de reenvíos)
        repetidos = df.sample(frac=.01,random_state=SEED+d)
        df = pd.concat([df,repetidos],ignore_index=True).sample(frac=1,random_state=SEED+d)
        df.to_csv(SRC/f"iot_2026-10-{d+1:02d}.csv.gz",index=False,compression='gzip')
print("Archivos IoT:",len(list(SRC.glob('iot_*.csv.gz'))),"| Registros base:",48*125*30,"| segundos:",round(perf_counter()-T0,2))