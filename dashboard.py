import plotly.express as px
import plotly.graph_objects as go

# ... (Mantenha o código anterior de correção)

if st.button("📝 Calcular Notas e Gerar Lista Final"):
    # ... (Processamento da lista_final que já fizemos)
    
    df_final = pd.DataFrame(lista_final)
    
    # --- INÍCIO DA ANÁLISE GERAL (DASHBOARD) ---
    st.divider()
    st.header("🔍 Análise Geral de Desempenho")
    
    # 1. Métricas de Sucesso
    col1, col2, col3, col4 = st.columns(4)
    media_geral = df_final["Nota Final"].mean()
    percentual_acerto = (df_final["Acertos"].sum() / (len(df_final) * num_questoes)) * 100
    
    col1.metric("Média Geral", f"{media_geral:.2f}")
    col2.metric("Aproveitamento", f"{percentual_acerto:.1f}%")
    col3.metric("Maior Nota", f"{df_final['Nota Final'].max():.2f}")
    col4.metric("Menor Nota", f"{df_final['Nota Final'].min():.2f}")

    tab_geral, tab_questoes, tab_turmas = st.tabs(["📈 Distribuição", "🎯 Análise por Questão", "🏫 Comparativo Turmas"])

    with tab_geral:
        st.subheader("Distribuição de Notas")
        # Gráfico de Histograma para ver a concentração de notas
        fig_hist = px.histogram(df_final, x="Nota Final", nbins=10, 
                               title="Frequência de Notas na Classe",
                               labels={'Nota Final': 'Nota', 'count': 'Qtd de Alunos'},
                               color_discrete_sequence=['#636EFA'])
        st.plotly_chart(fig_hist, use_container_width=True)

    with tab_questoes:
        st.subheader("Índice de Acerto por Questão")
        # Calculando o percentual de acerto de cada questão
        stats_questoes = []
        for q in qcols:
            respostas_certas = 0
            gaba_q = dict_gaba.get(str(q).strip())
            for _, row in df_resp.iterrows():
                if str(row[q]).strip().upper() == gaba_q:
                    respostas_certas += 1
            
            percent_q = (respostas_certas / len(df_resp)) * 100
            stats_questoes.append({"Questão": str(q), "Acerto %": percent_q})
        
        df_stats_q = pd.DataFrame(stats_questoes)
        
        # Gráfico de barras colorindo questões críticas (abaixo de 50% de acerto)
        fig_q = px.bar(df_stats_q, x="Questão", y="Acerto %", 
                       title="Percentual de Acerto por Item",
                       color="Acerto %", 
                       color_continuous_scale=px.colors.diverging.RdYlGn,
                       range_color=[0, 100])
        fig_q.add_hline(y=50, line_dash="dot", line_color="red", annotation_text="Alerta de Aprendizado")
        st.plotly_chart(fig_q, use_container_width=True)
        st.info("💡 **Dica Pedagógica:** Questões em vermelho indicam conteúdos que precisam de retomada com a turma.")

    with tab_turmas:
        st.subheader("Desempenho por Turma")
        df_turma = df_final.groupby("Turma")["Nota Final"].mean().reset_index()
        fig_turma = px.box(df_final, x="Turma", y="Nota Final", color="Turma",
                          title="Dispersão de Notas por Turma")
        st.plotly_chart(fig_turma, use_container_width=True)
