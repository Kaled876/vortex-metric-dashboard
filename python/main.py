from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

@app.post("/api/procesar-csv")
async def procesar_csv(
    file: UploadFile = File(...),
    solo_aciertos: bool = Form(True),
    min_rt: float = Form(150.0),
    max_rt: float = Form(3000.0),
    aplicar_iqr: bool = Form(True)
):
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Archivo debe tener extensión .csv")

    contents = await file.read()

    try:
        df_raw = pd.read_csv(io.BytesIO(contents))
        registros_totales = len(df_raw)

        if registros_totales == 0:
            raise HTTPException(status_code=400, detail="El CSV enviado está vaico.")

        if solo_aciertos and 'acierto' in df_raw.columns:
            df = df_raw[df_raw['acierto'] == True].copy()
        else:
            df = df_raw.copy()

        if 'tiempo_reaccion_ms' in df.columns:
            df = df[(df['tiempo_reaccion_ms'] >= min_rt) & (df['tiempo_reaccion_ms'] <= max_rt)].copy()

        if 'edad' in df.columns:
            df['grupo_edad'] = df['edad'].apply(obtener_grupo_etario)

        if aplicar_iqr and len(df) > 0 and 'tiempo_reaccion_ms' in df.columns:
            grupos_limpios = []
            for _, group_df in df.groupby('grupo_edad'):
                q1 = group_df['tiempo_reaccion_ms'].quantile(0.25)
                q3 = group_df['tiempo_reaccion_ms'].quantile(0.75)
                iqr = q3 - q1

                limite_inferior = q1 - (1.5 * iqr)
                limte_superior = q3 + (1.5 * iqr)

                filtrado = group_df[
                    (group_df['tiempo_reaccion_ms'] >= limite_inferior) &
                    (group_df['tiempo_reaccion_ms'] <= limte_superior)
                ]
                grupos_limpios.append(filtrado)

            df = pd.concat(grupos_limpios).reset_index(drop=True)

        registros_validos = len(df)

        resumen = []
        if 'grupo_edad' in df.columns and 'tiempo_reaccion_ms' in df.columns and len(df) > 0:
            resumen_df = df.groupby('grupo_edad')['tiempo_reaccion_ms'].agg(
                total_pruebas='count',
                promedio='mean',
                mediana='median',
                desviacion='std'
            ).round(2).fillna(0).reset_index()
            resumen = resumen_df.to_dict(orient="records")

        cols_presentes = [col for col in ['user_id', 'edad', 'grupo_edad', 'tiempo_reaccion_ms'] if col in df.columns]
        datos_grafico = df[cols_presentes].to_dict(orient="records") if len(df) > 0 else []

        return{
            "archivo": file.filename,
            "total_registros_brutos": registros_totales,
            "total_registros_validos": registros_validos,
            "registros_descartados": registros_totales - registros_validos,
            "resumen_estadistico": resumen,
            "datos_grafico": datos_grafico
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {str(e)}")