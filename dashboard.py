import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Educacional", layout="wide")
st.title("📊 Dashboard Educacional")

uploaded_file = st.file_uploader("Envie a planilha Excel", type=["xlsx", "xls"])

def find_col(df, options):
    for col in df.columns:
        for opt in options:
            if opt.lower() in str(col).lower():
                return col
    return None

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Analise_RespAluno")

        serie_col = find_col(df, ["serie", "série", "ano"])
        turma_col = find_col(df, ["turma", "classe"])
        disc_col = find_col(df, ["disciplina", "materia", "matéria", "componente"])
        quest_col = find_col(df, ["questao", "questão", "item"])
        resp_col = find_col(df, ["acerto", "acertos", "percentual", "%", "nota", "resultado"])

        st.success("Aba Analise_RespAluno carregada com sucesso.")

        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        metric_col = resp_col if resp_col in df.columns else (numeric_cols[0] if numeric_cols else None)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Registros", len(df))
        with c2:
            st.metric("Colunas", len(df.columns))
        with c3:
            st.metric("Turmas", df[turma_col].nunique() if turma_col else "-")
        with c4:
            st.metric("Disciplinas", df[disc_col].nunique() if disc_col else "-")

        filtros = st.columns(4)
        df_f = df.copy()

        if serie_col:
            with filtros[0]:
                vals = ["Todos"] + sorted(df[serie_col].astype(str).dropna().unique().tolist())
                sel = st.selectbox("Série", vals)
            if sel != "Todos":
                df_f = df_f[df_f[serie_col].astype(str) == sel]

        if turma_col:
            with filtros[1]:
                vals = ["Todos"] + sorted(df_f[turma_col].astype(str).dropna().unique().tolist())
                sel = st.selectbox("Turma", vals)
            if sel != "Todos":
                df_f = df_f[df_f[turma_col].astype(str) == sel]

        if disc_col:
            with filtros[2]:
                vals = ["Todos"] + sorted(df_f[disc_col].astype(str).dropna().unique().tolist())
                sel = st.selectbox("Disciplina", vals)
            if sel != "Todos":
                df_f = df_f[df_f[disc_col].astype(str) == sel]

        if metric_col:
            with filtros[3]:
                st.write("Métrica:", metric_col)

        if metric_col and df_f[metric_col].dtype != "object":
            media_geral = df_f[metric_col].mean()
        else:
            media_geral = None

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Média geral", f"{media_geral:.1f}" if media_geral is not None else "-")
        with c2:
            st.metric("Maior valor", f"{df_f[metric_col].max():.1f}" if metric_col and metric_col in df_f and df_f[metric_col].dtype != "object" else "-")
        with c3:
            st.metric("Menor valor", f"{df_f[metric_col].min():.1f}" if metric_col and metric_col in df_f and df_f[metric_col].dtype != "object" else "-")

        a, b = st.columns(2)

        with a:
            st.subheader("Média por Série")
            if serie_col and metric_col:
                g1 = df_f.groupby(serie_col, as_index=False)[metric_col].mean()
                fig1 = px.bar(g1, x=serie_col, y=metric_col, text_auto=".1f")
                st.plotly_chart(fig1, use_container_width=True)

        with b:
            st.subheader("Média por Disciplina")
            if disc_col and metric_col:
                g2 = df_f.groupby(disc_col, as_index=False)[metric_col].mean().sort_values(metric_col, ascending=False)
                fig2 = px.bar(g2, x=disc_col, y=metric_col, text_auto=".1f")
                st.plotly_chart(fig2, use_container_width=True)

        c, d = st.columns(2)

        with c:
            st.subheader("Média por Turma")
            if turma_col and metric_col:
                g3 = df_f.groupby(turma_col, as_index=False)[metric_col].mean().sort_values(metric_col, ascending=False)
                fig3 = px.bar(g3, x=turma_col, y=metric_col, text_auto=".1f")
                st.plotly_chart(fig3, use_container_width=True)

        with d:
            st.subheader("Tabela de dados")
            st.dataframe(df_f.head(200), use_container_width=True)

        if turma_col and disc_col and metric_col:
            st.subheader("Mapa de calor: Turma x Disciplina")
            heat = df_f.pivot_table(index=turma_col, columns=disc_col, values=metric_col, aggfunc="mean")
            fig4 = px.imshow(heat, text_auto=".1f", aspect="auto", color_continuous_scale="Blues")
            st.plotly_chart(fig4, use_container_width=True)

        if quest_col and metric_col:
            st.subheader("Questões com menor desempenho")
            q = df_f.groupby(quest_col, as_index=False)[metric_col].mean().sort_values(metric_col, ascending=True).head(10)
            fig5 = px.bar(q, x=metric_col, y=quest_col, orientation="h", text_auto=".1f")
            st.plotly_chart(fig5, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao carregar a planilha: {e}")
