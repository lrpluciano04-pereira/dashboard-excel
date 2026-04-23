with tab_graficos:
                col_a, col_b = st.columns(2)
                
                # Criando a coluna de 'Série' extraindo os primeiros caracteres da Turma
                # Exemplo: "9º Ano A" vira "9º Ano"
                def extrair_serie(turma):
                    # Tenta pegar o padrão "Nº Ano" ou apenas os primeiros caracteres antes de espaços/letras finais
                    match = re.search(r'(\d+º?\s?(?:Ano|Série|ano|serie))', str(turma))
                    return match.group(1) if match else str(turma)[:6]

                df_final["Série"] = df_final["Turma"].apply(extrair_serie)

                with col_a:
                    st.subheader("📊 Média por Série")
                    df_serie = df_final.groupby("Série")["Nota Final"].mean().reset_index()
                    fig_serie = px.bar(df_serie, x="Série", y="Nota Final", 
                                      text="Nota Final",
                                      title="Desempenho por Ano Escolar",
                                      color="Nota Final",
                                      color_continuous_scale="Blues")
                    fig_serie.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                    fig_serie.update_layout(yaxis_range=[0, valor_total_prova + 1])
                    st.plotly_chart(fig_serie, use_container_width=True)

                with col_b:
                    st.subheader("🏫 Média por Turma")
                    df_turma_media = df_final.groupby("Turma")["Nota Final"].mean().reset_index()
                    fig_turma = px.bar(df_turma_media, x="Turma", y="Nota Final", 
                                      text="Nota Final",
                                      title="Comparativo entre Turmas",
                                      color="Turma")
                    fig_turma.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                    fig_turma.update_layout(yaxis_range=[0, valor_total_prova + 1])
                    st.plotly_chart(fig_turma, use_container_width=True)
                
                st.info("💡 **Análise Sugerida:** Se houver grande diferença entre turmas da mesma série, vale investigar se o ritmo de conteúdo ou a metodologia de ensino está variando entre as salas.")
