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
if 'dict_gaba' not in st.session_state:
    st.session_state['dict_gaba'] = {}

# --- FUNÇÕES DE SUPORTE ---

def clean_q_name(name):
    """Extrai apenas os dígitos de uma string. Ex: 'Questão 01' -> '1'"""
    nums = re.findall(r'\d+', str(name))
    return str(int(nums[0])) if nums else str(name).strip()

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
        if s.isdigit() or re.fullmatch(r'\d+', s) or "quest" in s.lower():
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

file = st.file_uploader("Suba a planilha (Gabarito e RespAluno)", type=["xlsx"])

if file:
    try:
        xls = pd.ExcelFile(file)
        if "Gabarito" not in xls.sheet_names or "RespAluno" not in xls.sheet_names:
            st.error("⚠️ Erro: As abas devem ser 'Gabarito' e 'RespAluno'.")
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
                valores_questoes[clean_q_name(q)] = v_unit
        else:
            df_init_v = pd.DataFrame({"Questão": [str(q).strip() for q in qcols], "Valor": [0.0]*num_questoes})
            editado = st.sidebar.data_editor(df_init_v, hide_index=True)
            for _, row in editado.iterrows():
                valores_questoes[clean_q_name(row["Questão"])] = float(row["Valor"])

        # --- PROCESSAMENTO ---
        if st.button("🚀 Calcular Notas e Gerar Dashboard"):
            # NORMALIZAÇÃO DO GABARITO (Chave limpa)
            dict_gaba = {clean_q_name(k): str(v).strip().upper() 
                         for k, v in zip(df_gabarito[g_quest], df_gabarito[g_resp])}
            
            st.session_state['dict_gaba'] = dict_gaba

            lista_final = []
            dados_questoes = []
            distratores = []

            for _, row in df_resp.iterrows():
                nota_aluno = 0.0
                acertos_aluno = 0
                for q in qcols:
                    q_limpo = clean_q_name(q)
                    resp_aluno = str(row[q]).strip().upper() if pd.notna(row[q]) else "N/A"
                    resp_certa = dict_gaba.get(q_limpo)
                    
                    acertou = 1 if (resp_aluno == resp_certa and resp_certa is not None) else 0
                    if acertou:
                        nota_aluno += valores_questoes.get(q_limpo, 0.0)
                        acertos_aluno += 1
                    
                    dados_questoes.append({"Questão": q_limpo, "Acerto": acertou})
                    distratores.append({"Questão": q_limpo, "Opção": resp_aluno})

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

            # ... (Abas 1, 2 e 3 permanecem iguais) ...
            with tab1:
                st.dataframe(df_geral, use_container_width=True, hide_index=True)
            with tab2:
                st.plotly_chart(px.bar(df_geral.groupby("Série", as_index=False)["Nota Final"].mean(), x="Série", y="Nota Final"), use_container_width=True)
            with tab3:
                df_q_plot = pd.DataFrame(st.session_state['dados_questoes']).groupby("Questão")["Acerto"].mean().reset_index()
                df_q_plot["%"] = df_q_plot["Acerto"] * 100
                st.plotly_chart(px.bar(df_q_plot, x="Questão", y="%"), use_container_width=True)

            with tab4:
                st.markdown("### 🔲 Segmentação de Questões")
                df_d = pd.DataFrame(st.session_state['distratores'])
                opcoes_validas = ['A', 'B', 'C', 'D', 'E']
                df_d = df_d[df_d['Opção'].isin(opcoes_validas)]
                
                # Ordenação numérica real
                questoes_disp = sorted(df_d["Questão"].unique(), key=int)
                
                selecao_pills = st.pills(
                    "Escolha as questões:",
                    options=questoes_disp,
                    selection_mode="multi",
                    default=questoes_disp[0:3] if len(questoes_disp) > 3 else questoes_disp
                )
                
                if selecao_pills:
                    df_q_metrics = pd.DataFrame(st.session_state['dados_questoes'])
                    
                    # CARDS DE INFORMAÇÃO CORRIGIDOS
                    cols_info = st.columns(len(selecao_pills))
                    for i, q_nome in enumerate(selecao_pills):
                        q_key = str(q_nome)
                        # Busca no dicionário global de gabarito salvo no state
                        gabarito_correto = st.session_state['dict_gaba'].get(q_key, "N/D")
                        
                        perc_acerto = df_q_metrics[df_q_metrics["Questão"] == q_key]["Acerto"].mean() * 100
                        
                        with cols_info[i]:
                            st.metric(label=f"Questão {q_key}", value=f"Gabarito: {gabarito_correto}")
                            st.caption(f"🎯 Taxa de Acerto: {perc_acerto:.1f}%")

                    # Gráfico
                    df_f = df_d[df_d['Questão'].isin(selecao_pills)]
                    df_res = df_f.groupby(['Questão', 'Opção']).size().reset_index(name='n')
                    df_res['%'] = df_res.groupby('Questão')['n'].transform(lambda x: (x/x.sum())*100)
                    
                    fig = px.bar(df_res, x="Questão", y="%", color="Opção", barmode="group",
                                 text_auto='.1f', range_y=[0, 110],
                                 category_orders={"Opção": opcoes_validas},
                                 color_discrete_sequence=px.colors.qualitative.Bold)
                    st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Erro: {e}")
