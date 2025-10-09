"""
Gera uma tabela (Excel) com os dados de faturamento exclusivamente do mês de setembro
para todos os anos registrados, filtrando pela equipe 'VAREJO'.

Baseado em query `querys/faturamento.markdown`.
"""

import os
import pandas as pd
from functions.connect import get_connection


def run_query_setembro_varejo() -> pd.DataFrame:
    """
    Executa a consulta de faturamento apenas para o mês de setembro (todos os anos)
    e apenas para a equipe 'VAREJO'.
    """
    cnxn = get_connection()
    cur = cnxn.cursor()

    # Query adaptada de querys/faturamento.markdown
    # Removidos parâmetros de data e aplicado filtro para mês=9 e equipe VAREJO
    query = r"""
with
Custo AS (
    select M.REGISTRO, m.reg_material, M.REG_EMPRESA,
        (select first 1 P.VALOR 
         from PRECO_MEDIO_DIA P
         where P.ID_MATERIAL = M.REGISTRO 
         and P.ID_EMPRESA = M.REG_EMPRESA 
         order by P.DATA desc) custo
    from MATERIAIS_COMPL M
    group by M.REGISTRO, M.REG_EMPRESA, reg_material
)
select distinct
    n.DATA,
    n.nota || '/' || n.serie as nota,
    V.DESCRICAO as TIPO_MOVIMENTO,
    n.cliente as cod_cli,
    p.razaosoc cliente,
    m.codigo cod_prod,
    m.descricao,
    I.QUANT as QUANT,
    cast (
        IIF(v.registro in (9,140,112,202,144,63,22,81,80),
            (((i.valor+i.pis_cofins_zf) - (i.desconto / 100) * (i.valor+i.pis_cofins_zf) ) * -1),
            (i.valor - (i.desconto / 100) * i.valor )
        )  as decimal(10, 2)
    ) valor_unitario,
    cast (
        IIF( v.registro in (9,140,112,202,144,63,22,81,80), 
            ((i.valor - (i.desconto / 100) * i.valor ) * I.QUANT + coalesce(i.valoripi, 0)) * -1,
            ((i.valor - (i.desconto / 100) * i.valor ) * I.QUANT + coalesce(i.valoripi, 0))
        ) +( i.nfe_vfrete+nfe_vseguro)
         - (i.icms_zf +i.pis_cofins_zf)
         as decimal(10, 2)
    ) total_NF,
    cast (
        IIF( v.registro in (9,140,112,202,144,63,22,81,80), 
            ((i.valor - (i.desconto / 100) * i.valor ) * I.QUANT) * -1, 
            ((i.valor - (i.desconto / 100) * i.valor ) * I.QUANT)
        ) - (i.icms_zf +i.pis_cofins_zf)  as decimal(10, 2)
    ) total_merc,
    cast (  (i.icms_zf +i.pis_cofins_zf)   as decimal(10,2)) VLRZF,
    i.nfe_vfrete+nfe_vseguro as "FRETE+SEGURO",
    IIF(v.registro in (9,140,112,202,144,63,22,81,80), i.valoricm *-1,i.valoricm) as valoricm ,
    IIF(v.registro in (9,140,112,202,144,63,22,81,80),i.valoripi *-1,i.valoripi) as valoripi ,
    IIF(v.registro in (9,140,112,202,144,63,22,81,80), (i.valor_pis + i.valor_cofins )*-1,i.valor_pis + i.valor_cofins) as  pis_confis ,
    cast (
        IIF( v.registro in (9,140,112,202,144,63,22,81,80), 
            ((((i.valor - (i.desconto / 100) * i.valor )) * I.QUANT )  * (i.comissao / 100)) * -1, 
            ((((i.valor - (i.desconto / 100) * i.valor )) * I.QUANT )  * (i.comissao / 100))
        ) as decimal(10, 2)
    ) comissao,
    cast (
        IIF( v.registro in (9,140,112,202,144,63,22,81,80), 
            iif(i.NFE_VFRETE = 0, (i.baseicm / n.totmerc) * n.valor_frete_pago,0 ) * -1,
            iif(i.NFE_VFRETE = 0, (i.baseicm / n.totmerc) * n.valor_frete_pago, 0)
        ) as decimal(10, 2)
    ) as frete,
    cast (
        IIF( v.registro in (9,140,112,202,144,63,22,81,80), 
            ((i.valor - (i.desconto / 100) * i.valor ) * I.QUANT - (
                i.valoricm + 
                (I.NFE_VFRETE + I.NFE_VSEGURO + I.NFE_VDESPESAS ) + 
                (i.valor_pis + i.valor_cofins) + 
                iif(i.NFE_VFRETE = 0, (i.baseicm / n.totmerc) * n.valor_frete_pago, i.NFE_VFRETE) + 
                ((((i.valor - (i.desconto / 100) * i.valor)) * I.QUANT) * (i.comissao / 100))
            )) * -1,
            ((i.valor - (i.desconto / 100) * i.valor ) * I.QUANT - (
                i.valoricm + 
                (I.NFE_VFRETE + I.NFE_VSEGURO + I.NFE_VDESPESAS ) + 
                (i.valor_pis + i.valor_cofins) + 
                iif(i.NFE_VFRETE = 0, (i.baseicm / n.totmerc) * n.valor_frete_pago, i.NFE_VFRETE) + 
                ((((i.valor - (i.desconto / 100) * i.valor)) * I.QUANT) * (i.comissao / 100))
            ))
        ) as decimal(10, 2)
    ) vlr_liquido,
    cast( IIF( v.registro in (9),
        (c.custo * i.QUANT)*-1 ,(c.custo * i.QUANT)) as decimal(10,2)) AS CMV,
    cast(
        IIF(
            ((i.valor - (i.desconto / 100) * i.valor) * I.QUANT) = 0,
            0,
            (
                ((i.valor - (i.desconto / 100) * i.valor) * I.QUANT) -
                (
                    c.custo * i.QUANT +
                    i.valoricm +
                    (I.NFE_VFRETE + I.NFE_VSEGURO + I.NFE_VDESPESAS) +
                    iif(i.NFE_VFRETE = 0, (i.baseicm / n.totmerc) * n.valor_frete_pago, i.NFE_VFRETE) +
                    (i.valor_pis + i.valor_cofins) +
                    (((i.valor - (i.desconto / 100) * i.valor) * I.QUANT) * (i.comissao / 100))
                )
            )
        ) as decimal(15,2)
    ) as margem,
    ven.categoria,
    p.atividade,
    G.GRUPO,
    S.SUBGRUPO,
    pv.razaosoc vendedor,
    e.equipe,
    i.nfe_cfop as cfop,
    n.uf_cliente uf,
    p.cidade,
    extract(month from  n.DATA) as mes,
    extract(year from  n.DATA) as ano,
    i.lote,
    emp.razaosoc as empresa,i.registro
from notas n
    inner join itemnota i on I.nota = n.REGISTRO
    inner join MATERIAIS M on M.REGISTRO = I.produto
    inner join GRUPOS G on G.REGISTRO = M.GRUPO
    inner join SUBGRUPOS S on S.REGISTRO = M.SUBGRUPO
    inner join TIPO_VENDA V on V.REGISTRO = I.ID_TIPONOTA
    inner join pessoas p on p.codigo = n.cliente
    inner join Custo C on i.produto = c.reg_material
    and c.REG_EMPRESA=n.empresa
    inner join vendedores ven on ven.pessoa = n.vendedor
    inner join pessoas pv on pv.codigo = ven.pessoa
    inner join equipes e on e.registro = ven.equipe
    inner join empresas emp on emp.registro=n.empresa
where
   extract(month from n.DATA) = 9
   and n.situacao <> 'C'
   and upper(e.equipe) = 'VAREJO'
   and v.registro in  ( 01,70,71,79,83,98,120,122,129,143,154,156,160,164,179,181,184,223,224,22)
"""

    cur.execute(query)
    rows = cur.fetchall()

    # Monta DataFrame a partir de cursor.description
    colnames = [desc[0].strip() if isinstance(desc[0], str) else desc[0] for desc in cur.description]
    df = pd.DataFrame(rows, columns=colnames)

    cur.close()
    cnxn.close()
    return df


