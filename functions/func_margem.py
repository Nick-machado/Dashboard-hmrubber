import plotly.express as px

def dataframe_margem(df, filtro):
    df_margem = df.groupby(f"{filtro}")["$ Margem"].sum().reset_index()
    df_margem = df_margem.sort_values(by="$ Margem", ascending=False)
    return df_margem

def grafico_margem(df, filtro):
    fig = px.bar(
        df,
        x="$ Margem",
        y=f"{filtro}",
        color=f"{filtro}",
        orientation='h',
        title=f"Somatória da Margem por {filtro} (Ranqueado)",
        hover_data={"$ Margem": ":,.2f", f"{filtro}": True}
    )

    for i, row in df.iterrows():
        valor_formatado = f"R$ {row['$ Margem']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        fig.add_annotation(
            x=row["$ Margem"],
            y=row[f"{filtro}"],
            text=valor_formatado,
            showarrow=False,
            font=dict(size=14, color="white"),
            xanchor="left",
        )

    fig.update_layout(showlegend=False)

    return fig