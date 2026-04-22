import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Educacional", layout="wide")
st.title("📊 Dashboard Educacional")

uploaded_file = st.file_uploader("Envie a planilha Excel", type=["xlsx", "xls"])

def find_col(df, options):
    for col in df.columns:
        name = str(col).lower()
        for opt in options:
            if opt in name:
                return col
    return None

def to_percent_series(s):
    s = pd.to_numeric(s, errors="coerce")
    if s.dropna().max() <= 1:
        return s * 100
    return s

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Analise_RespAluno")

    serie_col = find_col(df, ["serie", "série", "ano"])
    semestre_col = find_col(df, ["semestre"])
    metric_col = find_col(df, ["acerto", "acertos", "percentual", "%", "nota", "resultado", "media", "média"])

    if metric_col is None:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        metric_col = numeric_cols[0] if numeric_cols else None

    if metric_col is None or serie_col is None or semestre_col is None:
        st.error("Não encontrei as colunas necessárias: Série, Semestre e Métrica.")
        st.stop()

    df[metric_col] = to_percent_series(df[metric_col])

    st.subheader("Filtro de semestre")
    semestres = ["Todos"] + sorted(df[semestre_col].astype(str).dropna().unique().tolist())
    semestre_sel = st.selectbox("Semestre", semestres)

    df_f = df.copy()
    if semestre_sel != "Todos":
        df_f = df_f[df_f[semestre_col].astype(str) == semestre_sel]

    st.subheader("Média geral por série")
    g = df_f.groupby(serie_col, as_index=False)[metric_col].mean().sort_values(metric_col, ascending=False)

    fig = px.bar(
        g,
        x=serie_col,
        y=metric_col,
        text=metric_col,
        title="Média percentual por Série"
    )
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
    fig.update_layout(xaxis_title="Série", yaxis_title="Percentual")

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(g, use_container_width=True)
