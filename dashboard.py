import streamlit as st
import pandas as pd
import re
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Dashboard Educacional Pro", page_icon="📊", layout="wide")

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
        df.to_excel(writer, index=False, sheet_name="Notas_Finais")
    bio.seek(0)
    return bio.getvalue()

# --- INTERFACE ---

st.title("📊 Sistema Inteligente de Avaliação")

file = st.file_uploader("Suba a planilha com as guias 'Gabarito' e 'RespAluno'", type=["xlsx"])

if file:
    try:
        xls = pd.ExcelFile(file)
        if "Gabarito" not in xls.sheet_names or "RespAluno" not in xls.sheet_names:
            st.error("⚠️ Erro: O arquivo precisa ter as abas chamadas 'Gabarito' e 'RespAluno'.")
            st.stop()

        df_gabarito = pd.read_excel(file, sheet_name="Gabarito")
        df_resp = pd.read_excel(file, sheet_name="RespAluno")

        qcols = question_cols(df_resp)
        num_questoes = len(qcols)
        
        # Localização dinâmica das colunas
        c_nome = find_col(df_resp, ["nome"])
        c_turma = find_col(df_resp, ["turma"])
        c_serie = find_col(df_resp, ["série", "serie"]) # Nova coluna oficial
        
        g_quest = find_col(df_gabarito, ["questão", "questao"])
        g_resp = find_col(df_gabarito, ["resposta"])

        # --- SIDEBAR ---
        st.sidebar.header("⚙️ Configurações da Prova")
        valor_total = st.sidebar.number_input("Valor total da prova", min_value=0.0, value=10.0, step=0.5)
        metodo = st.sidebar.radio("Atribuição de Valores:", ["Dividir igualmente", "Valor por questão"])

        valores_questoes = {}
        if metodo == "Dividir igualmente":
            v_unit = valor_total / num_questoes if num_questoes > 0 else 0
            for q in qcols:
                valores_questoes[str(q).strip()] = v_unit
        else:
            st.write("### 🖋️ Defina o valor de cada questão")
            df_init_v = pd.DataFrame({"Questão": [str(q).strip() for q in qcols], "Valor": [0.0]*num_questoes})
            editado = st.data_editor(df_init_v, hide_index=True, use_container_width=True)
            for _, row in editado.iterrows():
                valores_questoes[str(row["Questão"]).strip()] = float(row["Valor"])

        # --- PROCESSAMENTO ---
        if st.button("🚀 Calcular Notas e Gerar Dashboard"):
            dict_gaba = {str(k).strip(): str(v).strip().upper() 
                         for k, v in zip(df_gabarito[g_quest], df_gabarito[g_resp])}

            lista_final = []
            dados_questoes = []
            distratores = []

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
                    
                    dados_questoes.append({"Questão": q_str, "Acerto": acertou})
                    distratores.append({"Questão": q_str, "Opção": resp_aluno})

                lista_final.append({
                    "Série": str(row[c_serie]) if c_serie else "N/A", # Pega direto da planilha
                    "Turma": str(row[c_turma]) if c_turma else "N/A",
                    "Nome": str(row[c_nome]) if c_nome else "Sem Nome",
                    "Acertos": int(acertos_aluno),
                    "Nota Final": round(float(nota_aluno), 2)
                })

            st.session_state['df_final'] = pd.DataFrame(lista_final)
            st.session_state['dados_questoes'] = dados_questoes
            st.session_state['distratores'] = distratores
            st.session_state['dict_gaba'] = dict_gaba

        if 'df_final' in st.session_state:
            df_final = st.session_state['df_final']
            
            st.divider()
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Média Geral", f"{df_final['Nota Final'].mean():.2f}")
            m2.metric("Aproveitamento", f"{(df_final['Acertos'].sum()/(len(df_final)*num_questoes)*100):.1f}%")
            m3.metric("Maior Nota", f"{df_final['Nota Final'].max():.2f}")
            m4.metric("Total Alunos", len(df_final))

            tab1, tab2, tab3, tab4 = st.tabs(["📋 Lista de Notas", "📈 Médias Gerais", "🎯 Análise por Item", "🔍 Análise de Alternativas"])

            with tab1:
                st.subheader("Filtros de Pesquisa")
                f_col1, f_col2 = st.columns(2)
                turmas_disponiveis = ["Todas"] + sorted(df_final["Turma"].unique().tolist())
                turma_selecionada = f_col1.selectbox("1. Selecione a Turma", turmas_disponiveis)
                df_temp = df_final.copy()
                if turma_selecionada != "Todas":
                    df_temp = df_temp[df_temp["Turma"] == turma_selecionada]
                nomes_disponiveis = ["Todos os Alunos"] + sorted(df_temp["Nome"].unique().tolist())
                aluno_selecionado = f_col2.selectbox("2. Selecione o Aluno", nomes_disponiveis)
                df_filtrado = df_temp.copy()
                if aluno_selecionado != "Todos os Alunos":
                    df_filtrado = df_filtrado[df_filtrado["Nome"] == aluno_selecionado]
                df_ordenado = df_filtrado.sort_values(by=["Série", "Turma", "Nome"])
                
                st.dataframe(
                    df_ordenado[["Série", "Turma", "Nome", "Acertos", "Nota Final"]], 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={"Nota Final": st.column_config.NumberColumn("Nota Final", format="%.2f")}
                )
                st.download_button("📥 Baixar Planilha Filtrada", data=excel_bytes(df_ordenado), file_name=f"Notas.xlsx")

            with tab2:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader("Média por Série")
                    # Agrupamento usando a coluna oficial "Série"
                    df_serie_media = df_final.groupby("Série")["Nota Final"].mean().reset_index()
                    fig_serie = px.bar(df_serie_media, x="Série", y="Nota Final", text_auto='.2f', 
                                       color_discrete_sequence=["#007BFF"], range_y=[0, valor_total])
                    fig_serie.update_layout(showlegend=False)
                    st.plotly_chart(fig_serie, use_container_width=True)
                with col_b:
                    st.subheader("Média por Turma")
                    df_turma_m = df_final.groupby("Turma")["Nota Final"].mean().reset_index()
                    fig_turma = px.bar(df_turma_m, x="Turma", y="Nota Final", text_auto='.2f', color="Turma", range_y=[0, valor_total])
                    st.plotly_chart(fig_turma, use_container_width=True)

            with tab3:
                st.subheader("Percentual de Acerto por Questão")
                df_q = pd.DataFrame(st.session_state['dados_questoes'])
                df_analise_q = df_q.groupby("Questão")["Acerto"].mean().reset_index()
                df_analise_q["% Acerto"] = df_analise_q["Acerto"] * 100
                df_analise_q["Questão_Num"] = pd.to_numeric(df_analise_q["Questão"])
                df_analise_q = df_analise_q.sort_values("Questão_Num")
                fig_q = px.bar(df_analise_q, x="Questão", y="% Acerto", color="% Acerto", text="% Acerto", color_continuous_scale="RdYlGn", range_y=[0, 115])
                fig_q.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_q.add_hline(y=50, line_dash="dot", line_color="red")
                st.plotly_chart(fig_q, use_container_width=True)

            with tab4:
                st.subheader("Detalhamento por Alternativas")
                df_dist = pd.DataFrame(st.session_state['distratores'])
                questoes_disponiveis = sorted(df_dist["Questão"].unique(), key=lambda x: int(re.sub(r'\D', '', x)) if re.sub(r'\D', '', x) else 0)
                
                selecao_questoes = st.pills("Selecione as questões:", options=questoes_disponiveis, selection_mode="multi", default=questoes_disponiveis[0:1])

                if selecao_questoes:
                    df_q_metrics = pd.DataFrame(st.session_state['dados_questoes'])
                    cols = st.columns(len(selecao_questoes))
                    for i, q_esc in enumerate(selecao_questoes):
                        gab = st.session_state['dict_gaba'].get(str(q_esc).strip(), "N/D")
                        acerto_val = df_q_metrics[df_q_metrics["Questão"] == str(q_esc)]["Acerto"].mean() * 100
                        with cols[i]:
                            st.metric(label=f"Questão {q_esc}", value=f"Gabarito: {gab}")
                            st.caption(f"🎯 Acerto: {acerto_val:.1f}%")

                    df_f = df_dist[df_dist["Questão"].isin(selecao_questoes)].copy()
                    df_f = df_f[df_f["Opção"].isin(['A', 'B', 'C', 'D', 'E'])]
                    
                    if not df_f.empty:
                        df_counts = df_f.groupby(['Questão', 'Opção']).size().reset_index(name='Qtd')
                        df_counts['%'] = df_counts.groupby('Questão')['Qtd'].transform(lambda x: (x / x.sum()) * 100)
                        
                        fig_dist = px.bar(df_counts, x="Questão", y="%", color="Opção", barmode="group", text_auto='.1f',
                                         category_orders={"Opção": ['A', 'B', 'C', 'D', 'E']}, range_y=[0, 110])
                        fig_dist.update_traces(texttemplate='%{y:.1f}%', textposition='outside')
                        st.plotly_chart(fig_dist, use_container_width=True)
                    else:
                        st.warning("Nenhuma resposta válida (A-E) encontrada para estas questões.")

    except Exception as e:
        st.error(f"Erro detectado: {e}. Verifique se a aba 'RespAluno' possui a coluna 'Série'.")
