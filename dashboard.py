import streamlit as st
import pandas as pd
import plotly.express as px
import re
from io import BytesIO

st.set_page_config(page_title="Dashboard Educacional", page_icon="📊", layout="wide")

st.markdown("""
<style>
.block-container{padding-top:1.2rem;padding-bottom:2rem;padding-left:2rem;padding-right:2rem;}
.title-box{background:linear-gradient(90deg,#0f172a 0%,#1e293b 100%);padding:1.4rem 1.5rem;border-radius:18px;color:white;margin-bottom:1rem;box-shadow:0 8px 24px rgba(15,23,42,.18);}
.subtitle{opacity:.85;font-size:.95rem;margin-top:.35rem;}
div[data-testid="stMetric"]{background:white;border:1px solid #e5e7eb;padding:14px 16px;border-radius:16px;box-shadow:0 4px 16px rgba(15,23,42,.06);}
section[data-testid="stSidebar"]{background:#f8fafc;border-right:1px solid #e5e7eb;}
.chart-card{background:white;border:1px solid #e5e7eb;border-radius:18px;padding:1rem 1rem .5rem 1rem;box-shadow:0 4px 18px rgba(15,23,42,.05);margin-bottom:1rem;}
</style>
""", unsafe_allow_html=True)

def find_col(df, options):
    for col in df.columns:
        nome = str(col).lower().strip()
        for opt in options:
            if opt in nome:
                return col
    return None

def to_percent_series(s):
    s = pd.to_numeric(s, errors="coerce")
    if s.dropna().max() <= 1:
        return s * 100
    return s

def natural_key(text):
    parts = re.split(r'(\d+)', str(text))
    return [int(p) if p.isdigit() else p for p in parts]

def excel_bytes(df):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Analise_RespAluno")
    bio.seek(0)
    return bio.getvalue()

