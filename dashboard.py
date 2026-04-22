import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Educacional", layout="wide")
st.title("📊 Dashboard Educacional - Análise de Respostas")

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
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Analise_RespAluno")

        serie_col = find_col(df, ["serie", "série", "ano"])
        turma_col = find_col(df, ["turma", "classe"])
        disc_col = find_col(df, ["disciplina", "materia", "matéria", "componente"])
        quest_col = find_col(df, ["questao", "questão", "item"])
        metric_col = find_col(df, ["acerto", "acertos", "percentual", "%", "nota", "resultado", "media", "média"])

        if metric_col is None:
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            metric_col = numeric_cols[0] if numeric_cols else None

        if metric_col is None:
            st.error("Não encontrei uma coluna numérica para calcular as médias.")
            st.stop()

        df[metric_col] = to_percent_series(df[metric_col])

        st.success("Aba Analise_RespAluno carregada com sucesso.")

        df_f = df.copy()

        st.subheader("Filtros")
        c1, c2, c3, c4 = st.columns(4)

        if serie_col:
            with c1:
                op = ["Todos"] + sorted(df_f[serie_col].astype(str).dropna().unique().tolist())
                sel = st.selectbox("Série", op)
            if sel != "Todos":
                df_f = df_f[df_f[serie_col].astype(str) == sel]

        if turma_col:
            with c2:
                op = ["Todos"] + sorted(df_f[turma_col].astype(str).dropna().unique().tolist())
                sel = st.selectbox("Turma", op)
            if sel != "Todos":
                df_f = df_f[df_f[turma_col].astype(str) == sel]

        if disc_col:
            with c3:
                op = ["Todos"] + sorted(df_f[disc_col].astype(str).dropna().unique().tolist())
                sel = st.selectbox("Disciplina", op)
            if sel != "Todos":
                df_f = df_f[df_f[disc_col].astype(str) == sel]

        if quest_col:
            with c4:
                op = ["Todas"] + sorted(df_f[quest_col].astype(str).dropna().unique().tolist())
                sel = st.selectbox("Questão", op)
            if sel != "Todas":
                df_f = df_f[df_f[quest_col].astype(str) == sel]

        media_geral = df_f[metric_col].mean()

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Média geral", f"{media_geral:.1f}%")
        with k2:
            st.metric("Registros", len(df_f))
        with k3:
            st.metric("Maior valor", f"{df_f[metric_col].max():.1f}%")
        with k4:
            st.metric("Menor valor", f"{df_f[metric_col].min():.1f}%")

        st.divider()

        colA, colB = st.columns(2)

        with colA:
            st.subheader("Média por Série")
            if serie_col:
                g1 = df_f.groupby(serie_col, as_index=False)[metric_col].mean().sort_values(metric_col, ascending=False)
                fig1 = px.bar(g1, x=serie_col, y=metric_col, text=metric_col, title="Média percentual por Série")
                fig1.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig1.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
                st.plotly_chart(fig1, use_container_width=True)

        with colB:
            st.subheader("Média por Disciplina")
            if disc_col:
                g2 = df_f.groupby(disc_col, as_index=False)[metric_col].mean().sort_values(metric_col, ascending=False)
                fig2 = px.bar(g2, x=disc_col, y=metric_col, text=metric_col, title="Média percentual por Disciplina")
                fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig2.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
                st.plotly_chart(fig2, use_container_width=True)

        colC, colD = st.columns(2)

        with colC:
            st.subheader("Média por Turma")
            if turma_col:
                g3 = df_f.groupby(turma_col, as_index=False)[metric_col].mean().sort_values(metric_col, ascending=False)
                fig3 = px.bar(g3, x=turma_col, y=metric_col, text=metric_col, title="Média percentual por Turma")
                fig3.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig3.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
                st.plotly_chart(fig3, use_container_width=True)

        with colD:
            st.subheader("Resumo dos dados")
            st.dataframe(df_f.head(50), use_container_width=True)

        st.divider()

        if turma_col and disc_col:
            st.subheader("Mapa de Calor: Turma x Disciplina")
            heat = df_f.pivot_table(index=turma_col, columns=disc_col, values=metric_col, aggfunc="mean")
            fig4 = px.imshow(heat, text_auto=".1f", aspect="auto", color_continuous_scale="Blues", zmin=0, zmax=100)
            st.plotly_chart(fig4, use_container_width=True)

        if quest_col:
            st.subheader("Questões com Menor Desempenho")
            q = df_f.groupby(quest_col, as_index=False)[metric_col].mean().sort_values(metric_col, ascending=True).head(10)
            fig5 = px.bar(q, x=metric_col, y=quest_col, orientation="h", text=metric_col)
            fig5.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig5.update_xaxes(range=[0, 100], tickformat='.0f', title="Percentual")
            st.plotly_chart(fig5, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao carregar a planilha: {e}")
else:
    st.info("Envie uma planilha para começar.")
