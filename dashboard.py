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
        df.to_excel(writer, index=False, sheet_name="Notas")
    bio.seek(0)
    return bio.getvalue()

# --- INTERFACE ---

st.title("📊 Sistema de Notas e Classificação")

file = st.file_uploader("Carregue sua planilha Excel (abas 'Gabarito' e 'RespAluno')", type=["xlsx"])

if file:
    try:
        xls = pd.ExcelFile(file)
        if "Gabarito" not in xls.sheet_names or "RespAluno" not in xls.sheet_names:
            st.error("⚠️ Erro: O arquivo precisa das abas 'Gabarito' e 'RespAluno'.")
            st.stop()

        df_gabarito = pd.read_excel(file, sheet_name="Gabarito")
        df_resp = pd.read_excel(file, sheet_name="RespAluno")

        qcols = question_cols(df_resp)
        num_questoes = len(qcols)
        
        c_nome = find_col(df_resp, ["nome"])
        c_turma = find_col(df_resp, ["turma"])
        g_quest = find_col(df_gabarito, ["questão", "questao"])
        g_resp = find_col(df_gabarito, ["resposta"])

        # --- CONFIGURAÇÃO DE VALORES (SIDEBAR) ---
        st.sidebar.header("🎯 Definição de Valores")
        valor_total_prova = st.sidebar.number_input("Valor total da prova", min_value=0.0, value=10.0, step=0.5)
        
        metodo = st.sidebar.radio("Como deseja atribuir o valor?", 
                                 ["Dividir valor total igualmente", "Definir valor de cada questão"])

        valores_questoes = {}
        
        if metodo == "Dividir valor total igualmente":
            valor_unitario = valor_total_prova / num_questoes if num_questoes > 0 else 0
            for q in qcols:
                valores_questoes[str(q).strip()] = valor_unitario
            st.sidebar.info(f"Cada questão vale: {valor_unitario:.2f}")
        
        else:
            st.markdown("### 🖋️ Informe o valor individual de cada questão")
            st.caption("A soma dos valores abaixo deve totalizar o valor total da prova definido na lateral.")
            
            df_valores_editor = pd.DataFrame({
                "Questão": [str(q).strip() for q in qcols], 
                "Valor": [0.0]*num_questoes
            })
            
            editado = st.data_editor(df_valores_editor, hide_index=True, use_container_width=True)
            
            for _, row in editado.iterrows():
                valores_questoes[str(row["Questão"]).strip()] = float(row["Valor"])
            
            soma_atual = sum(valores_questoes.values())
            if abs(soma_atual - valor_total_prova) > 0.001:
                st.warning(f"⚠️ A soma dos valores inseridos ({soma_atual:.2f}) é diferente do valor total da prova ({valor_total_prova:.2f}).")

        # --- BOTÃO DE PROCESSAMENTO ---
        if st.button("📝 Calcular Notas e Gerar Lista Final"):
            # Gabarito organizado
            questoes_gaba = df_gabarito[g_quest].astype(str).str.strip().tolist()
            respostas_gaba = df_gabarito[g_resp].astype(str).str.upper().str.strip().tolist()
            dict_gaba = dict(zip(questoes_gaba, respostas_gaba))

            lista_final = []
            for _, row in df_resp.iterrows():
                nota_aluno = 0.0
                acertos = 0
                
                for q in qcols:
                    q_str = str(q).strip()
                    resp_aluno = str(row[q]).strip().upper() if pd.notna(row[q]) else ""
                    resp_certa = dict_gaba.get(q_str)
                    
                    if resp_aluno == resp_certa and resp_certa is not None:
                        nota_aluno += valores_questoes.get(q_str, 0.0)
                        acertos += 1
                
                lista_final.append({
                    "Turma": str(row[c_turma]) if c_turma and pd.notna(row[c_turma]) else "N/A",
                    "Nome": str(row[c_nome]) if c_nome and pd.notna(row[c_nome]) else "Sem Nome",
                    "Acertos": acertos,
                    "Nota Final": round(nota_aluno, 2)
                })

            df_final = pd.DataFrame(lista_final)
            df_final = df_final.sort_values(by=["Turma", "Nome"])
            df_final = df_final[["Turma", "Nome", "Acertos", "Nota Final"]]

            st.divider()
            st.subheader("📋 Lista de Notas")
            st.dataframe(df_final, use_container_width=True, hide_index=True)

            # Exportação
            excel_out = excel_bytes(df_final)
            st.download_button(
                label="📥 Baixar Relatório (Excel)",
                data=excel_out,
                file_name="Notas_Finais.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.success("Notas calculadas com sucesso baseadas no valor de cada questão!")

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
