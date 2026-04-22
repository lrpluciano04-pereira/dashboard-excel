import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import re

st.set_page_config(page_title="Dashboard Educacional", page_icon="📊", layout="wide")

st.markdown("""
<style>
.block-container{padding-top:1.1rem;padding-bottom:2rem;padding-left:2rem;padding-right:2rem;}
.title-box{background:linear-gradient(90deg,#0f172a 0%,#1e293b 100%);padding:1.2rem 1.4rem;border-radius:18px;color:white;margin-bottom:1rem;box-shadow:0 8px 24px rgba(15,23,42,.18);}
.subtitle{opacity:.85;font-size:.95rem;margin-top:.35rem;}
div[data-testid="stMetric"]{background:white;border:1px solid #e5e7eb;padding:14px 16px;border-radius:16px;box-shadow:0 4px 16px rgba(15,23,42,.06);} 
section[data-testid="stSidebar"]{background:#f8fafc;border-right:1px solid #e5e7eb;}
.chart-card{background:white;border:1px solid #e5e7eb;border-radius:18px;padding:1rem 1rem .5rem 1rem;box-shadow:0 4px 18px rgba(15,23,42,.05);margin-bottom:1rem;}
.small-note{font-size:.9rem;color:#475569;}
</style>
""", unsafe_allow_html=True)

def find_col(df, options):
    for col in df.columns:
        nome = str(col).lower().strip()
        for opt in options:
            if opt in nome:
                return col
    return None

def safe_str(s):
    return s.astype(str).fillna("").str.strip()

def natural_key(text):
    parts = re.split(r'(\d+)', str(text))
    return [int(p) if p.isdigit() else p for p in parts]

def excel_bytes(df):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Analise_RespAluno")
    bio.seek(0)
    return bio.getvalue()

def question_cols(df):
    cols = []
    for c in df.columns:
        s = str(c).strip()
        if s.isdigit() or re.fullmatch(r'\d+', s):
            cols.append(c)
    return cols

