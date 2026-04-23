import streamlit as st
import pd
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="Corretor de Provas", page_icon="📝", layout="wide")

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
    # Usando o motor 'openpyxl' para garantir compatibilidade com .xlsx
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Resultados")
    bio.seek(0)
    return bio.getvalue()

# --- INTERFACE ---

st.title("📊 Correção e Classificação de Notas")
st.markdown("O sistema processará a planilha e organizará a lista por **Turma** e **Nome**.")

file = st.file_uploader("Suba o arquivo Excel (abas 'Gabarito' e 'RespAluno')", type=["xlsx"])

if file:
    try:
        xls = pd.ExcelFile(file)
        if "Gabarito" not in xls.sheet_names or "RespAluno" not in xls.sheet_names:
            st.error("Erro: O arquivo deve conter as abas 'Gabarito' e 'RespAluno'.")
            st.stop()

        df_gabarito = pd.read_excel(file, sheet_name="Gabarito")
        df_resp = pd.read_excel(file, sheet_name="RespAluno")

        qcols = question_cols(df_resp)
        num_questoes = len(qcols)
        
        c_nome = find_col(df_resp, ["nome"])
        c_turma = find_col(df_resp, ["turma"])
        g_quest = find_col(df_gabarito, ["questão", "questao"])
        g_resp = find_col(df_gabarito, ["resposta"])

        # CONFIGURAÇÃO DE VALORES (BARRA LATERAL)
        st.sidebar.header("⚙️ Parâmetros")
        valor_total = st.sidebar.number_input("Valor total da prova", min_value=0.0, value=10.0)
        metodo = st.sidebar.radio("Atribuição de pontos:", ["Igualitária", "Por Questão (Pesos)"])

        pesos = {}
        if metodo == "Igualitária":
            v_unitario = valor_total / num_questoes if num_questoes > 0 else 0
            for q in qcols:
                pesos[str(q)] = v_unitario
        else:
            st.info("Defina o valor de cada questão na tabela abaixo:")
            df_pesos_input = pd.DataFrame({"Questão": qcols, "Valor": [0.0]*num_questoes})
            editado = st.data_editor(df_pesos_input, hide_index=True, use_container_width=True)
            for _, row in editado.iterrows():
                pesos[str(row["Questão"])] = row["Valor"]

        if st.button("🚀 Calcular e Gerar Lista Final"):
            # Preparação do Gabarito (Correção do erro .str.upper())
            questoes_gaba = df_gabarito[g_quest].astype(str).tolist()
            respostas_gaba = df_gabarito[g_resp].astype(str).str.upper().str.strip().tolist()
            dict_gaba = dict(zip(questoes_gaba, respostas_gaba))

            resultados = []
            for _, row in df_resp.iterrows():
                nota_aluno = 0.0
                acertos = 0
                
                for q in qcols:
                    r_aluno = str(row[q]).strip().upper() if pd.notna(row[q]) else ""
                    r_certa = dict_gaba.get(str(q))
                    
                    if r_aluno == r_certa:
                        nota_aluno += pesos.get(str(q), 0)
                        acertos += 1
                
                resultados.append({
                    "Turma": row[c_turma] if c_turma else "S/T",
                    "Nome": row[c_nome] if c_nome else "Sem Nome",
                    "Acertos": acertos,
                    "Nota Final": round(nota_aluno, 2)
                })

            # Criando o DataFrame final
            df_final = pd.DataFrame(resultados)

            # --- ORDENAÇÃO E FORMATAÇÃO ---
            # Ordena por Turma (ascendente) e depois por Nome (ascendente)
            df_final = df_final.sort_values(by=["Turma", "Nome"])
            
            # Reordenando as colunas conforme solicitado
            colunas_ordem = ["Turma", "Nome", "Acertos", "Nota Final"]
            df_final = df_final[colunas_ordem]

            st.divider()
            st.subheader("📋 Lista de Classe Processada")
            
            # Exibição na tela
            st.dataframe(df_final, use_container_width=True, hide_index=True)

            # Botão de Download (Excel)
            xlsx_data = excel_bytes(df_final)
            st.download_button(
                label="📥 Baixar Planilha de Notas (Excel)",
                data=xlsx_data,
                file_name="Lista_de_Notas_Final.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            st.success("Cálculo concluído! Você pode baixar o arquivo acima.")

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
