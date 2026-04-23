import streamlit as st
import pandas as pd
import re
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Dashboard Educacional Pro", page_icon="📊", layout="wide")

# --- INICIALIZAÇÃO DO STATE ---
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

def extrair_serie(turma):
    turma_str = str(turma)
    match = re.search(r'(\d+º?\s?(?:Ano|Série|ano|serie))', turma_str, re.IGNORECASE)
    if match:
        return match.group(1).strip().title()
    return turma_str[:5].strip().title()

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
        st.sidebar.header("⚙️ Configurações")
        valor_total = st.sidebar.number_input("Valor total da prova", min_value=0.0, value=10.0, step=0.5)
        metodo = st.sidebar.radio("Atribuição de Valores:", ["Dividir igualmente", "Valor por questão"])

        valores_questoes = {}
        if metodo == "Dividir igualmente":
            v_unit = valor_total / num_questoes if num_questoes > 0 else 0
            for q in qcols:
                valores_questoes[str(q).strip()] = v_unit
        else:
            df_init_v = pd.DataFrame({"Questão": [str(q).strip() for q in qcols], "Valor": [0.0]*num_questoes})
            editado = st.sidebar.data_editor(df_init_v, hide_index=True)
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
            df_geral = st.session_state['df_final'].copy()
            df_geral["Série"] = df_geral["Turma"].apply(extrair_serie)
            
            st.divider()
            tab1, tab2, tab3, tab4 = st.tabs(["📋 Lista de Notas", "📈 Médias Gerais", "🎯 Acertos por Item", "🔍 Análise de Alternativas"])

            with tab1:
                f_col1, f_col2 = st.columns(2)
                turmas_disp = ["Todas"] + sorted(df_geral["Turma"].unique().tolist())
                turma_sel = f_col1.selectbox("Filtrar Turma", turmas_disp)
                df_tab1 = df_geral[df_geral["Turma"] == turma_sel] if turma_sel != "Todas" else df_geral
                nomes_disp = ["Todos os Alunos"] + sorted(df_tab1["Nome"].unique().tolist())
                aluno_sel = f_col2.selectbox("Filtrar Aluno", nomes_disp)
                df_filt = df_tab1[df_tab1["Nome"] == aluno_sel] if aluno_sel != "Todos os Alunos" else df_tab1
                st.dataframe(df_filt[["Turma", "Nome", "Acertos", "Nota Final"]], use_container_width=True, hide_index=True)

            with tab2:
                c1, c2 = st.columns(2)
                with c1:
                    st.plotly_chart(px.bar(df_geral.groupby("Série", as_index=False)["Nota Final"].mean(), x="Série", y="Nota Final", color="Série", range_y=[0, valor_total], title="Média por Série"), use_container_width=True)
                with c2:
                    st.plotly_chart(px.bar(df_geral.groupby("Turma", as_index=False)["Nota Final"].mean(), x="Turma", y="Nota Final", color="Turma", range_y=[0, valor_total], title="Média por Turma"), use_container_width=True)

            with tab3:
                df_q = pd.DataFrame(st.session_state['dados_questoes'])
                df_an = df_q.groupby("Questão")["Acerto"].mean().reset_index()
                df_an["% Acerto"] = df_an["Acerto"] * 100
                df_an = df_an.sort_values(by="Questão", key=lambda x: x.astype(int))
                fig_ac = px.bar(df_an, x="Questão", y="% Acerto", text_auto='.1f', color="% Acerto", color_continuous_scale="RdYlGn", range_y=[0, 115])
                st.plotly_chart(fig_ac, use_container_width=True)

            with tab4:
                st.markdown("### 🔲 Segmentação de Questões")
                df_d = pd.DataFrame(st.session_state['distratores'])
                opcoes_validas = ['A', 'B', 'C', 'D', 'E']
                df_d = df_d[df_d['Opção'].isin(opcoes_validas)]
                questoes_disp = sorted(df_d["Questão"].unique(), key=int)
                
                # SEGMENTAÇÃO ESTILO EXCEL (BOTOES CLICAVEIS)
                selecao_pills = st.pills(
                    "Selecione as questões para detalhamento:",
                    options=questoes_disp,
                    selection_mode="multi",
                    default=questoes_disp[0:5] if len(questoes_disp) > 5 else questoes_disp
                )
                
                if selecao_pills:
                    df_f = df_d[df_d['Questão'].isin(selecao_pills)]
                    df_counts = df_f.groupby(['Questão', 'Opção']).size().reset_index(name='count')
                    df_total = df_f.groupby('Questão').size().reset_index(name='total')
                    df_res = pd.merge(df_counts, df_total, on='Questão')
                    df_res['%'] = (df_res['count'] / df_res['total']) * 100
                    df_res = df_res.sort_values(by="Questão", key=lambda x: x.astype(int))

                    fig = px.bar(df_res, x="Questão", y="%", color="Opção", barmode="group",
                                 category_orders={"Opção": opcoes_validas},
                                 text_auto='.1f', range_y=[0, 110],
                                 color_discrete_sequence=px.colors.qualitative.Bold)
                    fig.update_layout(yaxis_title="Percentual (%)")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Clique nos botões acima para selecionar as questões.")

    except Exception as e:
        st.error(f"Erro detectado: {e}")
