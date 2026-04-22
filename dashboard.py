st.subheader("Médias por Série e Série/PP")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Média geral por série**")
    g_serie = df_f.groupby(serie_col, as_index=False)[metric_col].mean()
    g_serie[serie_col] = g_serie[serie_col].astype(str).str.strip()
    g_serie = g_serie.set_index(serie_col).reindex(serie_ordem).reset_index()
    g_serie[metric_col] = g_serie[metric_col].fillna(0)

    fig1 = px.bar(
        g_serie,
        x=serie_col,
        y=metric_col,
        text=metric_col,
        color=serie_col,
        color_discrete_map=cores_serie,
        category_orders={serie_col: serie_ordem}
    )
    fig1.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig1.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
    fig1.update_layout(xaxis_title="Série", yaxis_title="Percentual", showlegend=False)
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.markdown("**Média Geral Série/PP**")
    if "PP" in df_f.columns:
        pp_col = "PP"
    else:
        pp_col = find_col(df_f, ["pp"])

    if pp_col:
        g_pp = df_f.groupby(pp_col, as_index=False)[metric_col].mean()
        g_pp[pp_col] = g_pp[pp_col].astype(str).str.strip()

        fig2 = px.bar(
            g_pp,
            x=pp_col,
            y=metric_col,
            text=metric_col,
            color=pp_col
        )
        fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig2.update_yaxes(range=[0, 100], tickformat='.0f', title="Percentual")
        fig2.update_layout(xaxis_title="Série/PP", yaxis_title="Percentual", showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("Não encontrei a coluna Série/PP na planilha.")
