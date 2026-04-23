import streamlit as st
import pandas as pd
import re

# ... (Mantenha as funções auxiliares find_col, safe_str, etc., que você já criou)

st.title("📊 Sistema de Correção de Provas")

# 1. Upload de arquivo único
file = st.file_uploader("Suba a planilha (com as guias 'Gabarito' e 'RespAluno')", type=["xlsx"])

if file:
    # Lendo todas as abas
    xls = pd.ExcelFile(file)
    sheets = xls.sheet_names
    
    if "Gabarito" in sheets and "RespAluno" in sheets:
        gabarito = pd.read_excel(file, sheet_name="Gabarito")
        resp = pd.read_excel(file, sheet_name="RespAluno")
        
        # Identificação de colunas (usando suas funções find_col)
        qcols = question_cols(resp) # Aquela sua função que identifica colunas numéricas
        num_questoes = len(qcols)
        
        st.divider()
        st.subheader("⚙️ Configuração da Pontuação")
        
        # 2. Definição do valor da prova
        col1, col2 = st.columns(2)
        valor_total = col1.number_input("Quanto vale a prova?", min_value=0.0, value=10.0, step=0.5)
        modo_pontuacao = col2.radio("Como a nota deve ser calculada?", 
                                   ["Dividir valor por igual", "Atribuir pesos diferentes por questão"])

        pesos = {}
        
        if modo_pontuacao == "Dividir valor por igual":
            valor_por_questao = valor_total / num_questoes
            for q in qcols:
                pesos[q] = valor_por_questao
            st.info(f"Cada questão vale: {valor_por_questao:.2f}")
        
        else:
            st.write("Digite o valor de cada questão:")
            # Criando uma tabela editável para os pesos
            df_pesos = pd.DataFrame({"Questão": qcols, "Valor": [0.0]*num_questoes})
            edited_pesos = st.data_editor(df_pesos, hide_index=True)
            
            # Validando se a soma dos pesos bate com o valor total
            soma_pesos = edited_pesos["Valor"].sum()
            if soma_pesos != valor_total:
                st.warning(f"Atenção: A soma dos pesos ({soma_pesos:.2f}) é diferente do valor total da prova ({valor_total:.2f}).")
            
            for index, row in edited_pesos.iterrows():
                pesos[row["Questão"]] = row["Valor"]

        # 3. Botão para Processar Correção
        if st.button("Gerar Lista de Classe"):
            try:
                # Padronização do Gabarito
                g_quest = find_col(gabarito, ["questão", "questao"])
                g_resp = find_col(gabarito, ["resposta"])
                
                # Criar dicionário de gabarito para busca rápida
                dict_gabarito = dict(zip(gabarito[g_quest].astype(str), gabarito[g_resp].astype(str).str.upper()))

                # Processamento das Notas
                lista_notas = []
                r_nome = find_col(resp, ["nome"])
                r_turma = find_col(resp, ["turma"])

                for index, row in resp.iterrows():
                    nota_aluno = 0.0
                    acertos = 0
                    
                    for q in qcols:
                        resp_aluno = str(row[q]).upper().strip()
                        resp_certa = dict_gabarito.get(str(q))
                        
                        if resp_aluno == resp_certa:
                            nota_aluno += pesos[q]
                            acertos += 1
                    
                    lista_notas.append({
                        "Nome": row[r_nome],
                        "Turma": row[r_turma],
                        "Acertos": acertos,
                        "Nota": round(nota_aluno, 2)
                    })

                df_final = pd.DataFrame(lista_notas)
                
                st.divider()
                st.subheader("📋 Lista de Classe")
                st.dataframe(df_final.sort_values("Nome"), use_container_width=True, hide_index=True)
                
                # Opção de baixar a lista
                st.download_button("Baixar Lista de Notas", 
                                 df_final.to_csv(index=False).encode('utf-8'),
                                 "notas_classe.csv", "text/csv")
                
            except Exception as e:
                st.error(f"Erro na correção: {e}")
    else:
        st.error("O arquivo precisa conter as guias 'Gabarito' e 'RespAluno'.")
