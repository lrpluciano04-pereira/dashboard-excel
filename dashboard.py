import streamlit as st
import pandas as pd
import re
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Dashboard Educacional Pro", page_icon="📊", layout="wide")

# --- FUNÇÃO PARA GERAR ARQUIVO DE MODELO (AJUSTADO) ---
def gerar_modelo_excel():
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Aba Gabarito: Estrutura clara para o sistema ler
        df_gab = pd.DataFrame({
            "Questão": [str(i) for i in range(1, 11)],
            "Resposta": ["A", "B", "C", "D", "E", "A", "B", "C", "D", "E"]
        })
        df_gab.to_excel(writer, sheet_name='Gabarito', index=False)
        
        # Aba RespAluno: Colunas de identificação + colunas de questões
        dados_resp = {
            "Nome": ["Aluno Exemplo Alpha", "Aluno Exemplo Beta", "Aluno Exemplo Gamma"],
            "Série": ["1º Ano", "1º Ano", "2º Ano"],
            "Turma": ["Turma A", "Turma B", "Turma A"]
        }
        # Adiciona colunas de 1 a 10
        for i in range(1, 11):
            dados_resp[str(i)] = ["A", "B", "C"] if i % 2 == 0 else ["E", "D", "A"]
            
        df_resp = pd.DataFrame(dados_resp)
        df_resp.to_excel(writer, sheet_name='RespAluno', index=False)
    return output.getvalue()

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
    col_texto = st.container()
    with col_texto:
        st.markdown(f"""
        ### Bem-vindo ao meu projeto de TCC!
        Este sistema foi desenvolvido como parte do requisito para conclusão do curso de **Uso Educacional da Internet** na faculdade **UFLA - Universidade Federal de Lavras**. 
        
        **Desenvolvedor:** Luciano Rodrigues Pereira  
        **Objetivo:** Automatizar a correção de avaliações e fornecer uma análise pedagógica detalhada.
        """)
    
    st.info("💡 **Importante:** O arquivo Excel deve conter as abas 'Gabarito' e 'RespAluno'. Use o modelo abaixo.")
    
    st.download_button(
        label="📥 Baixar Arquivo Excel de Modelo",
        data=gerar_modelo_excel(),
        file_name="modelo_avaliacao_tcc.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

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
        st.sidebar.header("⚙️ Configurações")
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

        if st.button("🚀 Calcular Notas e Gerar Dashboard"):
            dict_gaba = {str(k).strip(): str(v).strip().upper() for k, v in zip(df_gabarito[g_quest], df_gabarito[g_resp])}
            lista_final, dados_questoes, distratores = [], [], []

            for _, row in df_resp.iterrows():
                nota_aluno, acertos_aluno = 0.0, 0
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
            
            # Métricas
            col_m = st.columns(4)
            col_m[0].metric("Média Geral", f"{df_final['Nota Final'].mean():.2f}")
            col_m[1].metric("Aproveitamento", f"{(df_final['Acertos'].sum()/(len(df_final)*num_questoes)*100):.1f}%")
            col_m[2].metric("Maior Nota", f"{df_final['Nota Final'].max():.2f}")
            col_m[3].metric("Total Alunos", len(df_final))

            tabs = st.tabs(["📋 Notas", "📈 Médias", "🎯 Itens", "🔍 Alternativas"])

            with tabs[0]:
                st.dataframe(df_final.sort_values(by=["Série", "Turma", "Nome"]), use_container_width=True, hide_index=True)

            with tabs[1]:
                c_a, c_b = st.columns(2)
                with c_a:
                    df_s = df_final.groupby("Série")["Nota Final"].mean().reset_index()
                    fig1 = px.bar(df_s, x="Série", y="Nota Final", color="Série", text_auto='.2f', title="Média por Série")
                    st.plotly_chart(fig1, use_container_width=True)
                with c_b:
                    df_t = df_final.groupby("Turma")["Nota Final"].mean().reset_index()
                    fig2 = px.bar(df_t, x="Turma", y="Nota Final", color="Turma", text_auto='.2f', title="Média por Turma")
                    st.plotly_chart(fig2, use_container_width=True)

            with tabs[2]:
                df_q = pd.DataFrame(st.session_state['dados_questoes'])
                df_q_agg = df_q.groupby("Questão")["Acerto"].mean().reset_index()
                df_q_agg["% Acerto"] = df_q_agg["Acerto"] * 100
                fig3 = px.bar(df_q_agg, x="Questão", y="% Acerto", color="Questão", text_auto='.1f', title="Acerto por Questão")
                st.plotly_chart(fig3, use_container_width=True)

            with tabs[3]:
                df_dist = pd.DataFrame(st.session_state['distratores'])
                df_f = df_dist[df_dist["Opção"].isin(['A', 'B', 'C', 'D', 'E'])]
                if not df_f.empty:
                    df_c = df_f.groupby(['Questão', 'Opção']).size().reset_index(name='Qtd')
                    df_c['%'] = df_c.groupby('Questão')['Qtd'].transform(lambda x: (x / x.sum()) * 100)
                    fig4 = px.bar(df_c, x="Opção", y="%", color="Questão", barmode="group", text_auto='.1f', 
                                  category_orders={"Opção": ['A', 'B', 'C', 'D', 'E']}, title="Distribuição de Alternativas")
                    st.plotly_chart(fig4, use_container_width=True)

    except Exception as e:
        st.error(f"Erro: {e}")
