import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Tendencias de streaming", page_icon="🎬", layout="wide")

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
RUTA_CSV = Path(__file__).parent / "streaming_content_trends.csv"


@st.cache_data
def cargar(origen):
    return pd.read_csv(origen)


@st.cache_data
def limpiar(df_crudo):
    df = df_crudo.copy()
    reporte = {
        "registros_iniciales": len(df),
        "duplicados": int(df.duplicated(subset="id").sum()),
        "nulos_antes": df.isna().sum(),
    }
    df = df.drop_duplicates(subset="id")
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df["mes"] = df["release_date"].dt.month
    df["tipo"] = df["media_type"].map({"movie": "Película", "tv": "Serie"})
    df["genres"] = df["genres"].fillna("Sin género")
    df["origin_country"] = df["origin_country"].fillna("Desconocido")
    df["overview"] = df["overview"].fillna("Sin descripción")
    df = df.dropna(subset=["release_date"])
    df["release_year"] = df["release_year"].astype(int)
    reporte["nulos_despues"] = df.isna().sum()
    reporte["registros_finales"] = len(df)
    return df, reporte


def dividir_generos(df):
    return (
        df[df["genres"] != "Sin género"]
        .assign(genero=lambda d: d["genres"].str.split(", "))
        .explode("genero")
    )


st.title("🎬 Tendencias de contenido en streaming")
st.caption("Limpieza de datos y visualización con Matplotlib y Seaborn, presentadas con Streamlit.")

if RUTA_CSV.exists():
    df_crudo = cargar(RUTA_CSV)
else:
    archivo = st.file_uploader("No encontré streaming_content_trends.csv junto a app.py. Súbelo aquí:", type="csv")
    if archivo is None:
        st.stop()
    df_crudo = cargar(archivo)

df_limpio, reporte = limpiar(df_crudo)

st.sidebar.header("Filtros")
tipos = st.sidebar.multiselect("Tipo de contenido", ["Película", "Serie"], default=["Película", "Serie"])
categorias = st.sidebar.multiselect(
    "Categoría de búsqueda",
    sorted(df_limpio["search_category"].unique()),
    default=sorted(df_limpio["search_category"].unique()),
)
anio_min, anio_max = int(df_limpio["release_year"].min()), int(df_limpio["release_year"].max())
rango_anios = st.sidebar.slider("Año de estreno", anio_min, anio_max, (anio_min, anio_max))
min_votos = st.sidebar.slider("Mínimo de votos para rankings de calificación", 0, 5000, 1000, step=50)

df = df_limpio[
    df_limpio["tipo"].isin(tipos)
    & df_limpio["search_category"].isin(categorias)
    & df_limpio["release_year"].between(*rango_anios)
]

if df.empty:
    st.warning("Con estos filtros no quedan registros. Amplía la selección en la barra lateral.")
    st.stop()

generos = dividir_generos(df)
confiables = df[df["vote_count"] >= min_votos]

tab_datos, tab_limpieza, tab_mpl, tab_sns, tab_conclu = st.tabs(
    ["📂 Datos", "🧹 Limpieza", "📊 Matplotlib", "🎨 Seaborn", "📝 Conclusiones"]
)

with tab_datos:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Títulos (con filtros)", len(df))
    c2.metric("Películas", int((df["tipo"] == "Película").sum()))
    c3.metric("Series", int((df["tipo"] == "Serie").sum()))
    c4.metric("Calificación promedio", f"{df['vote_average'].mean():.2f}")
    st.subheader("Vista previa")
    st.dataframe(df.drop(columns=["overview"]).head(50))
    st.subheader("Estadísticas descriptivas")
    st.dataframe(df[["popularity", "vote_average", "vote_count"]].describe().round(2))

with tab_limpieza:
    st.subheader("Resumen del preprocesamiento")
    c1, c2, c3 = st.columns(3)
    c1.metric("Registros iniciales", reporte["registros_iniciales"])
    c2.metric("Duplicados eliminados", reporte["duplicados"])
    c3.metric("Registros finales", reporte["registros_finales"])

    st.subheader("Valores nulos por columna")
    nulos = pd.DataFrame(
        {"Antes": reporte["nulos_antes"], "Después": reporte["nulos_despues"].reindex(reporte["nulos_antes"].index)}
    )
    st.dataframe(nulos)

    st.subheader("Pasos aplicados")
    st.markdown(
        """
1. Se eliminaron registros duplicados usando el `id` del título.
2. `release_date` se convirtió a formato fecha y se descartaron los registros sin fecha; de ahí se obtuvo el mes de estreno.
3. `release_year` se convirtió a entero.
4. Los nulos de `genres`, `origin_country` y `overview` se rellenaron con una etiqueta descriptiva.
5. Se creó la columna `tipo` (Película o Serie) a partir de `media_type`.
6. Para rankings de calificación se filtran títulos con un mínimo de votos (ajustable en la barra lateral), porque los que tienen 1 o 2 votos pueden tener calificaciones de 0 o 10 que distorsionan el ranking.
"""
    )

    st.subheader("Títulos con pocos votos (antes del filtro)")
    pocos = df_limpio[df_limpio["vote_count"] < 10][["title", "vote_average", "vote_count"]].sort_values("vote_count")
    st.write(f"Hay {len(pocos)} títulos con menos de 10 votos.")
    st.dataframe(pocos.head(15))

