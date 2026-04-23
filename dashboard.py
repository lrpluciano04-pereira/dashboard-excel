import streamlit as st
import pandas as pd
import re
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Dashboard Educacional Pro", page_icon="📊", layout="wide")

# --- FUNÇÃO PARA GERAR ARQUIVO DE MODELO ---
def gerar_modelo_excel():
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_gab = pd.DataFrame({"Questão": [1, 2, 3, 4, 5], "Resposta": ["A", "B", "C", "D", "E"]})
        df_gab.to_excel(writer, sheet_name='Gabarito', index=False)
        df_resp = pd.DataFrame({
            "Nome": ["Aluno Exemplo 1", "Aluno Exemplo 2"],
            "Série": ["1º Ano", "1º Ano"],
            "Turma": ["Turma A", "Turma B"],
            "1": ["A", "B"], "2": ["B", "B"], "3": ["C", "E"], "4": ["D", "D"], "5": ["E", "A"]
        })
        df_resp.to_excel(writer, sheet_name='RespAluno', index=False)
    return output.getvalue()

# --- FUNÇÕES DE SUPORTE ---
def find_col(df, options):
    for col in df.columns:
        nome = str(col).lower().strip()
        for opt in options:
            if opt in nome: return col
    return None

def question_cols(df):
    return [c for c in df.columns if str(c).strip().isdigit() or re.fullmatch(r'\d+', str(c).strip())]

def excel_bytes(df):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Notas_Finais")
    bio.seek(0)
    return bio.getvalue()

# --- INTERFACE ---
st.title("📊 Sistema Inteligente de Avaliação")

with st.expander("🎓 Sobre este Projeto (TCC / Institucional)", expanded=True):
    st.markdown("### Desenvolvedor: Luciano Rodrigues Pereira | UFLA")
    st.download_button(label="📥 Baixar Modelo Excel", data=gerar_modelo_excel(), file_name="modelo.xlsx")

file = st.file_uploader("Suba sua planilha:", type=["xlsx"])

if file:
    try:
        xls = pd.ExcelFile(file)
        df_gabarito = pd.read_excel(file, sheet_name="Gabarito")
        df_resp = pd.read_excel(file, sheet_name="RespAluno")

        qcols = question_cols(df_resp)
        c_nome = find_col(df_resp, ["nome"])
        c_turma = find_col(df_resp, ["turma"])
        c_serie = find_col(df_resp, ["série", "serie"])
        g_quest = find_col(df_gabarito, ["questão", "questao"])
        g_resp = find_col(df_gabarito, ["resposta"])

        st.sidebar.header("⚙️ Configurações")
        valor_total = st.sidebar.number_input("Valor total", value=10.0)
        
        if st.button("🚀 Calcular Notas"):
            dict_gaba = {str(k).strip(): str(v).strip().upper() for k, v in zip(df_gabarito[g_quest], df_gabarito[g_resp])}
            lista_final, dados_questoes, distratores = [], [], []

            for _, row in df_resp.iterrows():
                nota_aluno, acertos = 0.0, 0
                for q in qcols:
                    q_str = str(q).strip()
                    resp_aluno = str(row[q]).strip().upper() if pd.notna(row[q]) else "N/A"
                    resp_certa = dict_gaba.get(q_str)
                    acertou = 1 if (resp_aluno == resp_certa) else 0
                    if acertou:
                        nota_aluno += (valor_total / len(qcols))
                        acertos += 1
                    dados_questoes.append({"Questão": q_str, "Acerto": acertou})
                    distratores.append({"Questão": q_str, "Opção": resp_aluno})

                lista_final.append({
                    "Série": str(row[c_serie]) if c_serie else "N/A",
                    "Turma": str(row[c_turma]) if c_turma else "N/A",
                    "Nome": str(row[c_nome]) if c_nome else "Sem Nome",
                    "Acertos": acertos, "Nota Final": round(nota_aluno, 2)
                })

            st.session_state.update({'df_final': pd.DataFrame(lista_final), 'dados_questoes': dados_questoes, 'distratores': distratores, 'dict_gaba': dict_gaba})

        if 'df_final' in st.session_state:
            tab1, tab2, tab3, tab4 = st.tabs(["📋 Lista", "📈 Médias", "🎯 Acertos", "🔍 Alternativas"])

            with tab2:
                c_a, c_b = st.columns(2)
                df_f = st.session_state['df_final']
                with c_a:
                    fig_s = px.bar(df_f.groupby("Série")["Nota Final"].mean().reset_index(), x="Série", y="Nota Final", color="Série")
                    st.plotly_chart(fig_s, use_container_width=True)
                with c_b:
                    fig_t = px.bar(df_f.groupby("Turma")["Nota Final"].mean().reset_index(), x="Turma", y="Nota Final", color="Turma")
                    fig_t.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_t, use_container_width=True)

            with tab3:
                df_q = pd.DataFrame(st.session_state['dados_questoes']).groupby("Questão")["Acerto"].mean().reset_index()
                df_q["% Acerto"] = df_q["Acerto"] * 100
                st.plotly_chart(px.bar(df_q, x="Questão", y="% Acerto", color="% Acerto", range_y=[0,100], color_continuous_scale="RdYlGn"), use_container_width=True)

            with tab4:
                st.subheader("Detalhamento por Alternativas")
                df_dist = pd.DataFrame(st.session_state['distratores'])
                questoes = sorted(df_dist["Questão"].unique(), key=lambda x: int(re.sub(r'\D', '', x)) if re.sub(r'\D', '', x) else 0)
                selecao = st.pills("Questões:", options=questoes, selection_mode="multi", default=questoes[0:1])

                if selecao:
                    df_q_metrics = pd.DataFrame(st.session_state['dados_questoes'])
                    cols = st.columns(len(selecao))
                    for i, q_esc in enumerate(selecao):
                        gab = st.session_state['dict_gaba'].get(str(q_esc).strip(), "N/D")
                        with cols[i]: st.metric(f"Questão {q_esc}", f"Gabarito: {gab}")

                    # FILTRO E RECONSTRUÇÃO PARA MOSTRAR A-E SEMPRE
                    df_f = df_dist[df_dist["Questão"].isin(selecao)].copy()
                    df_counts = df_f.groupby(['Questão', 'Opção']).size().reset_index(name='Qtd')
                    
                    # Cálculo de porcentagem
                    total_por_q = df_counts.groupby('Questão')['Qtd'].transform('sum')
                    df_counts['%'] = (df_counts['Qtd'] / total_por_q) * 100

                    fig_dist = px.bar(df_counts, x="Questão", y="%", color="Opção", barmode="group", 
                                     text_auto='.1f', range_y=[0, 110],
                                     category_orders={"Opção": ["A", "B", "C", "D", "E"]}) # Força a ordem
                    
                    # Garante que o eixo X mostre todas as opções de A a E mesmo sem votos
                    fig_dist.update_xaxes(type='category')
                    st.plotly_chart(fig_dist, use_container_width=True)

    except Exception as e: st.error(f"Erro: {e}")