st.markdown("""
<div class="title-box">
    <h1 style="margin:0;font-size:2rem;">📊 Dashboard Educacional</h1>
    <div class="subtitle">Macro → meso → micro, com análise por prova, disciplina, questão e aluno</div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Arquivos")
    gabarito_file = st.file_uploader("Gabarito", type=["xlsx", "xls"], key="gabarito")
    resp_file = st.file_uploader("RespAluno", type=["xlsx", "xls"], key="respaluno")

if gabarito_file and resp_file:
    try:
        gabarito = pd.read_excel(gabarito_file)
        resp = pd.read_excel(resp_file)
        gabarito.columns = [str(c).strip() for c in gabarito.columns]
        resp.columns = [str(c).strip() for c in resp.columns]

        g_prova = find_col(gabarito, ["nome prova", "prova"])
        g_disc = find_col(gabarito, ["disciplina"])
        g_quest = find_col(gabarito, ["questão", "questao"])
        g_resp = find_col(gabarito, ["resposta"])

        r_prova = find_col(resp, ["nome prova", "prova"])
        r_turma = find_col(resp, ["turma"])
        r_mat = find_col(resp, ["matricula", "matrícula"])
        r_nome = find_col(resp, ["nome"])
        qcols = question_cols(resp)

        if not all([g_prova, g_disc, g_quest, g_resp, r_prova, r_turma, r_mat, r_nome]) or not qcols:
            st.error("Não encontrei todas as colunas necessárias. Verifique os nomes das colunas nas duas planilhas.")
            st.stop()

        gabarito = gabarito[[g_prova, g_disc, g_quest, g_resp]].copy()
        gabarito[g_prova] = safe_str(gabarito[g_prova])
        gabarito[g_disc] = safe_str(gabarito[g_disc])
        gabarito[g_resp] = safe_str(gabarito[g_resp]).str.upper()
        gabarito[g_quest] = pd.to_numeric(gabarito[g_quest], errors="coerce")
        gabarito = gabarito.dropna(subset=[g_quest]).copy()
        gabarito[g_quest] = gabarito[g_quest].astype(int)
        gabarito = gabarito.rename(columns={g_prova: "Nome Prova", g_disc: "Disciplina", g_quest: "Questão", g_resp: "Resposta_Gabarito"})

        resp2 = resp.copy()
        resp2[r_prova] = safe_str(resp2[r_prova])
        resp2[r_turma] = safe_str(resp2[r_turma])
        resp2[r_mat] = safe_str(resp2[r_mat])
        resp2[r_nome] = safe_str(resp2[r_nome])
        for c in qcols:
            resp2[c] = safe_str(resp2[c]).str.upper()

        melted = resp2.melt(id_vars=[r_prova, r_turma, r_mat, r_nome], value_vars=qcols, var_name="Questão", value_name="Resposta_Aluno")
        melted["Questão"] = pd.to_numeric(melted["Questão"], errors="coerce")
        melted = melted.dropna(subset=["Questão"]).copy()
        melted["Questão"] = melted["Questão"].astype(int)
        melted["Resposta_Aluno"] = safe_str(melted["Resposta_Aluno"]).str.upper()
        melted = melted.rename(columns={r_prova: "Nome Prova", r_turma: "Turma", r_mat: "matricula", r_nome: "nome"})
        melted["Nome Prova"] = safe_str(melted["Nome Prova"])

        analise = melted.merge(gabarito, on=["Nome Prova", "Questão"], how="left")
        analise["Correta"] = (safe_str(analise["Resposta_Aluno"]).str.upper() == safe_str(analise["Resposta_Gabarito"]).str.upper()).astype(int)
        analise["Resultado"] = analise["Correta"].map({1: "Certa", 0: "Errada"})
        analise["Acerto%"] = analise["Correta"] * 100

        analise_final = analise[["Nome Prova", "Turma", "matricula", "nome", "Disciplina", "Questão", "Resposta_Aluno", "Resposta_Gabarito", "Correta", "Resultado", "Acerto%"]].copy()
        analise_final["Questão"] = analise_final["Questão"].astype(int)

        provas = sorted(analise_final["Nome Prova"].dropna().astype(str).unique().tolist())
        disciplinas = sorted(analise_final["Disciplina"].dropna().astype(str).unique().tolist())
        turmas = sorted(analise_final["Turma"].dropna().astype(str).unique().tolist(), key=natural_key)
        alunos = sorted(analise_final["nome"].dropna().astype(str).unique().tolist(), key=str.lower)

        st.success("Planilha Analise_RespAluno gerada com sucesso.")
        st.download_button("Baixar Analise_RespAluno.xlsx", data=excel_bytes(analise_final), file_name="Analise_RespAluno.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.sidebar.header("Filtros gerais")
        prova_sel = st.sidebar.selectbox("Nome Prova", ["Todas"] + provas)
        turma_sel = st.sidebar.selectbox("Turma", ["Todas"] + turmas)
        aluno_sel = st.sidebar.selectbox("Aluno", ["Todos"] + alunos)

        df = analise_final.copy()
        if prova_sel != "Todas":
            df = df[df["Nome Prova"].astype(str) == prova_sel]
        if turma_sel != "Todas":
            df = df[df["Turma"].astype(str) == turma_sel]
        if aluno_sel != "Todos":
            df = df[df["nome"].astype(str) == aluno_sel]

        if df.empty:
            st.warning("Sem dados para os filtros selecionados.")
            st.stop()

        multi_prova = len(provas) > 1
        macro = analise_final.groupby("Nome Prova", as_index=False).agg(AcertoMedio=("Correta", "mean"), Alunos=("matricula", "nunique"), Questoes=("Questão", "nunique"))
        macro["Acerto%"] = macro["AcertoMedio"] * 100
        macro = macro.sort_values("Acerto%", ascending=False)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Média geral", f"{df['Acerto%'].mean():.1f}%")
        m2.metric("Alunos", f"{df['matricula'].nunique()}")
        m3.metric("Questões", f"{df['Questão'].nunique()}")
        m4.metric("Provas", f"{df['Nome Prova'].nunique()}")

        st.markdown("## Visão macro")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("**Comparação geral entre provas**")
            fig = px.bar(macro, x="Nome Prova", y="Acerto%", text="Acerto%", color="Nome Prova")
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_yaxes(range=[0, 100])
            fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("**Comparação geral por disciplina**")
            disc_macro = analise_final.groupby(["Nome Prova", "Disciplina"], as_index=False)["Correta"].mean()
            disc_macro["Acerto%"] = disc_macro["Correta"] * 100
            fig = px.bar(disc_macro, x="Nome Prova", y="Acerto%", color="Disciplina", barmode="group", text="Acerto%")
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_yaxes(range=[0, 100])
            fig.update_layout(margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        if multi_prova:
            st.markdown("## Comparação de provas")
            c3, c4 = st.columns(2)
            with c3:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown("**Média por prova e turma**")
                prova_turma = analise_final.groupby(["Nome Prova", "Turma"], as_index=False)["Correta"].mean()
                prova_turma["Acerto%"] = prova_turma["Correta"] * 100
                fig = px.bar(prova_turma, x="Nome Prova", y="Acerto%", color="Turma", barmode="group", text="Acerto%")
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_yaxes(range=[0, 100])
                fig.update_layout(margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with c4:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown("**Ranking das provas**")
                fig = px.bar(macro.sort_values("Acerto%", ascending=True), x="Acerto%", y="Nome Prova", orientation="h", text="Acerto%", color="Acerto%", color_continuous_scale="Blues")
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_xaxes(range=[0, 100])
                fig.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("## Visão micro por disciplina")
        disc_sel2 = st.selectbox("Escolha a disciplina", disciplinas, key="disc_quest")
        df_disc = analise_final[analise_final["Disciplina"] == disc_sel2].copy()
        if not df_disc.empty:
            q_stats = df_disc.groupby("Questão", as_index=False).agg(AcertoMedio=("Correta", "mean"), Total=("Correta", "size"))
            q_stats["Acerto%"] = q_stats["AcertoMedio"] * 100
            q_stats = q_stats.sort_values("Questão")
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("**Percentual de acerto por questão**")
            fig_q = px.bar(q_stats, x="Questão", y="Acerto%", text="Acerto%", color="Acerto%", color_continuous_scale="Blues")
            fig_q.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig_q.update_yaxes(range=[0, 100])
            fig_q.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig_q, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("**Distribuição das respostas por questão**")
            quest_sel = st.selectbox("Escolha a questão", sorted(df_disc["Questão"].unique().tolist()), key="quest_sel")
            d_quest = df_disc[df_disc["Questão"] == quest_sel].copy()
            dist = d_quest.groupby("Resposta_Aluno", as_index=False).size().rename(columns={"size": "Quantidade"})
            dist["Percentual"] = dist["Quantidade"] / dist["Quantidade"].sum() * 100
            dist = dist.sort_values("Quantidade", ascending=False)
            fig_dist = px.bar(dist, x="Resposta_Aluno", y="Percentual", text="Percentual", color="Resposta_Aluno")
            fig_dist.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig_dist.update_yaxes(range=[0, 100])
            fig_dist.update_layout(showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig_dist, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("## Visão micro por aluno")
        aluno_focus = st.selectbox("Escolha o aluno", sorted(df["nome"].dropna().astype(str).unique().tolist(), key=str.lower), key="aluno_focus")
        df_aluno = analise_final[analise_final["nome"] == aluno_focus].copy()
        if not df_aluno.empty:
            aluno_rank = df_aluno.groupby(["matricula", "nome", "Turma"], as_index=False).agg(AcertoMedio=("Correta", "mean"), Questoes=("Questão", "count"))
            aluno_rank["Acerto%"] = aluno_rank["AcertoMedio"] * 100
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("**Desempenho do aluno selecionado**")
            st.metric("Média do aluno", f"{aluno_rank['Acerto%'].iloc[0]:.1f}%")
            st.dataframe(df_aluno.sort_values(["Nome Prova", "Disciplina", "Questão"]), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("## Tabela detalhada")
        st.dataframe(df.sort_values(["Turma", "nome", "Questão"]).reset_index(drop=True), use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar os arquivos: {e}")
else:
    st.info("Envie os dois arquivos: Gabarito e RespAluno.")
