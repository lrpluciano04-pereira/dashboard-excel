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
    # O motor openpyxl é o padrão para arquivos .xlsx
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Notas")
    bio.seek(0)
    return bio.getvalue()

# --- INTERFACE ---

st.title("📊 Sistema de Notas e Classificação")
st.markdown("Gere a lista de classe organizada por **Turma** e **Nome** a partir das abas 'Gabarito' e 'RespAluno'.")

file = st.file_uploader("Carregue sua planilha Excel", type=["xlsx"])

if file:
    try:
        xls = pd.ExcelFile(file)
        if "Gabarito" not in xls.sheet_names or "RespAluno" not in xls.sheet_names:
            st.error("⚠️ Erro: O arquivo precisa das abas 'Gabarito' e 'RespAluno'.")
            st.stop()

        df_gabarito = pd.read_excel(file, sheet_name="Gabarito")
        df_resp = pd.read_excel(file, sheet_name="RespAluno")

        # Mapeamento de colunas
        qcols = question_cols(df_resp)
        num_questoes = len(qcols)
        c_nome = find_col(df_resp, ["nome"])
        c_turma = find_col(df_resp, ["turma"])
        g_quest = find_col(df_gabarito, ["questão", "questao"])
        g_resp = find_col(df_gabarito, ["resposta"])

        # BARRA LATERAL: CONFIGURAÇÃO DE VALORES
        st.sidebar.header("💰 Pontuação")
        valor_total = st.sidebar.number_input("Valor total da prova", min_value=0.0, value=10.0, step=0.5)
        metodo = st.sidebar.radio("Como distribuir os pontos?", ["Dividir por igual", "Pesos diferentes"])

        pesos = {}
        if metodo == "Dividir por igual":
            v_unit = valor_total / num_questoes if num_questoes > 0 else 0
            for q in qcols:
                pesos[str(q)] = v_unit
            st.sidebar.caption(f"Valor por questão: {v_unit:.2f}")
        else:
            st.write("### 🖋️ Defina o valor de cada questão:")
            df_pesos_editor = pd.DataFrame({"Questão": qcols, "Valor": [0.0]*num_questoes})
            editado = st.data_editor(df_pesos_editor, hide_index=True, use_container_width=True)
            for _, row in editado.iterrows():
                pesos[str(row["Questão"])] = row["Valor"]

        # BOTÃO DE PROCESSAMENTO
        if st.button("📝 Calcular Notas e Organizar Lista"):
            # Preparar dicionário do Gabarito
            # .str.upper() e .str.strip() garantem que 'a' seja igual a 'A' e ignora espaços extras
            questoes_gaba = df_gabarito[g_quest].astype(str).tolist()
            respostas_gaba = df_gabarito[g_resp].astype(str).str.upper().str.strip().tolist()
            dict_gaba = dict(zip(questoes_gaba, respostas_gaba))

            lista_final = []
            for _, row in df_resp.iterrows():
                nota_aluno = 0.0
                acertos = 0
                
                for q in qcols:
                    resp_aluno = str(row[q]).strip().upper() if pd.notna(row[q]) else ""
                    resp_certa = dict_gaba.get(str(q))
                    
                    if resp_aluno == resp_certa:
                        nota_aluno += pesos.get(str(q), 0)
                        acertos += 1
                
                lista_final.append({
                    "Turma": row[c_turma] if c_turma else "Indefinida",
                    "Nome": row[c_nome] if c_nome else "Sem Nome",
                    "Acertos": acertos,
                    "Nota Final": round(nota_aluno, 2)
                })

            # Criar DataFrame e ordenar
            df_final = pd.DataFrame(lista_final)
            
            # Ordenação: primeiro Turma, depois Nome
            df_final = df_final.sort_values(by=["Turma", "Nome"])
            
            # Reordenar colunas conforme pedido
            df_final = df_final[["Turma", "Nome", "Acertos", "Nota Final"]]

            st.divider()
            st.subheader("📋 Resultados da Avaliação")
            
            # Exibir na tela
            st.dataframe(df_final, use_container_width=True, hide_index=True)

            # Preparar download
            excel_out = excel_bytes(df_final)
            st.download_button(
                label="📥 Baixar Lista de Notas (Excel)",
                data=excel_out,
                file_name="Relatorio_Notas_Classe.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            st.success("Lista gerada e ordenada com sucesso!")

    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")
else:
    st.info("Aguardando upload da planilha para iniciar a correção.")
