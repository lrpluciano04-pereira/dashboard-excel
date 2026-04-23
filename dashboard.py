import streamlit as st
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
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    bio.seek(0)
    return bio.getvalue()

# --- INTERFACE ---

st.title("📊 Correção e Análise de Provas")
file = st.file_uploader("Suba o Excel com as abas 'Gabarito' e 'RespAluno'", type=["xlsx"])

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

        # CONFIGURAÇÃO DE VALORES
        st.sidebar.header("⚙️ Configuração")
        valor_total = st.sidebar.number_input("Valor total da prova", min_value=0.0, value=10.0)
        metodo = st.sidebar.radio("Pontos:", ["Igualitária", "Por Questão"])

        pesos = {}
        if metodo == "Igualitária":
            v_unitario = valor_total / num_questoes if num_questoes > 0 else 0
            for q in qcols:
                pesos[str(q)] = v_unitario
        else:
            df_pesos_input = pd.DataFrame({"Questão": qcols, "Valor": [0.0]*num_questoes})
            editado = st.data_editor(df_pesos_input, hide_index=True)
            for _, row in editado.iterrows():
                pesos[str(row["Questão"])] = row["Valor"]

        if st.button("🚀 Calcular Notas e Gerar Lista"):
            # --- CORREÇÃO DO ERRO AQUI ---
            # Usamos .str.upper() para aplicar em toda a coluna ou convertemos individualmente
            questoes_gaba = df_gabarito[g_quest].astype(str).tolist()
            respostas_gaba = df_gabarito[g_resp].astype(str).str.upper().str.strip().tolist()
            
            dict_gaba = dict(zip(questoes_gaba, respostas_gaba))

            resultados = []
            for _, row in df_resp.iterrows():
                nota_aluno = 0.0
                acertos = 0
                
                for q in qcols:
                    # Garantir que a resposta do aluno seja string antes do upper
                    r_aluno = str(row[q]).strip().upper() if pd.notna(row[q]) else ""
                    r_certa = dict_gaba.get(str(q))
                    
                    if r_aluno == r_certa:
                        nota_aluno += pesos.get(str(q), 0)
                        acertos += 1
                
                resultados.append({
                    "Nome": row[c_nome] if c_nome else "N/A",
                    "Turma": row[c_turma] if c_turma else "N/A",
                    "Acertos": acertos,
                    "Nota Final": round(nota_aluno, 2)
                })

            df_final = pd.DataFrame(resultados)
            st.divider()
            st.subheader("📋 Lista de Classificação")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Média da Classe", f"{df_final['Nota Final'].mean():.2f}")
            m2.metric("Maior Nota", f"{df_final['Nota Final'].max():.2f}")
            m3.metric("Menor Nota", f"{df_final['Nota Final'].min():.2f}")

            st.dataframe(df_final.sort_values("Nome"), use_container_width=True, hide_index=True)

            st.download_button("📥 Baixar Notas", data=excel_bytes(df_final), file_name="notas.xlsx")

    except Exception as e:
        st.error(f"Ocorreu um erro no processamento: {e}")
