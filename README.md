# SpVAR Espacial · Homicidios × Luces Nocturnas (Colombia)

Taller de econometría espacial. Estudia la relación dinámica entre la **tasa de homicidios** y las **luces nocturnas (VIIRS)** en **33 departamentos de Colombia, 2014-2024**, con un modelo SpVAR (vector autorregresivo espacial). Incluye una interfaz interactiva en Streamlit.

> Resultado **exploratorio**. No permite afirmar relaciones causales.

## Fuentes de datos

| Dato | Fuente |
|------|--------|
| Homicidios | MinDefensa, dataset `m8fd-ahd9` en datos.gov.co |
| Población | DANE, proyecciones departamentales (2005-2017 y 2018-2050) |
| PIB departamental | DANE, cuentas nacionales departamentales |
| Cartografía | DANE, Marco Geoestadístico Nacional (MGN 2024) |
| Luces nocturnas | VIIRS vía Google Earth Engine |

## Flujo del análisis

1. **Datos**: descarga de homicidios (API Socrata), población DANE y MGN; agregación departamento-año y cálculo de la tasa por 100.000 hab.
2. **Luces nocturnas**: extracción de la media por departamento y año con Earth Engine.
3. **Matrices de pesos espaciales (W)**: Queen, Rook, kNN (k=3, 4, 5) y distancia inversa; diagnóstico con Moran's I.
4. **Transformaciones**: logaritmos y log-diferencias, con tratamiento explícito de ceros.
5. **Rezagos espaciales y temporales** de ambas variables.
6. **Estimación**: SpVAR por ecuación con efectos de año; comparación MCO, SAR, SEM, SAC y SDM.
7. **Robustez**: exclusión de departamentos pequeños o problemáticos, distintas W, saltos de luces en 2017 y 2023.
8. **Modelo final**: luces = SEM + kNN3; tasa = MCO.
9. **Análisis dinámico**: estabilidad, IRF, FEVD y causalidad espacial de Granger.
10. **Resultados**: mapas coropléticos, LISA y auditoría PASA/FALLA.
11. **Interfaz**: versión Gradio y versión final en Streamlit.

## Hallazgo principal

Cuando aumenta el crecimiento de la tasa de homicidios en los departamentos vecinos, tiende a disminuir el crecimiento de las luces nocturnas. El resultado varía según la matriz de vecinos, los departamentos pequeños y el periodo, por lo que **no se considera robusto**.

## Limitaciones

- Periodo temporal corto (poca potencia estadística).
- Algunas observaciones fueron sustituidas (ceros o valores no positivos).
- Saltos importantes en las luces en 2017 y 2023.
- El modelo SAC no pudo estimarse.
- No se fijó semilla global (las permutaciones de Moran usan 999).

## Estructura de la interfaz (Streamlit)

1. **Explorador territorial**: indicadores y evolución por departamento y año.
2. **Mapas de Colombia**: coropletas interactivas con Folium.
3. **Simulación**: impacto aproximado de cambios en la tasa o en las luces.
4. **Resultados del modelo**: modelos seleccionados, hallazgo y limitaciones.

## Cómo ejecutar

### En Google Colab
Ejecute el cuaderno en orden. Necesita:
- Un proyecto de Google Earth Engine (`ee.Initialize(project='su-proyecto')`).
- El shapefile del MGN si la descarga automática falla (`MGN2024_DPTO_POLITICO.zip`).

### Localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

**Importante:** la parte de Streamlit del script usa objetos creados antes en el cuaderno (`df_k3`, `gdf`, `panel`, `agg`). Para ejecutarla fuera de Colab, guarde esos datos en archivos (por ejemplo `panel_spvar_listo.csv` y `departamentos_33.gpkg`) y cárguelos al inicio de `app.py` en lugar de depender de las variables del cuaderno.

## Archivos generados por el cuaderno

- `tabla_dept_anio_registros.csv`
- `panel_homicidios_tasas.csv`
- `panel_homicidios_luces.csv`
- `panel_spvar_listo.csv`
- `departamentos_33.gpkg`
- `salida_bloque5.zip` (mapas, tablas y texto interpretativo)