with tab_mpl:
    st.header("Gráficos con Matplotlib")

    col1, col2 = st.columns(2)

    with col1:
        top_generos = generos["genero"].value_counts().head(8)
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.bar(top_generos.index, top_generos.values, color="steelblue")
        ax.set_title("Barras: géneros más frecuentes")
        ax.set_xlabel("Género")
        ax.set_ylabel("Cantidad de títulos")
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        fig.tight_layout()
        st.pyplot(fig)

        por_tipo = df["tipo"].value_counts()
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.pie(por_tipo.values, labels=por_tipo.index, autopct="%1.1f%%", colors=["#e07a5f", "#3d405b"][: len(por_tipo)])
        ax.set_title("Pastel: películas vs series")
        st.pyplot(fig)

        datos_scatter = df[df["vote_count"] > 0]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.scatter(datos_scatter["vote_count"], datos_scatter["vote_average"], alpha=0.4, s=15)
        ax.set_xscale("log")
        ax.set_title("Dispersión: votos vs calificación")
        ax.set_xlabel("Número de votos (escala log)")
        ax.set_ylabel("Calificación promedio")
        fig.tight_layout()
        st.pyplot(fig)

        estrenos_mes = df[df["release_year"] == 2026].groupby("mes").size().reindex(range(1, 13), fill_value=0)
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.fill_between(estrenos_mes.index, estrenos_mes.values, color="skyblue", alpha=0.5)
        ax.plot(estrenos_mes.index, estrenos_mes.values, marker="o", color="blue")
        ax.set_title("Áreas: estrenos por mes (2026)")
        ax.set_xlabel("Mes")
        ax.set_ylabel("Cantidad de títulos")
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(MESES)
        fig.tight_layout()
        st.pyplot(fig)

    with col2:
        top10 = (
            confiables.sort_values(["vote_average", "vote_count"], ascending=False)
            .drop_duplicates("title")
            .head(10)
            .sort_values("vote_average")
        )
        fig, ax = plt.subplots(figsize=(7, 4.5))
        if top10.empty:
            ax.text(0.5, 0.5, "Sin títulos con ese mínimo de votos", ha="center", va="center")
            ax.axis("off")
        else:
            ax.barh(top10["title"], top10["vote_average"], color="seagreen")
            ax.set_xlim(max(top10["vote_average"].min() - 0.3, 0), 10)
            ax.set_xlabel("Calificación promedio")
        ax.set_title(f"Barras horizontales: top 10 mejor calificados (≥{min_votos} votos)")
        fig.tight_layout()
        st.pyplot(fig)

        pop_mes = df[df["release_year"] == 2026].groupby("mes")["popularity"].mean().reindex(range(1, 13))
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.plot(pop_mes.index, pop_mes.values, marker="o", color="darkorange")
        ax.set_title("Líneas: popularidad promedio por mes de estreno (2026)")
        ax.set_xlabel("Mes")
        ax.set_ylabel("Popularidad promedio")
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(MESES)
        fig.tight_layout()
        st.pyplot(fig)

        califs = df[df["vote_count"] >= 100]["vote_average"]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.hist(califs, bins=15, edgecolor="black", color="mediumpurple")
        ax.set_title("Histograma: distribución de calificaciones (≥100 votos)")
        ax.set_xlabel("Calificación promedio")
        ax.set_ylabel("Frecuencia")
        fig.tight_layout()
        st.pyplot(fig)

        orden = ["popular", "top_rated", "trending"]
        presentes = [c for c in orden if c in df["search_category"].unique()]
        grupos = [df[df["search_category"] == c]["vote_average"] for c in presentes]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.boxplot(grupos, tick_labels=presentes)
        ax.set_title("Boxplot: calificación por categoría de búsqueda")
        ax.set_ylabel("Calificación promedio")
        fig.tight_layout()
        st.pyplot(fig)

    st.subheader("Radar: porcentaje de títulos por género")
    st.caption("Solo géneros que existen tanto en películas como en series, para que la comparación sea justa.")
    top6 = ["Drama", "Comedy", "Animation", "Crime", "Mystery", "Family"]
    conteo = generos[generos["genero"].isin(top6)].groupby(["tipo", "genero"]).size().unstack(fill_value=0)
    conteo = conteo.reindex(columns=top6, fill_value=0)
    totales = df["tipo"].value_counts()
    share = conteo.div(totales.reindex(conteo.index), axis=0) * 100
    angulos = np.linspace(0, 2 * np.pi, len(top6) + 1)
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, polar=True)
    for tipo, color in [("Película", "#e07a5f"), ("Serie", "#3d405b")]:
        if tipo in share.index:
            vals = np.concatenate((share.loc[tipo].values, [share.loc[tipo].values[0]]))
            ax.plot(angulos, vals, "o-", linewidth=2, label=tipo, color=color)
            ax.fill(angulos, vals, alpha=0.2, color=color)
    ax.set_thetagrids(angulos[:-1] * 180 / np.pi, top6)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))
    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        st.pyplot(fig)

