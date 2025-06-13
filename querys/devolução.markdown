select
    n.DATA,
   -- M.REGISTRO,
    n.nota || '/' || n.serie as nota,
    V.DESCRICAO as TIPO_MOVIMENTO,
    m.codigo cod_prod,
    m.descricao,
    I.QUANT as QUANT,
    cast (
        IIF(v.registro in (01,70,71,79,83,98,120,122,128,143,154,156,160,164,179,181,184,223,224,22),
            (((i.valor+i.pis_cofins_zf) - (i.desconto / 100) * (i.valor+i.pis_cofins_zf) ) * -1),
            (i.valor - (i.desconto / 100) * i.valor )
        )  as decimal(10, 2)
    ) valor_unitario,
      cast (
        IIF( v.registro in (01,70,71,79,83,98,120,122,128,143,154,156,160,164,179,181,184,223,224,22), 
            ((i.valor - (i.desconto / 100) * i.valor ) * I.QUANT + coalesce(i.valoripi, 0)) * -1,
            ((i.valor - (i.desconto / 100) * i.valor ) * I.QUANT + coalesce(i.valoripi, 0))
        ) 
         - (i.icms_zf +i.pis_cofins_zf)
         as decimal(10, 2)
    ) total_mercadoria,
     (i.val_frete + i.totmerc) * -1 total_NF,
    G.GRUPO,
    S.SUBGRUPO,
    i.nfe_cfop as cfop,
    extract(month from  n.DATA) as mes,
    extract(year from  n.DATA) as ano,
    i.lote,
    emp.razaosoc as empresa,i.registro,
    n.fornecedor||' - '|| p.razaosoc cliente,pv.razaosoc vendedor, e.equipe
from compras n
    inner join it_compras i on I.nota = n.REGISTRO
    inner join MATERIAIS M on M.REGISTRO = I.produto
    inner join GRUPOS G on G.REGISTRO = M.GRUPO
    inner join SUBGRUPOS S on S.REGISTRO = M.SUBGRUPO
    inner join TIPO_VENDA V on V.REGISTRO = I.ID_TIPONOTA
    inner join empresas emp on emp.registro=n.empresa
    inner join pessoas p on p.codigo = n.fornecedor
    left join clientes  c on c.pessoa = n.fornecedor
    left join vendedores ven on ven.pessoa = c.vendedor
    left join pessoas pv on pv.codigo = ven.pessoa
    left join equipes e on e.registro = ven.equipe
where
     n.DATA BETWEEN ? and ?
   -- n.DATA >= '21.03.2025'
    --m.codigo='IB117'
    --n.nota = 207631
    --and (c.custo * i.QUANT) is not null
    and n.situacao <> 'C'
    and v.registro in  ( 01,70,71,79,83,98,120,122,128,143,154,156,160,164,179,181,184,223,224,22)