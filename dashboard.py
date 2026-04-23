import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="Corretor de Provas", page_icon="📝", layout="wide")

# --- FUNÇÕES DE SUPORTE (Obrigatórias para evitar o NameError) ---

def find_col(df, options):
    for col in df.columns:
        nome = str(col).lower().strip()
        for opt in options:
            if opt in nome:
                return col
    return None

def question_cols(df):
    """Identifica colunas que são apenas números (as questões)"""
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
st.markdown("Suba um arquivo Excel contendo as abas **Gabarito** e **RespAluno**.")

file = st.file_uploader("Arquivo de Avaliação", type=["xlsx"])

if file:
    try:
        # Lendo as abas
        xls = pd.ExcelFile(file)
        if "Gabarito" not in xls.sheet_names or "RespAluno" not in xls.sheet_names:
            st.error("Erro: O arquivo deve conter exatamente as abas 'Gabarito' e 'RespAluno'.")
            st.stop()

        df_gabarito = pd.read_excel(file, sheet_name="Gabarito")
        df_resp = pd.read_excel(file, sheet_name="RespAluno")

        # Identificação automática de colunas
        qcols = question_cols(df_resp)
        num_questoes = len(qcols)
        
        c_nome = find_col(df_resp, ["nome"])
        c_turma = find_col(df_resp, ["turma"])
        
        g_quest = find_col(df_gabarito, ["questão", "questao"])
        g_resp = find_col(df_gabarito, ["resposta"])

        if not qcols or not g_resp:
            st.error("Não foi possível identificar as questões ou as respostas no arquivo.")
            st.stop()

        # --- CONFIGURAÇÃO DE VALORES ---
        st.sidebar.header("⚙️ Configuração da Nota")
        valor_total = st.sidebar.number_input("Valor total da prova", min_value=0.0, value=10.0)
        metodo = st.sidebar.radio("Distribuição de pontos:", ["Igualitária", "Por Questão (Pesos)"])

        pesos = {}
        if metodo == "Igualitária":
            v_unitario = valor_total / num_questoes
            for q in qcols:
                pesos[str(q)] = v_unitario
            st.sidebar.info(f"Cada questão vale: {v_unitario:.2f}")
        else:
            st.subheader("🖋️ Atribuir pesos por questão")
            # Editor de dados para o professor digitar os valores
            df_pesos_input = pd.DataFrame({"Questão": qcols, "Valor": [0.0]*num_questoes})
            editado = st.data_editor(df_pesos_input, hide_index=True, use_container_width=True)
            for _, row in editado.iterrows():
                pesos[str(row["Questão"])] = row["Valor"]
            
            soma = sum(pesos.values())
            if abs(soma - valor_total) > 0.01:
                st.warning(f"A soma dos pesos ({soma:.2f}) difere do valor total ({valor_total:.2f})")

        # --- PROCESSAMENTO DA CORREÇÃO ---
        if st.button("🚀 Calcular Notas e Gerar Lista"):
            # Dicionário do gabarito para consulta rápida
            dict_gaba = dict(zip(df_gabarito[g_quest].astype(str), df_gabarito[g_resp].astype(str).upper()))

            resultados = []
            for _, row in df_resp.iterrows():
                nota_aluno = 0.0
                acertos = 0
                
                for q in qcols:
                    r_aluno = str(row[q]).strip().upper()
                    r_certa = dict_gaba.get(str(q))
                    
                    if r_aluno == r_certa:
                        nota_aluno += pesos.get(str(q), 0)
                        acertos += 1
                
                resultados.append({
                    "Nome": row[c_nome],
                    "Turma": row[c_turma],
                    "Acertos": acertos,
                    "Nota Final": round(nota_aluno, 2)
                })

            df_final = pd.DataFrame(resultados)

            # Exibição
            st.divider()
            st.subheader("📋 Lista de Classificação")
            
            # Métricas Rápidas
            m1, m2, m3 = st.columns(3)
            m1.metric("Média da Classe", f"{df_final['Nota Final'].mean():.2f}")
            m2.metric("Maior Nota", f"{df_final['Nota Final'].max():.2f}")
            m3.metric("Menor Nota", f"{df_final['Nota Final'].min():.2f}")

            st.dataframe(df_final.sort_values("Nome"), use_container_width=True, hide_index=True)

            # Download
            st.download_button(
                "📥 Baixar Lista de Notas (Excel)",
                data=excel_bytes(df_final),
                file_name="lista_de_notas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Ocorreu um erro no processamento: {e}")
