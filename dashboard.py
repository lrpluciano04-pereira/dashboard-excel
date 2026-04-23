import streamlit as st
import pandas as pd
import re
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Dashboard Educacional Pro", page_icon="📊", layout="wide")

# --- INICIALIZAÇÃO DO STATE (Evita o erro de chave inexistente) ---
if 'df_final' not in st.session_state:
    st.session_state['df_final'] = None
if 'dados_questoes' not in st.session_state:
    st.session_state['dados_questoes'] = []
if 'distratores' not in st.session_state:
    st.session_state['distratores'] = []

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

def extrair_serie(turma):
    turma_str = str(turma)
    match = re.search(r'(\d+º?\s?(?:Ano|Série|ano|serie))', turma_str)
    if match:
        return match.group(1).title()
    return turma_str[:6]

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
        c_nome = find_col(df_resp, ["nome"])
        c_turma = find_col(df_resp, ["turma"])
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
            dict_gaba = dict(zip(df_gabarito[g_quest].astype(str).str.strip(), 
                                 df_gabarito[g_resp].astype(str).str.upper().str.strip()))

            lista_final = []
            dados_questoes = []
            distratores = []

            for _, row in df_resp.iterrows():
                nota_aluno = 0.0
                acertos_aluno = 0
                for q in qcols:
                    q_str = str(q).strip()
                    resp_aluno = str(row[q]).strip().upper() if pd.notna(row[q]) else "N/A"
                    resp_certa = dict_gaba.get(q_str)
                    
                    acertou = 1 if (resp_aluno == resp_certa and resp_certa is not None) else 0
                    if acertou:
                        nota_aluno += valores_questoes.get(q_str, 0.0)
                        acertos_aluno += 1
                    
                    dados_questoes.append({"Questão": q_str, "Acerto": acertou})
                    distratores.append({"Questão": q_str, "Opção": resp_aluno})

                lista_final.append({
                    "Turma": str(row[c_turma]) if c_turma else "N/A",
                    "Nome": str(row[c_nome]) if c_nome else "Sem Nome",
                    "Acertos": int(acertos_aluno),
                    "Nota Final": float(nota_aluno)
                })

            st.session_state['df_final'] = pd.DataFrame(lista_final)
            st.session_state['dados_questoes'] = dados_questoes
            st.session_state['distratores'] = distratores

        # --- EXIBIÇÃO ---
        if st.session_state['df_final'] is not None:
            df_final = st.session_state['df_final']
            df_final["Série"] = df_final["Turma"].apply(extrair_serie)
            
            st.divider()
            tab1, tab2, tab3, tab4 = st.tabs(["📋 Lista de Notas", "📈 Médias Gerais", "🎯 Acertos por Item", "🔍 Análise de Alternativas"])

            with tab1:
                st.subheader("Filtros de Pesquisa")
                f_col1, f_col2 = st.columns(2)
                turmas_disponiveis = ["Todas"] + sorted(df_final["Turma"].unique().tolist())
                turma_sel = f_col1.selectbox("Selecione a Turma", turmas_disponiveis)
                df_temp = df_final[df_final["Turma"] == turma_sel] if turma_sel != "Todas" else df_final
                nomes_disp = ["Todos os Alunos"] + sorted(df_temp["Nome"].unique().tolist())
                aluno_sel = f_col2.selectbox("Selecione o Aluno", nomes_disp)
                df_filt = df_temp[df_temp["Nome"] == aluno_sel] if aluno_sel != "Todos os Alunos" else df_temp

                st.dataframe(df_filt[["Turma", "Nome", "Acertos", "Nota Final"]], use_container_width=True, hide_index=True,
                            column_config={
                                "Acertos": st.column_config.NumberColumn(format="%d"),
                                "Nota Final": st.column_config.NumberColumn(format="%.2f")
                            })
                st.markdown("<style>[data-testid='stDataFrame'] td, [data-testid='stDataFrame'] th {text-align: center !important;}</style>", unsafe_allow_html=True)

            with tab2:
                col_a, col_b = st.columns(2)
                with col_a:
                    df_serie = df_final.groupby("Série")["Nota Final"].mean().reset_index()
                    st.plotly_chart(px.bar(df_serie, x="Série", y="Nota Final", text_auto='.2f', title="Média por Série", range_y=[0, valor_total]), use_container_width=True)
                with col_b:
                    df_turma_m = df_final.groupby("Turma")["Nota Final"].mean().reset_index()
                    st.plotly_chart(px.bar(df_turma_m, x="Turma", y="Nota Final", text_auto='.2f', title="Média por Turma", range_y=[0, valor_total]), use_container_width=True)

            with tab3:
                df_q = pd.DataFrame(st.session_state['dados_questoes'])
                df_an = df_q.groupby("Questão")["Acerto"].mean().reset_index()
                df_an["% Acerto"] = df_an["Acerto"] * 100
                df_an["Questão_Num"] = pd.to_numeric(df_an["Questão"])
                df_an = df_an.sort_values("Questão_Num")
                fig = px.bar(df_an, x="Questão", y="% Acerto", text="% Acerto", color="% Acerto", color_continuous_scale="RdYlGn", range_y=[0, 115])
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

            with tab4:
                st.subheader("Análise Qualitativa de Erros")
                df_d = pd.DataFrame(st.session_state['distratores'])
                df_d["Questão_Num"] = pd.to_numeric(df_d["Questão"])
                df_d = df_d.sort_values(["Questão_Num", "Opção"])
                
                fig_dist = px.histogram(df_d, x="Questão", color="Opção", barnorm="percent", 
                                       title="Distribuição de Respostas por Questão",
                                       category_orders={"Questão": sorted(df_d["Questão"].unique(), key=int)},
                                       color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_dist, use_container_width=True)
                st.info("💡 Este gráfico ajuda a identificar 'padrões de erro'. Se muitos alunos marcam a mesma opção incorreta, há uma falha conceitual comum.")

    except Exception as e:
        st.error(f"Erro detectado: {e}")