with tab_sns:
    st.header("Gráficos con Seaborn")
    sns.set_theme(style="whitegrid")

    col1, col2 = st.columns(2)

    with col1:
        peliculas_pop = df[df["media_type"] == "movie"].nlargest(100, "popularity")
        fig, ax = plt.subplots(figsize=(7, 4.5))
        if peliculas_pop.empty:
            ax.text(0.5, 0.5, "Sin películas con estos filtros", ha="center", va="center")
            ax.axis("off")
        else:
            sns.countplot(x=peliculas_pop["mes"].astype(int), order=range(1, 13), ax=ax, color="#e07a5f")
            ax.set_xticks(range(12))
            ax.set_xticklabels(MESES)
        ax.set_title("Mes de estreno de las 100 películas más populares")
        ax.set_xlabel("Mes")
        ax.set_ylabel("Cantidad de películas")
        fig.tight_layout()
        st.pyplot(fig)

        top10_peliculas = (
            confiables[confiables["media_type"] == "movie"]
            .sort_values(["vote_average", "vote_count"], ascending=False)
            .drop_duplicates("title")
            .head(10)
        )
        fig, ax = plt.subplots(figsize=(7, 4.5))
        if top10_peliculas.empty:
            ax.text(0.5, 0.5, "Sin películas con ese mínimo de votos", ha="center", va="center")
            ax.axis("off")
        else:
            sns.barplot(data=top10_peliculas, y="title", x="vote_average", ax=ax, hue="title", palette="mako", legend=False)
            ax.set_xlim(max(top10_peliculas["vote_average"].min() - 0.3, 0), 10)
            ax.set_xlabel("Calificación promedio")
            ax.set_ylabel("")
        ax.set_title(f"Top 10 películas mejor calificadas (≥{min_votos} votos)")
        fig.tight_layout()
        st.pyplot(fig)

    with col2:
        gen_stats = (
            generos.groupby("genero")
            .agg(n=("id", "count"), popularidad=("popularity", "mean"))
            .query("n >= 20")
            .sort_values("popularidad", ascending=False)
            .head(10)
            .reset_index()
        )
        fig, ax = plt.subplots(figsize=(7, 4.5))
        if gen_stats.empty:
            ax.text(0.5, 0.5, "Ningún género con 20 o más títulos", ha="center", va="center")
            ax.axis("off")
        else:
            sns.barplot(data=gen_stats, y="genero", x="popularidad", ax=ax, hue="genero", palette="viridis", legend=False)
            ax.set_xlabel("Popularidad promedio")
            ax.set_ylabel("")
        ax.set_title("Géneros más populares (mínimo 20 títulos)")
        fig.tight_layout()
        st.pyplot(fig)

        fig, ax = plt.subplots(figsize=(7, 4.5))
        sns.histplot(df[df["vote_count"] >= 100]["vote_average"], bins=15, kde=True, ax=ax, color="skyblue")
        ax.set_title("Distribución de calificaciones (≥100 votos)")
        ax.set_xlabel("Calificación promedio")
        ax.set_ylabel("Frecuencia")
        fig.tight_layout()
        st.pyplot(fig)

    col3, col4 = st.columns(2)
    with col3:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        sns.boxplot(
            data=df[df["vote_count"] >= 100], x="tipo", y="vote_average", hue="search_category", palette="Set2", ax=ax
        )
        ax.set_title("Calificación por tipo y categoría de búsqueda")
        ax.set_xlabel("Tipo de contenido")
        ax.set_ylabel("Calificación promedio")
        fig.tight_layout()
        st.pyplot(fig)

    with col4:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        sns.heatmap(
            df[["popularity", "vote_average", "vote_count"]].corr(),
            annot=True, cmap="coolwarm", fmt=".2f", vmin=-1, vmax=1, ax=ax,
        )
        ax.set_title("Correlación entre popularidad, calificación y votos")
        fig.tight_layout()
        st.pyplot(fig)

with tab_conclu:
    st.header("Conclusiones")
    st.markdown(
        """
- **Mes de estreno:** las películas más populares se concentran en el verano, con julio como el mes más fuerte; septiembre y octubre casi no aparecen.
- **Categorías:** Drama es el género más frecuente con mucha diferencia, seguido de Comedy y Animation.
- **Mejor calificados:** al exigir un mínimo de votos desaparecen los títulos con calificaciones extremas por tener 1 o 2 votos, y el ranking se llena de clásicos y series muy vistas.
- **Calificaciones:** se concentran entre 8 y 8.5 una vez filtrados los títulos con pocos votos.
- **Popularidad vs calificación:** la correlación es débil, así que un título muy popular no necesariamente está bien calificado.

Las cifras exactas cambian al mover los filtros de la barra lateral.
"""
    )
