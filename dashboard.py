import streamlit as st
import pandas as pd
import re
import plotly.express as px
from io import BytesIO
import google.generativeai as genai  # NOVO: Importação da IA

st.set_page_config(page_title="Dashboard Educacional Pro", page_icon="📊", layout="wide")

# NOVO: Configuração da IA usando o Secret que você salvou
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Chave API não configurada nos Secrets do Streamlit.")

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

# --- APRESENTAÇÃO E EXPLICAÇÃO ---
st.title("📊 Sistema Inteligente de Avaliação")

with st.expander("🎓 Sobre este Projeto (TCC / Institucional)", expanded=True):
    col_foto, col_texto = st.columns([1, 4])
    with col_texto:
        st.markdown(f"""
        ### Bem-vindo ao meu projeto de TCC!
        Este sistema foi desenvolvido como parte do requisito para conclusão do curso de **Uso Educacional da Internet** na faculdade **UFLA - Universidade Federal de Lavras**. 
        
        **Desenvolvedor:** Luciano Rodrigues Pereira  
        **Objetivo:** Automatizar a correção de avaliações e fornecer uma análise pedagógica detalhada através de dashboards.
        """)
    
    st.info("💡 **Como utilizar:** Prepare um arquivo Excel com duas abas: 'Gabarito' e 'RespAluno'.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        **1. Aba Gabarito:**
        - Coluna `Questão`: Número da questão.
        - Coluna `Resposta`: Letra correta (A-E).
        """)
    with c2:
        st.markdown("""
        **2. Aba RespAluno:**
        - Colunas: `Nome`, `Série`, `Turma`.
        - Colunas numeradas (`1`, `2`, `3`...): Respostas de cada aluno.
        """)

st.divider()

# --- INTERFACE DE UPLOAD ---
file = st.file_uploader("Suba sua planilha preenchida aqui:", type=["xlsx"])

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
        c_serie = find_col(df_resp, ["série", "serie"])
        
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
                    "Série": str(row[c_serie]) if c_serie else "N/A",
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

            # ATUALIZADO: Adicionada a tab5 para IA
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Notas", "📈 Médias", "🎯 Itens", "🔍 Alternativas", "🤖 Relatório IA"])

            with tab1:
                st.subheader("Filtros de Pesquisa")
                f_col1, f_col2 = st.columns(2)
                turmas_disponiveis = ["Todas"] + sorted(df_final["Turma"].unique().tolist())
                turma_selecionada = f_col1.selectbox("Selecione a Turma", turmas_disponiveis)
                df_temp = df_final.copy()
                if turma_selecionada != "Todas":
                    df_temp = df_temp[df_temp["Turma"] == turma_selecionada]
                nomes_disponiveis = ["Todos os Alunos"] + sorted(df_temp["Nome"].unique().tolist())
                aluno_selecionado = f_col2.selectbox("Selecione o Aluno", nomes_disponiveis)
                df_filtrado = df_temp.copy()
                if aluno_selecionado != "Todos os Alunos":
                    df_filtrado = df_filtrado[df_filtrado["Nome"] == aluno_selecionado]
                
                st.dataframe(df_filtrado[["Série", "Turma", "Nome", "Acertos", "Nota Final"]], use_container_width=True, hide_index=True)

            with tab2:
                col_a, col_b = st.columns(2)
                with col_a:
                    df_serie_media = df_final.groupby("Série")["Nota Final"].mean().reset_index()
                    fig_serie = px.bar(df_serie_media, x="Série", y="Nota Final", text_auto='.2f', color="Série")
                    st.plotly_chart(fig_serie, use_container_width=True)
                with col_b:
                    df_turma_m = df_final.groupby("Turma")["Nota Final"].mean().reset_index()
                    fig_turma = px.bar(df_turma_m, x="Turma", y="Nota Final", text_auto='.2f', color="Turma")
                    st.plotly_chart(fig_turma, use_container_width=True)

            with tab3:
                df_q = pd.DataFrame(st.session_state['dados_questoes'])
                df_analise_q = df_q.groupby("Questão")["Acerto"].mean().reset_index()
                df_analise_q["% Acerto"] = df_analise_q["Acerto"] * 100
                fig_q = px.bar(df_analise_q, x="Questão", y="% Acerto", color="Questão", text_auto='.1f')
                st.plotly_chart(fig_q, use_container_width=True)

            with tab4:
                st.write("Análise detalhada de alternativas (conforme original).")
            
            # NOVO: Conteúdo da Tab de IA
            with tab5:
                st.subheader("🤖 IA - Relatório Pedagógico")
                st.write("Clique abaixo para que a IA analise os dados e gere um parecer para a gestão.")
                
                if st.button("Gerar Relatório Estratégico"):
                    df_q = pd.DataFrame(st.session_state['dados_questoes'])
                    df_analise_q = df_q.groupby("Questão")["Acerto"].mean().reset_index()
                    piores = df_analise_q.sort_values(by="Acerto").head(3)
                    piores_lista = piores["Questão"].tolist()
                    
                    prompt = f"""
                    Atue como um coordenador pedagógico. Analise os resultados desta prova:
                    - Média Final da Turma: {df_final['Nota Final'].mean():.2f}
                    - Taxa de Acerto Geral: {(df_final['Acertos'].sum()/(len(df_final)*num_questoes)*100):.1f}%
                    - Questões Críticas (maiores erros): {piores_lista}
                    
                    Escreva um relatório profissional para a direção sugerindo ações de reforço.
                    """
                    
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        with st.spinner("IA processando dados..."):
                            response = model.generate_content(prompt)
                            st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Erro ao acessar a IA: {e}")

    except Exception as e:
        st.error(f"Erro detectado: {e}")
