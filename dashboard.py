import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Excel", layout="wide")
st.title("📊 Dashboard Interativo")

uploaded_file = st.file_uploader("Faça upload da sua planilha (.xlsx)", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Analise_RespAluno")

        st.success("Planilha carregada com sucesso!")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Dados")
            st.dataframe(df)

        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        all_cols = df.columns.tolist()

        if len(all_cols) >= 2 and len(numeric_cols) >= 1:
            with col2:
                st.subheader("Gráfico")
                x_col = st.selectbox("Eixo X", all_cols)
                y_col = st.selectbox("Eixo Y", numeric_cols)
                fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} por {x_col}")
                st.plotly_chart(fig, use_container_width=True)

        st.subheader("Resumo estatístico")
        st.write(df.describe(include="all"))

    except Exception as e:
        st.error(f"Erro ao ler a aba 'Analise_RespAluno': {e}")