st.markdown("""
<div class="title-box">
    <h1 style="margin:0;font-size:2rem;">📊 Dashboard Educacional</h1>
    <div class="subtitle">Upload do gabarito + respostas do aluno, geração automática da Analise_RespAluno</div>
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

        g_prova = find_col(gabarito, ["prova"])
        g_disc = find_col(gabarito, ["disciplina"])
        g_questao = find_col(gabarito, ["questão", "questao"])
        g_resp = find_col(gabarito, ["resposta"])

        r_id_mat = find_col(resp, ["id-titulomatricula", "id titulo matricula", "idtitulo matricula"])
        r_id_turma = find_col(resp, ["id-titulocodturma", "id titulo codturma", "idtitulo codturma"])
        r_codigo = find_col(resp, ["codigo", "código"])
        r_titulo = find_col(resp, ["titulo", "título"])
        r_descricao = find_col(resp, ["descricao", "descrição"])
        r_periodo = find_col(resp, ["periodoletivo", "periodo letivo", "período letivo"])
        r_filial = find_col(resp, ["codigofilial", "codigo filial", "código filial"])
        r_turma = find_col(resp, ["codigoturma", "codigo turma", "código turma"])
        r_matricula = find_col(resp, ["matricula", "matrícula"])
        r_nome = find_col(resp, ["nome"])
        r_prova = find_col(resp, ["prova"])
        quest_cols = [c for c in resp.columns if str(c).strip().isdigit()]

        if not all([g_prova, g_disc, g_questao, g_resp, r_prova]) or not quest_cols:
            st.error("Não encontrei todas as colunas necessárias para montar a análise.")
            st.stop()

        gabarito[g_questao] = pd.to_numeric(gabarito[g_questao], errors="coerce")
        gabarito = gabarito.dropna(subset=[g_questao])
        gabarito[g_questao] = gabarito[g_questao].astype(int)
        gabarito[g_resp] = gabarito[g_resp].astype(str).str.strip().str.upper()
        gabarito[g_prova] = gabarito[g_prova].astype(str).str.strip()
        gabarito[g_disc] = gabarito[g_disc].astype(str).str.strip()

        resp[r_prova] = resp[r_prova].astype(str).str.strip()
        for c in quest_cols:
            resp[c] = resp[c].astype(str).str.strip().str.upper()

        id_vars = [c for c in [r_id_mat, r_id_turma, r_codigo, r_titulo, r_descricao, r_periodo, r_filial, r_turma, r_matricula, r_nome, r_prova] if c]
        melted = resp.melt(
            id_vars=id_vars,
            value_vars=quest_cols,
            var_name="Questão",
            value_name="Resposta_Aluno"
        )

        melted["Questão"] = pd.to_numeric(melted["Questão"], errors="coerce")
        melted = melted.dropna(subset=["Questão"])
        melted["Questão"] = melted["Questão"].astype(int)
        melted["Resposta_Aluno"] = melted["Resposta_Aluno"].astype(str).str.strip().str.upper()

        analise = melted.merge(
            gabarito[[g_prova, g_disc, g_questao, g_resp]],
            left_on=[r_prova, "Questão"],
            right_on=[g_prova, g_questao],
            how="left"
        )

        analise["Correta"] = (analise["Resposta_Aluno"] == analise[g_resp]).astype(int)
        analise["Resultado"] = analise["Correta"].map({1: "Certa", 0: "Errada"})
        analise["Acerto%"] = analise["Correta"] * 100
        analise["Resposta_Gabarito"] = analise[g_resp] if g_resp in analise.columns else pd.NA

        rename_map = {}
        if r_id_mat and r_id_mat in analise.columns:
            rename_map[r_id_mat] = "ID-TituloMatricula"
        if r_id_turma and r_id_turma in analise.columns:
            rename_map[r_id_turma] = "ID-TituloCodTurma"
        if r_codigo and r_codigo in analise.columns:
            rename_map[r_codigo] = "codigo"
        if r_titulo and r_titulo in analise.columns:
            rename_map[r_titulo] = "titulo"
        if r_descricao and r_descricao in analise.columns:
            rename_map[r_descricao] = "descricao"
        if r_periodo and r_periodo in analise.columns:
            rename_map[r_periodo] = "periodoLetivo"
        if r_filial and r_filial in analise.columns:
            rename_map[r_filial] = "codigoFilial"
        if r_turma and r_turma in analise.columns:
            rename_map[r_turma] = "codigoTurma"
        if r_matricula and r_matricula in analise.columns:
            rename_map[r_matricula] = "matricula"
        if r_nome and r_nome in analise.columns:
            rename_map[r_nome] = "nome"
        if r_prova and r_prova in analise.columns:
            rename_map[r_prova] = "prova"
        if g_prova and g_prova in analise.columns:
            rename_map[g_prova] = "Prova"
        if g_disc and g_disc in analise.columns:
            rename_map[g_disc] = "Disciplina"
        if g_questao and g_questao in analise.columns:
            rename_map[g_questao] = "Questão"

        analise = analise.rename(columns=rename_map)

        if "Disciplina" not in analise.columns:
            analise["Disciplina"] = ""
        if "Prova" not in analise.columns:
            analise["Prova"] = analise["prova"] if "prova" in analise.columns else ""
        if "Questão" not in analise.columns:
            analise["Questão"] = ""
        if "Resposta_Aluno" not in analise.columns:
            analise["Resposta_Aluno"] = ""
        if "Resposta_Gabarito" not in analise.columns:
            analise["Resposta_Gabarito"] = ""
        if "Correta" not in analise.columns:
            analise["Correta"] = 0
        if "Resultado" not in analise.columns:
            analise["Resultado"] = ""
        if "Acerto%" not in analise.columns:
            analise["Acerto%"] = 0

        base_cols = []
        for c in [
            "ID-TituloMatricula", "ID-TituloCodTurma", "codigo", "titulo", "descricao",
            "periodoLetivo", "codigoFilial", "codigoTurma", "matricula", "nome", "prova",
            "Prova", "Disciplina", "Questão", "Resposta_Aluno", "Resposta_Gabarito", "Correta", "Resultado", "Acerto%"
        ]:
            if c in analise.columns:
                base_cols.append(c)

        analise_final = analise[base_cols].copy()

        def infer_semestre(x):
            s = str(x)
            m = re.search(r'(\d)', s)
            return m.group(1) if m else "1"

        def infer_serie(x):
            s = str(x)
            m = re.search(r'(\d-\dMA)', s)
            if m:
                return m.group(1)
            m = re.search(r'(\d+)', s)
            return m.group(1) if m else s

        analise_final["Semestre"] = analise_final.get("periodoLetivo", pd.Series(["1"] * len(analise_final))).astype(str).apply(infer_semestre)
        analise_final["Série"] = analise_final.get("codigoTurma", pd.Series([""] * len(analise_final))).astype(str).apply(infer_serie)
        analise_final["PP"] = analise_final.get("prova", pd.Series([""] * len(analise_final))).astype(str)
        analise_final["Turma"] = analise_final.get("codigoTurma", pd.Series([""] * len(analise_final))).astype(str)
        analise_final["Disciplina"] = analise_final.get("Disciplina", pd.Series([""] * len(analise_final))).astype(str)
        analise_final["Acerto%"] = to_percent_series(analise_final["Acerto%"])

        st.success("Planilha Analise_RespAluno gerada com sucesso.")
        st.download_button(
            "Baixar Analise_RespAluno.xlsx",
            data=excel_bytes(analise_final),
            file_name="Analise_RespAluno.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        df = analise_final.copy()
        serie_col = "Série"
        semestre_col = "Semestre"
        metric_col = "Acerto%"
        pp_col = "PP"
        turma_col = "Turma"
        disciplina_col = "Disciplina"

        with st.sidebar:
            st.header("Filtros")
            semestres = ["Todos"] + sorted(df[semestre_col].astype(str).dropna().unique().tolist())
            semestre_sel = st.selectbox("Semestre", semestres)

            df_semestre = df.copy()
            if semestre_sel != "Todos":
                df_semestre = df_semestre[df_semestre[semestre_col].astype(str) == semestre_sel]

            serie_sel = st.selectbox("Série", ["Todas"] + sorted(df_semestre[serie_col].astype(str).str.strip().dropna().unique().tolist()))
            pp_sel = st.selectbox("PP", ["Todos"] + sorted(df_semestre[pp_col].astype(str).str.strip().dropna().unique().tolist(), key=natural_key))
            disc_sel = st.selectbox("Disciplina", ["Todas"] + sorted(df_semestre[disciplina_col].astype(str).str.strip().dropna().unique().tolist()))

        df_semestre = df.copy()
        if semestre_sel != "Todos":
            df_semestre = df_semestre[df_semestre[semestre_col].astype(str) == semestre_sel]

        df_semestre_serie = df_semestre.copy()
        if serie_sel != "Todas":
            df_semestre_serie = df_semestre_serie[df_semestre_serie[serie_col].astype(str).str.strip() == serie_sel]

        df_total_filtrado = df_semestre_serie.copy()
        if pp_sel != "Todos":
            df_total_filtrado = df_total_filtrado[df_total_filtrado[pp_col].astype(str).str.strip() == pp_sel]
        if disc_sel != "Todas":
            df_total_filtrado = df_total_filtrado[df_total_filtrado[disciplina_col].astype(str).str.strip() == disc_sel]

        m1, m2, m3 = st.columns(3)
        m1.metric("Média geral", f"{df_total_filtrado[metric_col].mean():.1f}%")
        m2.metric("Registros", f"{len(df_total_filtrado):,}".replace(",", "."))
        m3.metric("Disciplinas", f"{df_total_filtrado[disciplina_col].nunique()}")

        st.markdown("### Análises principais")

        c1, c2 = st.columns(2)

        with c1:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("**Média geral por série**")
            g_serie = df_semestre.groupby(serie_col, as_index=False)[metric_col].mean()
            fig1 = px.bar(g_serie, x=serie_col, y=metric_col, text=metric_col, color=serie_col)
            fig1.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig1.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
            fig1.update_layout(showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig1, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("**Média geral por Série/PP**")
            g_pp = df_semestre.groupby(pp_col, as_index=False)[metric_col].mean()
            g_pp = g_pp.sort_values(pp_col, key=lambda s: s.map(natural_key))
            fig2 = px.bar(g_pp, x=pp_col, y=metric_col, text=metric_col, color=pp_col)
            fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig2.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
            fig2.update_layout(showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("**Média geral por turma**")
        g_turma = df_semestre_serie.groupby(turma_col, as_index=False)[metric_col].mean()
        g_turma = g_turma.sort_values(turma_col, key=lambda s: s.map(natural_key))
        fig3 = px.bar(g_turma, x=turma_col, y=metric_col, text=metric_col, color=turma_col)
        fig3.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig3.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
        fig3.update_layout(showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("**Média geral por disciplina**")
        g_disc = df_total_filtrado.groupby(disciplina_col, as_index=False)[metric_col].mean()
        g_disc = g_disc.sort_values(metric_col, ascending=False)
        fig4 = px.bar(g_disc, x=disciplina_col, y=metric_col, text=metric_col, color=disciplina_col)
        fig4.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig4.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
        fig4.update_layout(showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig4, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("**Média geral Série/Disciplina/PP**")
        g_triplo = df_total_filtrado.groupby([pp_col, disciplina_col, serie_col], as_index=False)[metric_col].mean()
        g_triplo["Eixo_X"] = g_triplo[pp_col].astype(str) + " | " + g_triplo[disciplina_col].astype(str) + " | " + g_triplo[serie_col].astype(str)
        fig5 = px.bar(g_triplo, x="Eixo_X", y=metric_col, text=metric_col, color=pp_col)
        fig5.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig5.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
        fig5.update_layout(xaxis_title="PP | Disciplina | Série", margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig5, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erro ao processar os arquivos: {e}")
else:
    st.info("Envie os dois arquivos: Gabarito e RespAluno.")
