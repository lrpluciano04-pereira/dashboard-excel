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
.subtitle{opacity:.85;font-size:.95rem;margin-top:0.35rem;}
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

def safe_metric(v):
    try:
        if pd.isna(v):
            return "0.0%"
        return f"{float(v):.1f}%"
    except Exception:
        return "0.0%"

def safe_mean(df, col):
    return float(df[col].mean()) if (col in df.columns and len(df)) else 0.0

st.markdown("""
<div class="title-box">
    <h1 style="margin:0;font-size:2rem;">📊 Painel de Desempenho</h1>
    <div class="subtitle">Visão executiva, comparação, análise por disciplina e desempenho individual</div>
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

        melted = resp2.melt(
            id_vars=[r_prova, r_turma, r_mat, r_nome],
            value_vars=qcols,
            var_name="Questão",
            value_name="Resposta_Aluno"
        )
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

        st.success("Planilha Analise_RespAluno gerada com sucesso.")
        st.download_button(
            "Baixar Analise_RespAluno.xlsx",
            data=excel_bytes(analise_final),
            file_name="Analise_RespAluno.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.sidebar.header("Filtros gerais")
        prova_sel = st.sidebar.selectbox("Nome Prova", ["Todas"] + provas)
        df_p = analise_final.copy()
        if prova_sel != "Todas":
            df_p = df_p[df_p["Nome Prova"].astype(str) == prova_sel]

        turma_opts = ["Todas"] + sorted(df_p["Turma"].dropna().astype(str).unique().tolist(), key=natural_key)
        turma_sel = st.sidebar.selectbox("Turma", turma_opts)
        df_pt = df_p.copy()
        if turma_sel != "Todas":
            df_pt = df_pt[df_pt["Turma"].astype(str) == turma_sel]

        aluno_opts = ["Todos"] + sorted(df_pt["nome"].dropna().astype(str).unique().tolist(), key=str.lower)
        aluno_sel = st.sidebar.selectbox("Aluno", aluno_opts)

        df = df_pt.copy()
        if aluno_sel != "Todos":
            df = df[df["nome"].astype(str) == aluno_sel]

        if df.empty:
            st.warning("Sem dados para os filtros selecionados.")
            st.stop()

        multi_prova = len(provas) > 1
        macro = analise_final.groupby("Nome Prova", as_index=False).agg(
            AcertoMedio=("Correta", "mean"),
            Alunos=("matricula", "nunique"),
            Questoes=("Questão", "nunique")
        )
        macro["Acerto%"] = macro["AcertoMedio"] * 100

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Média geral", safe_metric(safe_mean(df, "Acerto%")))
        m2.metric("Alunos", f"{df['matricula'].nunique()}")
        m3.metric("Questões", f"{df['Questão'].nunique()}")
        m4.metric("Provas", f"{df['Nome Prova'].nunique()}")

        tab1, tab2, tab3, tab4 = st.tabs(["Visão Geral", "Comparação", "Disciplina", "Aluno"])

        with tab1:
            st.markdown("## Visão macro")
            st.markdown("<div class='small-note'>Comece por aqui para entender o panorama geral e só depois desça para os detalhes.</div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)

            with c1:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown("**Comparação geral entre provas**")
                fig = px.bar(
                    macro.sort_values("Acerto%", ascending=True),
                    x="Acerto%", y="Nome Prova",
                    orientation="h", text="Acerto%",
                    color="Acerto%", color_continuous_scale="Blues"
                )
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_xaxes(range=[0, 100])
                fig.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig, use_container_width=True, key="chart_macro_provas")
                st.markdown('</div>', unsafe_allow_html=True)

            with c2:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown("**Mapa de desempenho por prova e disciplina (%)**")
                disc_macro = analise_final.groupby(["Nome Prova", "Disciplina"], as_index=False)["Correta"].mean()
                disc_macro["Acerto%"] = disc_macro["Correta"] * 100
                fig = px.density_heatmap(
                    disc_macro,
                    x="Nome Prova", y="Disciplina", z="Acerto%",
                    color_continuous_scale="Blues", text_auto=True
                )
                fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), coloraxis_colorbar_title="Acerto%")
                st.plotly_chart(fig, use_container_width=True, key="chart_macro_disc")
                st.markdown('</div>', unsafe_allow_html=True)

        with tab2:
            st.markdown("## Comparação de provas")
            if multi_prova:
                c3, c4 = st.columns(2)

                with c3:
                    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                    st.markdown("**Média por prova e turma**")
                    prova_turma = analise_final.groupby(["Nome Prova", "Turma"], as_index=False)["Correta"].mean()
                    prova_turma["Acerto%"] = prova_turma["Correta"] * 100
                    fig = px.bar(
                        prova_turma.sort_values("Acerto%", ascending=True),
                        x="Acerto%", y="Nome Prova",
                        color="Turma", orientation="h",
                        text="Acerto%", barmode="group"
                    )
                    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                    fig.update_xaxes(range=[0, 100])
                    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), legend_title_text="Turma")
                    st.plotly_chart(fig, use_container_width=True, key="chart_comp_prova_turma")
                    st.markdown('</div>', unsafe_allow_html=True)

                with c4:
                    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                    st.markdown("**Provas x quantidade de alunos**")
                    prova_alunos = analise_final.groupby("Nome Prova", as_index=False)["matricula"].nunique().rename(columns={"matricula": "Alunos"})
                    fig = px.bar(
                        prova_alunos.sort_values("Alunos", ascending=True),
                        x="Alunos", y="Nome Prova",
                        orientation="h", text="Alunos",
                        color="Alunos", color_continuous_scale="Greens"
                    )
                    fig.update_traces(texttemplate='%{text}', textposition='outside')
                    fig.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=10))
                    st.plotly_chart(fig, use_container_width=True, key="chart_ranking_provas")
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("Há apenas uma prova nos arquivos; a comparação entre provas será exibida quando houver mais de uma.")

        with tab3:
            st.markdown("## Visão micro por disciplina")
            if not disciplinas:
                st.info("Nenhuma disciplina disponível para os filtros atuais.")
            else:
                disc_sel2 = st.selectbox("Escolha a disciplina", ["Todos"] + disciplinas, key="disc_quest")
                df_disc = df.copy() if disc_sel2 == "Todos" else df[df["Disciplina"].astype(str) == disc_sel2].copy()

                if not df_disc.empty:
                    q_stats = df_disc.groupby("Questão", as_index=False).agg(
                        AcertoMedio=("Correta", "mean"),
                        Total=("Correta", "size")
                    )
                    q_stats["Acerto%"] = q_stats["AcertoMedio"] * 100
                    q_stats = q_stats.sort_values("Questão")

                    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                    st.markdown("**Percentual de acerto por questão**")
                    fig_q = px.bar(
                        q_stats, x="Questão", y="Acerto%",
                        text="Acerto%", color="Acerto%",
                        color_continuous_scale="Blues"
                    )
                    fig_q.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                    fig_q.update_yaxes(range=[0, 100])
                    fig_q.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=10))
                    st.plotly_chart(fig_q, use_container_width=True, key="chart_q_acerto")
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                    st.markdown("**Distribuição das respostas por questão**")
                    quest_sel = st.selectbox("Escolha a questão", sorted(df_disc["Questão"].unique().tolist()), key="quest_sel")
                    d_quest = df_disc[df_disc["Questão"] == quest_sel].copy()
                    dist = d_quest.groupby("Resposta_Aluno", as_index=False).size().rename(columns={"size": "Quantidade"})
                    dist["Percentual"] = dist["Quantidade"] / dist["Quantidade"].sum() * 100 if len(dist) else 0
                    dist = dist.sort_values("Percentual", ascending=False)
                    fig_dist = px.bar(
                        dist, x="Resposta_Aluno", y="Percentual",
                        text="Percentual", color="Percentual",
                        color_continuous_scale="Blues"
                    )
                    fig_dist.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                    fig_dist.update_yaxes(range=[0, 100])
                    fig_dist.update_layout(showlegend=False, coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=10))
                    st.plotly_chart(fig_dist, use_container_width=True, key="chart_q_dist")
                    st.markdown('</div>', unsafe_allow_html=True)

        with tab4:
            st.markdown("## Visão micro por aluno")
            aluno_base = df[df["Turma"] == turma_sel].copy() if turma_sel != "Todas" else df.copy()
            aluno_opts = sorted(aluno_base["nome"].dropna().astype(str).unique().tolist(), key=str.lower)

            if not aluno_opts:
                st.info("Nenhum aluno disponível para a turma selecionada.")
            else:
                aluno_focus = st.selectbox("Escolha o aluno", aluno_opts, key="aluno_focus")
                df_aluno = aluno_base[aluno_base["nome"] == aluno_focus].copy()

                if not df_aluno.empty:
                    resumo_aluno = df_aluno.groupby(["matricula", "nome", "Turma"], as_index=False).agg(
                        AcertoMedio=("Correta", "mean"),
                        Questoes=("Questão", "count")
                    )
                    resumo_aluno["Acerto%"] = resumo_aluno["AcertoMedio"] * 100
                    media_turma = aluno_base.groupby(["Turma"], as_index=False).agg(MediaTurma=("Correta", "mean"))
                    media_turma["MediaTurma%"] = media_turma["MediaTurma"] * 100
                    turma_media = media_turma["MediaTurma%"].iloc[0] if not media_turma.empty else 0

                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                        st.markdown("**Aluno x Turma**")
                        comp = pd.DataFrame({
                            "Grupo": ["Aluno", "Turma"],
                            "Acerto%": [resumo_aluno["Acerto%"].iloc[0], turma_media]
                        })
                        fig = px.bar(comp, x="Grupo", y="Acerto%", text="Acerto%", color="Grupo", color_continuous_scale="Blues")
                        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                        fig.update_yaxes(range=[0, 100])
                        fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
                        st.plotly_chart(fig, use_container_width=True, key="chart_aluno_turma")
                        st.markdown('</div>', unsafe_allow_html=True)

                    with c2:
                        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                        st.markdown("**Resumo do aluno selecionado**")
                        st.metric("Média do aluno", safe_metric(resumo_aluno["Acerto%"].iloc[0]))
                        st.metric("Média da turma", safe_metric(turma_media))
                        st.metric("Diferença", f"{resumo_aluno['Acerto%'].iloc[0]-turma_media:.1f} p.p.")
                        st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                    st.markdown("**Desempenho por questão do aluno**")
                    tabela_q = df_aluno[["Questão", "Resposta_Aluno", "Resposta_Gabarito", "Resultado"]].sort_values("Questão").copy()
                    tabela_q["Status"] = tabela_q["Resultado"].map({"Certa": "✅", "Errada": "❌"})
                    tabela_q = tabela_q[["Questão", "Status", "Resposta_Aluno", "Resposta_Gabarito", "Resultado"]]
                    st.dataframe(tabela_q, use_container_width=True, hide_index=True)
                    st.markdown('<div class="small-note">A tabela permite leitura mais precisa por questão; se quiser, essa área pode virar um scorecard com semáforo.</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erro ao processar os arquivos: {e}")
else:
    st.info("Envie os dois arquivos: Gabarito e RespAluno.")
