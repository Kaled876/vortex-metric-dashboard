import React, { useState, useCallback } from "react";
import Plot from 'react-plotly.js';

export default function DashboardReaccion() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [datos, setDatos] = useState(null);
    const [filtros, setFiltros] = useState({
        soloAciertos: true,
        minRt: 150,
        maxRt: 3000,
        aplicarIqr: true
    });

    const handleFileUpload = async (file) => {
        if (!file || !file.name.endsWith('.cab')) {
            setError('Archivo no es .cab :( Por favor intentalo de nuevo.');
            return;
        }

        setLoading(true);
        setError(null);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('solo_aciertos', filtros.soloAciertos);
        formData.append('min_rt', filtros.minRt);
        formData.append('max_rt', filtros.maxRt);
        formData.append('aplicar_iqr', filtros.aplicarIqr);

        try {
            const response = await fetch('http://localhost:8000/api/procesar-cab', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Error procesando el archivo');
            }

            const result = await response.json();
            setDatos(result);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // Preparando el Boxplot de Plotly para trazar
    const prepararDatosGrafico = useCallback(() => {
        if(!datos?.datos_grafico) return [];

        const gruposOrdenados = [
            'Niño (5-17)',
            'Adulto (18-64)',
            'Anciano (65+)'
        ];

        return gruposOrdenados
            .filter(grupo => datos.datos_grafico.some(d => d.grupo_edad === grupo))
            .map(grupo => {
                const puntosGrupo = datos.datos_grafico.filter(d => d.grupo_edad === grupo);
                return {
                    y: puntosGrupo.map(d => d.tiempo_reaccion_ms),
                    x: puntosGrupo.map(() => grupo),
                    type: 'box',
                    name: grupo,
                    boxpoints: 'outliers',
                    jitter: 0.3,
                    pointpos: -1.8,
                    marker: { size: 5 },
                    hoverinfo: 'y+name'
                };
            });
    }, [datos]);

    return (
        <div style={{maxWidth: '1100px', margin: '0 auto', padding: '24px', fontFamily: 'system-ui' }}>
            <h1>Panel Terapéutico - Tiempos de Reacción</h1>

            <div
                style={{
                    border: '2px dashed #2563eb',
                    borderRadius: '12px',
                    padding: '32px',
                    textAlign: 'center',
                    backgroundColor: '#1a1a1a',
                    cursor: 'pointer',
                    marginBottom: '24px'
                }}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                    e.preventDefault();
                    if (e.dataTransfer.files.length > 0) handleFileUpload(e.dataTransfer.files[0]);
                }}
                onClick={() => document.getElementById('file-input').click()}
            >
                <input
                    id="file-input"
                    type="file"
                    accept=".cab"
                    style={{ display: 'none' }}
                    onChange={(e) => e.target.files[0] && handleFileUpload(e.target.files)}
                />
                <p style={{ margin: 0, fontWeight: 600, color: '#1e40af' }}>
                    {loading ? 'Procesando archivo...' : 'Arrastar un .cab o haz clic para selecionarlo'}
                </p>
            </div>

            {error && (
                <div style={{ backgroundColor: '#fef2f2', color: '#991b1b', padding: '12px 16px', borderRadius: '8px', marginBottom: '16px' }}>
                    {error}
                </div>
            )}

            {datos && (
                <div>
                    <div style={{ backgroundColor: '#f8fafc', padding: '16px', borderRadius: '8px', marginBottom: '20px', border: '1px solid #e2e8f0' }}>
                        <span style={{ fontWeight: 600, marginRight: '16px' }}>
                            <span style={{ color: '#059669', fontSize: '14px' }}>
                                ({datos.registros_descratados})
                            </span>
                        </span>
                    </div>

                    <div style={{ background: '#ffffff', border: '1px soild #e2e8f0', borderRadius: '12px', padding: '16px', marginBottom: '24px' }}>
                        <h2>Distribución por Grupo de Edad (Boxplot)</h2>
                        <Plot
                            data={prepararDatosGrafico()}
                            layout={{
                                autosize: true,
                                yaxis: { title: 'Tiempo de Reacción (ms)', zeroline: false },
                                xaxis: { title: 'Grupo Etario' },
                                margin: { t: 30, b: 50, l: 60, r: 20 },
                                showlegend: false
                            }}
                            useResizeHandler={true}
                            style={{ width: '100%', height: '450px' }}
                            config={{ responsive: true, displayModeBar: true }}
                        />
                    </div>

                    <div style={{ background: '#ffffff', border: '1px soild #e2e8f0', borderRadius: '12px', padding: '20px' }}>
                        <h2>Estadísticas Descriptivas</h2>
                        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                            <thead>
                                <tr style={{ background: '#f1f5f9', borderBottom: '2px soild #cbd5e1' }}>
                                    <th style={{ padding: '10px'  }}>Grupo de Edad</th>
                                    <th style={{ padding: '10px'  }}>Pruebas (#)</th>
                                    <th style={{ padding: '10px'  }}>Media (ms)</th>
                                    <th style={{ padding: '10px'  }}>Mediana (ms)</th>
                                    <th style={{ padding: '10px'  }}>Desv. Est. (σ)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {datos.resumen_estadistico.map((row) => (
                                    <tr key={row.grupo_edad} style={{ borderBottom: '1px solid #e2e8f0' }}>
                                        <td style={{ padding: '10px', fontWeight: 600 }}>{row.grupo_edad}</td>
                                        <td style={{ padding: '10px' }}>{row.total_pruebas}</td>
                                        <td style={{ padding: '10px' }}>{row.promedio} ms</td>
                                        <td style={{ padding: '10px' }}>{row.mediana} ms</td>
                                        <td style={{ padding: '10px' }}>±{row.desviacion} ms</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}