def salvar_excel(df: pd.DataFrame, nome_arquivo: str = 'faturamento_setembro_varejo.xlsx'):
    """
    Salva o DataFrame em consultas/<nome_arquivo>, com duas abas:
    - Detalhe: linhas completas
    - Resumo: agregados por ano (somas de QUANT, TOTAL_NF, CMV, MARGEM)
    """
    pasta_consultas = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'consultas')
    os.makedirs(pasta_consultas, exist_ok=True)
    caminho = os.path.join(pasta_consultas, nome_arquivo)

    # Monta resumo simples por ano, se as colunas existirem
    resumo = None
    try:
        cols_exist = all(c in df.columns for c in ['ANO', 'QUANT', 'TOTAL_NF', 'CMV', 'MARGEM'])
        if cols_exist:
            resumo = (
                df.groupby(['ANO'], as_index=False)[['QUANT', 'TOTAL_NF', 'CMV', 'MARGEM']]
                  .sum()
                  .sort_values('ANO')
            )
    except Exception:
        resumo = None

    with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Detalhe')
        if resumo is not None:
            resumo.to_excel(writer, index=False, sheet_name='Resumo_ano')
    return caminho


if __name__ == '__main__':
    print('Executando consulta: Setembro (todos os anos) - Equipe VAREJO...')
    try:
        df = run_query_setembro_varejo()
        print(f'Total de registros: {len(df)}')
        if not df.empty:
            print(df.head().to_string(index=False))
        caminho = salvar_excel(df)
        print(f'Arquivo salvo em: {caminho}')
    except Exception as e:
        print(f'Erro ao executar consulta: {e}')
