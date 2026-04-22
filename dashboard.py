
import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(
    page_title="Dashboard Educacional",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
    .block-container {padding-top: 1.2rem; padding-bottom: 2rem; padding-left: 2rem; padding-right: 2rem;}
    .title-box {background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%); padding: 1.4rem 1.5rem; border-radius: 18px; color: white; margin-bottom: 1rem; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18);}    
    .subtitle {opacity: 0.85; font-size: 0.95rem; margin-top: 0.35rem;}
    div[data-testid="stMetric"] {background: white; border: 1px solid #e5e7eb; padding: 14px 16px; border-radius: 16px; box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);}
    section[data-testid="stSidebar"] {background: #f8fafc; border-right: 1px solid #e5e7eb;}
    .chart-card {background: white; border: 1px solid #e5e7eb; border-radius: 18px; padding: 1rem 1rem 0.5rem 1rem; box-shadow: 0 4px 18px rgba(15, 23, 42, 0.05); margin-bottom: 1rem;}
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

serie_ordem = ["2-1MA", "2-2MA", "2-3MA"]
cores_serie = {"2-1MA": "#2563eb", "2-2MA": "#16a34a", "2-3MA": "#f97316"}

st.markdown("""
<div class="title-box">
    <h1 style="margin:0; font-size:2rem;">📊 Dashboard Educacional</h1>
    <div class="subtitle">Análise visual de desempenho por série, PP, turma e disciplina</div>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Envie a planilha Excel", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Analise_RespAluno")

        serie_col = find_col(df, ["serie", "série", "ano"])
        semestre_col = find_col(df, ["semestre"])
        metric_col = find_col(df, ["acerto", "acertos", "percentual", "%", "nota", "resultado", "media", "média"])
        pp_col = find_col(df, ["pp"])
        turma_col = find_col(df, ["turma"])
        disciplina_col = find_col(df, ["disciplina", "materia", "matéria"])

        if metric_col is None:
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            metric_col = numeric_cols[0] if numeric_cols else None

        if metric_col is None or serie_col is None or semestre_col is None:
            st.error("Não encontrei as colunas necessárias: Série, Semestre e Métrica.")
            st.stop()

        df[metric_col] = to_percent_series(df[metric_col])

        with st.sidebar:
            st.header("Filtros")
            semestres = ["Todos"] + sorted(df[semestre_col].astype(str).dropna().unique().tolist())
            semestre_sel = st.selectbox("Semestre", semestres)

            df_f = df.copy()
            if semestre_sel != "Todos":
                df_f = df_f[df_f[semestre_col].astype(str) == semestre_sel]

            serie_sel = "Todas"
            pp_sel = "Todos"
            disc_sel = "Todas"

            if serie_col:
                serie_opcoes = ["Todas"] + sorted(df_f[serie_col].astype(str).str.strip().dropna().unique().tolist())
                serie_sel = st.selectbox("Série", serie_opcoes)

            if pp_col:
                pp_opcoes = ["Todos"] + sorted(df_f[pp_col].astype(str).str.strip().dropna().unique().tolist(), key=natural_key)
                pp_sel = st.selectbox("PP", pp_opcoes)

            if disciplina_col:
                disc_opcoes = ["Todas"] + sorted(df_f[disciplina_col].astype(str).str.strip().dropna().unique().tolist())
                disc_sel = st.selectbox("Disciplina", disc_opcoes)

        df_f = df.copy()
        if semestre_sel != "Todos":
            df_f = df_f[df_f[semestre_col].astype(str) == semestre_sel]
        if serie_col and serie_sel != "Todas":
            df_f = df_f[df_f[serie_col].astype(str).str.strip() == serie_sel]
        if pp_col and pp_sel != "Todos":
            df_f = df_f[df_f[pp_col].astype(str).str.strip() == pp_sel]
        if disciplina_col and disc_sel != "Todas":
            df_f = df_f[df_f[disciplina_col].astype(str).str.strip() == disc_sel]

        m1, m2, m3 = st.columns(3)
        m1.metric("Média geral", f"{df_f[metric_col].mean():.1f}%")
        m2.metric("Registros", f"{len(df_f):,}".replace(",", "."))
        m3.metric("Disciplinas", f"{df_f[disciplina_col].nunique() if disciplina_col else 0}")

        st.markdown("### Análises principais")

        c1, c2 = st.columns(2)

        with c1:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("**Média geral por série**")
            g_serie = df_f.groupby(serie_col, as_index=False)[metric_col].mean()
            g_serie[serie_col] = g_serie[serie_col].astype(str).str.strip()
            g_serie = g_serie[g_serie[serie_col].isin(serie_ordem)]
            g_serie[serie_col] = pd.Categorical(g_serie[serie_col], categories=serie_ordem, ordered=True)
            g_serie = g_serie.sort_values(serie_col)

            fig1 = px.bar(g_serie, x=serie_col, y=metric_col, text=metric_col, color=serie_col, color_discrete_map=cores_serie, category_orders={serie_col: serie_ordem})
            fig1.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig1.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
            fig1.update_layout(xaxis_title="Série", yaxis_title="Percentual", showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig1, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("**Média geral por Série/PP**")
            if pp_col:
                ordem_pp = sorted(df_f[pp_col].astype(str).str.strip().unique().tolist(), key=natural_key)
                g_pp = df_f.groupby(pp_col, as_index=False)[metric_col].mean()
                g_pp[pp_col] = g_pp[pp_col].astype(str).str.strip()
                g_pp = g_pp[g_pp[pp_col].isin(ordem_pp)]
                g_pp[pp_col] = pd.Categorical(g_pp[pp_col], categories=ordem_pp, ordered=True)
                g_pp = g_pp.sort_values(pp_col)

                fig2 = px.bar(g_pp, x=pp_col, y=metric_col, text=metric_col, color=pp_col)
                fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig2.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
                fig2.update_layout(xaxis_title="Série/PP", yaxis_title="Percentual", showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.warning("Não encontrei a coluna PP.")
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("**Média geral por turma**")
        if turma_col:
            df_turma = df.copy()
            if semestre_sel != "Todos":
                df_turma = df_turma[df_turma[semestre_col].astype(str) == semestre_sel]
            if serie_col and serie_sel != "Todas":
                df_turma = df_turma[df_turma[serie_col].astype(str).str.strip() == serie_sel]

            g_turma = df_turma.groupby(turma_col, as_index=False)[metric_col].mean()
            g_turma[turma_col] = g_turma[turma_col].astype(str).str.strip()
            g_turma = g_turma.sort_values(turma_col, key=lambda s: s.map(natural_key))

            fig3 = px.bar(g_turma, x=turma_col, y=metric_col, text=metric_col, color=turma_col)
            fig3.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig3.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
            fig3.update_layout(xaxis_title="Turma", yaxis_title="Percentual", showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.warning("Não encontrei a coluna Turma.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("**Média geral por disciplina**")
        if disciplina_col:
            g_disc = df_f.groupby(disciplina_col, as_index=False)[metric_col].mean()
            g_disc[disciplina_col] = g_disc[disciplina_col].astype(str).str.strip()
            g_disc = g_disc.sort_values(metric_col, ascending=False)

            fig4 = px.bar(g_disc, x=disciplina_col, y=metric_col, text=metric_col, color=disciplina_col)
            fig4.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig4.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
            fig4.update_layout(xaxis_title="Disciplina", yaxis_title="Percentual", showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.warning("Não encontrei a coluna Disciplina.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("**Média geral Série/Disciplina/PP**")
        if disciplina_col and pp_col and serie_col:
            g_triplo = df_f.groupby([pp_col, disciplina_col, serie_col], as_index=False)[metric_col].mean()
            g_triplo[pp_col] = g_triplo[pp_col].astype(str).str.strip()
            g_triplo[disciplina_col] = g_triplo[disciplina_col].astype(str).str.strip()
            g_triplo[serie_col] = g_triplo[serie_col].astype(str).str.strip()
            g_triplo["Eixo_X"] = g_triplo[pp_col] + " | " + g_triplo[disciplina_col] + " | " + g_triplo[serie_col]

            chart_orientation = "v"  # troque para "h" se quiser horizontal

            if chart_orientation == "v":
                fig5 = px.bar(
                    g_triplo,
                    x="Eixo_X",
                    y=metric_col,
                    text=metric_col,
                    color=pp_col
                )
                fig5.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig5.update_layout(xaxis_title="PP | Disciplina | Série", yaxis_title="Percentual")
                fig5.update_yaxes(range=[0, 100], tickformat='.0f')
            else:
                fig5 = px.bar(
                    g_triplo,
                    x=metric_col,
                    y="Eixo_X",
                    text=metric_col,
                    color=pp_col,
                    orientation='h'
                )
                fig5.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig5.update_layout(xaxis_title="Percentual", yaxis_title="PP | Disciplina | Série")
                fig5.update_xaxes(range=[0, 100], tickformat='.0f')

            fig5.update_layout(margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.warning("Não encontrei as colunas necessárias para este gráfico.")
        st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erro ao carregar a planilha: {e}")
else:
    st.info("Envie uma planilha para começar.")
