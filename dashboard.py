import streamlit as st
import pandas as pd
import re
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Dashboard Educacional", page_icon="📊", layout="wide")

# --- FUNÇÕES DE SUPORTE ---

def find_col(df, options):
    for col in df.columns:
        nome = str(col).lower().strip()
        for opt in options:
            if opt in nome:
                return col
    return None

def question_cols(df):
    cols = []
    for c in df.columns:
        s = str(c).strip()
        if s.isdigit() or re.fullmatch(r'\d+', s):
            cols.append(c)
    return cols

def excel_bytes(df):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Notas")
    bio.seek(0)
    return bio.getvalue()

# --- INTERFACE PRINCIPAL ---

st.title("📊 Análise de Dados Educacionais")
st.markdown("Sistema integrado de correção e análise pedagógica.")

file = st.file_uploader("Carregue a planilha (Abas: 'Gabarito' e 'RespAluno')", type=["xlsx"])

if file:
    try:
        xls = pd.ExcelFile(file)
        if "Gabarito" not in xls.sheet_names or "RespAluno" not in xls.sheet_names:
            st.error("⚠️ O arquivo deve conter as abas 'Gabarito' and 'RespAluno'.")
            st.stop()

        df_gabarito = pd.read_excel(file, sheet_name="Gabarito")
        df_resp = pd.read_excel(file, sheet_name="RespAluno")

        # Mapeamento automático
        qcols = question_cols(df_resp)
        num_questoes = len(qcols)
        c_nome = find_col(df_resp, ["nome"])
        c_turma = find_col(df_resp, ["turma"])
        g_quest = find_col(df_gabarito, ["questão", "questao"])
        g_resp = find_col(df_gabarito, ["resposta"])

        # --- CONFIGURAÇÃO DE VALORES (SIDEBAR) ---
        st.sidebar.header("🎯 Definição de Valores")
        valor_total_prova = st.sidebar.number_input("Valor total da prova", min_value=0.0, value=10.0, step=0.5)
        metodo = st.sidebar.radio("Atribuição de valor:", ["Dividir igualmente", "Individual por questão"])

        valores_questoes = {}
        if metodo == "Dividir igualmente":
            v_unit = valor_total_prova / num_questoes if num_questoes > 0 else 0
            for q in qcols:
                valores_questoes[str(q).strip()] = v_unit
        else:
            st.write("### 🖋️ Informe o valor de cada questão")
            df_pesos_editor = pd.DataFrame({
                "Questão": [str(q).strip() for q in qcols], 
                "Valor": [valor_total_prova/num_questoes]*num_questoes
            })
            editado = st.data_editor(df_pesos_editor, hide_index=True, use_container_width=True)
            for _, row in editado.iterrows():
                valores_questoes[str(row["Questão"]).strip()] = float(row["Valor"])

        # --- BOTÃO DE PROCESSAMENTO ---
        if st.button("📝 Calcular Notas e Gerar Análises"):
            # 1. Preparar Gabarito
            questoes_gaba = df_gabarito[g_quest].astype(str).str.strip().tolist()
            respostas_gaba = df_gabarito[g_resp].astype(str).str.upper().str.strip().tolist()
            dict_gaba = dict(zip(questoes_gaba, respostas_gaba))

            # 2. Processar Correção
            lista_final = []
            detalhes_questoes = [] # Para análise de acertos por item

            for _, row in df_resp.iterrows():
                nota_aluno = 0.0
                acertos_aluno = 0
                
                for q in qcols:
                    q_str = str(q).strip()
                    resp_aluno = str(row[q]).strip().upper() if pd.notna(row[q]) else ""
                    resp_certa = dict_gaba.get(q_str)
                    
                    acertou = 1 if (resp_aluno == resp_certa and resp_certa is not None) else 0
                    if acertou:
                        nota_aluno += valores_questoes.get(q_str, 0.0)
                        acertos_aluno += 1
                    
                    detalhes_questoes.append({"Questão": q_str, "Acertou": acertou})

                lista_final.append({
                    "Turma": str(row[c_turma]) if c_turma else "N/A",
                    "Nome": str(row[c_nome]) if c_nome else "Sem Nome",
                    "Acertos": acertos_aluno,
                    "Nota Final": round(nota_aluno, 2)
                })

            df_final = pd.DataFrame(lista_final).sort_values(by=["Turma", "Nome"])
            
            # --- ÁREA DO DASHBOARD ---
            st.divider()
            st.header("🔍 Análise Geral de Desempenho")
            
            # Métricas em destaque
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Média Geral", f"{df_final['Nota Final'].mean():.2f}")
            m2.metric("Aproveitamento", f"{(df_final['Acertos'].sum()/(len(df_final)*num_questoes)*100):.1f}%")
            m3.metric("Maior Nota", f"{df_final['Nota Final'].max():.2f}")
            m4.metric("Menor Nota", f"{df_final['Nota Final'].min():.2f}")

            tab_lista, tab_graficos, tab_itens = st.tabs(["📋 Lista de Notas", "📈 Gráficos", "🎯 Análise por Item"])

            with tab_lista:
                st.dataframe(df_final, use_container_width=True, hide_index=True)
                st.download_button("📥 Baixar Excel", data=excel_bytes(df_final), file_name="Notas_Finais.xlsx")

            with tab_graficos:
                col_a, col_b = st.columns(2)
                with col_a:
                    fig_hist = px.histogram(df_final, x="Nota Final", title="Distribuição de Notas",
                                           color_discrete_sequence=['#1E88E5'], labels={'count':'Alunos'})
                    st.plotly_chart(fig_hist, use_container_width=True)
                with col_b:
                    fig_box = px.box(df_final, x="Turma", y="Nota Final", title="Dispersão por Turma", color="Turma")
                    st.plotly_chart(fig_box, use_container_width=True)

            with tab_itens:
                df_itens = pd.DataFrame(detalhes_questoes)
                df_analise_item = df_itens.groupby("Questão")["Acertou"].mean().reset_index()
                df_analise_item["Acerto %"] = df_analise_item["Acertou"] * 100
                
                fig_itens = px.bar(df_analise_item, x="Questão", y="Acerto %", 
                                  title="Índice de Acerto por Questão",
                                  color="Acerto %", color_continuous_scale="RdYlGn")
                fig_itens.add_hline(y=50, line_dash="dot", line_color="red")
                st.plotly_chart(fig_itens, use_container_width=True)
                st.info("Questões abaixo da linha tracejada (50%) sugerem necessidade de revisão do conteúdo.")

    except Exception as e:
        st.error(f"Erro Crítico: {e}")
