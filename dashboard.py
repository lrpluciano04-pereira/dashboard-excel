import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(page_title="Dashboard Educacional", layout="wide")
st.title("📊 Dashboard Educacional")

uploaded_file = st.file_uploader("Envie a planilha Excel", type=["xlsx", "xls"])

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

def natural_key(text):
    parts = re.split(r'(\d+)', str(text))
    return [int(p) if p.isdigit() else p for p in parts]

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Analise_RespAluno")

        semestre_col = find_col(df, ["semestre"])
        pp_col = find_col(df, ["pp"])
        turma_col = find_col(df, ["turma"])

        serie_cols = [c for c in df.columns if str(c).strip() in ["2-1MA", "2-2MA", "2-3MA"]]

        if semestre_col is None:
            st.error("Não encontrei a coluna Semestre.")
            st.stop()

        if not serie_cols:
            st.error("Não encontrei as colunas 2-1MA, 2-2MA e 2-3MA.")
            st.stop()

        for c in serie_cols:
            df[c] = to_percent_series(df[c])

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
            serie_order = ["2-1MA", "2-2MA", "2-3MA"]
            serie_values = []
            for c in serie_order:
                if c in df_f.columns:
                    serie_values.append({"Série": c, "Média": df_f[c].mean()})

            g_serie = pd.DataFrame(serie_values)

            fig1 = px.bar(
                g_serie,
                x="Série",
                y="Média",
                text="Média",
                color="Série",
                color_discrete_map={
                    "2-1MA": "#1f77b4",
                    "2-2MA": "#2ca02c",
                    "2-3MA": "#ff7f0e"
                },
                category_orders={"Série": serie_order}
            )
            fig1.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig1.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
            fig1.update_layout(xaxis_title="Série", yaxis_title="Percentual", showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            st.markdown("**Média Geral Série/PP**")
            if pp_col:
                g_pp = df_f.groupby(pp_col, as_index=False)[pp_col].size()
                g_pp = df_f.groupby(pp_col, as_index=False)[serie_cols[0]].mean()
                g_pp[pp_col] = g_pp[pp_col].astype(str).str.strip()
                g_pp = g_pp.sort_values(pp_col, key=lambda s: s.map(natural_key))

                fig2 = px.bar(
                    g_pp,
                    x=pp_col,
                    y=serie_cols[0],
                    text=serie_cols[0],
                    color=pp_col
                )
                fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig2.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
                fig2.update_layout(xaxis_title="Série/PP", yaxis_title="Percentual", showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.warning("Não encontrei a coluna Série/PP na planilha.")

        st.markdown("**Média Geral Turmas/PP's**")
        if turma_col:
            g_turma = df_f.groupby(turma_col, as_index=False)[serie_cols[0]].mean()
            g_turma[turma_col] = g_turma[turma_col].astype(str).str.strip()
            g_turma = g_turma.sort_values(turma_col, key=lambda s: s.map(natural_key))

            fig3 = px.bar(
                g_turma,
                x=turma_col,
                y=serie_cols[0],
                text=serie_cols[0],
                color=turma_col
            )
            fig3.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig3.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
            fig3.update_layout(xaxis_title="Turma", yaxis_title="Percentual", showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.warning("Não encontrei a coluna Turma na planilha.")

        st.dataframe(df_f.head(50), use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao carregar a planilha: {e}")
else:
    st.info("Envie uma planilha para começar.")
