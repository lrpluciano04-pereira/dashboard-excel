import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Educacional", layout="wide")
st.title("📊 Dashboard Educacional")

uploaded_file = st.file_uploader("Envie a planilha Excel", type=["xlsx", "xls"])

serie_ordem = ["2-1MA", "2-2MA", "2-3MA"]
cores_serie = {
    "2-1MA": "#1f77b4",
    "2-2MA": "#2ca02c",
    "2-3MA": "#ff7f0e"
}

def find_col(df, options):
    for col in df.columns:
        nome = str(col).lower().strip()
        for opt in options:
            if opt in nome:
                return col
    return None

def to_percent_series(s):
    s = pd.to_numeric(s, errors="coerce")
    if s.dropna().max() <= 1:
        return s * 100
    return s

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Analise_RespAluno")

        serie_col = find_col(df, ["serie", "série", "ano"])
        semestre_col = find_col(df, ["semestre"])
        metric_col = find_col(df, ["acerto", "acertos", "percentual", "%", "nota", "resultado", "media", "média"])
        pp_col = find_col(df, ["pp"])
        turma_col = find_col(df, ["turma"])

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

        st.subheader("Análise de Prova Parcial")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Média geral por série**")
            g_serie = df_f.groupby(serie_col, as_index=False)[metric_col].mean()
            g_serie[serie_col] = g_serie[serie_col].astype(str).str.strip()
            g_serie = g_serie.set_index(serie_col).reindex(serie_ordem).reset_index()
            g_serie[metric_col] = g_serie[metric_col].fillna(0)

            fig1 = px.bar(
                g_serie,
                x=serie_col,
                y=metric_col,
                text=metric_col,
                color=serie_col,
                color_discrete_map=cores_serie,
                category_orders={serie_col: serie_ordem}
            )
            fig1.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig1.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
            fig1.update_layout(
                xaxis_title="Série",
                yaxis_title="Percentual",
                showlegend=False
            )
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            st.markdown("**Média Geral Série/PP**")
            if pp_col:
                g_pp = df_f.groupby(pp_col, as_index=False)[metric_col].mean()
                g_pp[pp_col] = g_pp[pp_col].astype(str).str.strip()
                g_pp = g_pp.sort_values(metric_col, ascending=False)

                fig2 = px.bar(
                    g_pp,
                    x=pp_col,
                    y=metric_col,
                    text=metric_col,
                    color=pp_col
                )
                fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig2.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
                fig2.update_layout(
                    xaxis_title="Série/PP",
                    yaxis_title="Percentual",
                    showlegend=False
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.warning("Não encontrei a coluna Série/PP na planilha.")

        st.markdown("**Média Geral Turmas/PP's**")
        if turma_col:
            g_turma = df_f.groupby(turma_col, as_index=False)[metric_col].mean().sort_values(metric_col, ascending=False)

            fig3 = px.bar(
                g_turma,
                x=turma_col,
                y=metric_col,
                text=metric_col,
                color=turma_col
            )
            fig3.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig3.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
            fig3.update_layout(
                xaxis_title="Turma",
                yaxis_title="Percentual",
                showlegend=False
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.warning("Não encontrei a coluna Turma na planilha.")

        st.dataframe(df_f.head(50), use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao carregar a planilha: {e}")
else:
    st.info("Envie uma planilha para começar.")
