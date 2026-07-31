from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from cabarchive import CabArchive
import pandas as pd
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def obtener_grupo_etario(edad: int) -> str:
    if edad < 17:
        return "Niño (5-17)"
    elif edad < 65:
        return "Adulto (18-64)"
    return "Anciano (65+)"

@app.post("/api/procesar-cab")
async def procesar_cab(
    file: UploadFile = File(...),
    solo_aciertos: bool = Form(True),
    min_rt: float = Form(150.0),
    max_rt: float = Form(3000.0),
    aplicar_iqr: bool = Form(True)
):
    if not file.filename.endswith('.cab'):
        raise HTTPException(status_code=400, detail="Archivo debe tener extensión .cab")

    contents = await file.read()

    try:
        archive = CabArchive(contents)

        csv_filename = next((name for name in archive.keys() if name.endswith('.csv')), None)
        if not csv_filename:
            raise HTTPException(status_code=400, detail="No hay archivo CSV aquí :(")

        csv_bytes = archive.get(csv_filename).buf
        df_raw = pd.read_csv(io.BytesIO(csv_bytes))

        registros_totales = len(df_raw)

        if solo_aciertos and 'acierto' in df_raw.columns:
            df = df_raw[df_raw['acierto'] == True].copy()
        else:
            df = df_raw.copy()

        df = df[(df['tiempo_reaccion_ms'] >= min_rt) & (df['tiempo_reaccion_ms'] <= max_rt)].copy()

        df['grupo_edad'] = df['edad'].apply(obtener_grupo_etario)

        if aplicar_iqr and len(df) > 0:
            grupos_limpios = []
            for _, group_df in df.groupby('grupo_edad'):
                q1 = group_df['tiempo_reaccion_ms'].quantile(0.25)
                q3 = group_df['tiempo_reaccion_ms'].quantile(0.75)
                iqr = q3 - q1

                limite_inferior = q1 - (1.5 * iqr)
                limte_superior = q3 - (1.5 * iqr)

                filtrado = group_df[
                    (group_df['tiempo_reaccion_ms'] >= limite_inferior) &
                    (group_df['tiempo_reaccion_ms'] <= limte_superior)
                ]
                grupos_limpios.append(filtrado)

            df = pd.concat(grupos_limpios).reset_index(drop=True)

        registros_validos = len(df)

        resumen = df.groupby('grupo_edad')['tiempo_reaccion_ms'].agg(
            total_pruebas='count',
            promedio='mean',
            mediana='median',
            desviacion='std'
        ).round(2).fillna(0).reset_index()

        return{
            "archivo": csv_filename,
            "total_registros_brutos": registros_totales,
            "total_registros_validos": registros_validos,
            "registros_descartados": registros_totales - registros_validos,
            "resumen_estadistico": resumen.to_dict(orient="records"),
            "datos_grafico": df[['user_id', 'edad', 'grupo_edad', 'tiempo_reaccion_ms']].to_dict(orient="records")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {str(e)}")