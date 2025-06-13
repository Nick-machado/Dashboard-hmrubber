with
Custo AS (
    select M.REGISTRO, m.reg_material, M.REG_EMPRESA,
        (select first 1 P.VALOR 
         from PRECO_MEDIO_DIA P
         where P.ID_MATERIAL = M.REGISTRO 
         and P.ID_EMPRESA = M.REG_EMPRESA 
         order by P.DATA desc) custo
    from MATERIAIS_COMPL M
   --  where m.reg_material= 2331
    group by M.REGISTRO, M.REG_EMPRESA, reg_material
)
select distinct
    n.DATA,
   -- M.REGISTRO,
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
   -- i.valor ,
   -- i.pis_cofins_zf,
  --  i.icms_zf,
  --  i.transp_valor as totalimpostos,

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
    cast (  (i.icms_zf +i.pis_cofins_zf)   as decimal(10,2))VLRZF,
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

 --  cast( ((i.valor - (i.desconto / 100) * i.valor) ) as decimal (10,2)) as desconto,
  cast( IIF( v.registro in (9),
    (c.custo * i.QUANT)*-1 ,(c.custo * i.QUANT)) as decimal(10,2)) AS CMV,
    cast(
        case 
            when ((i.valor - (i.desconto / 100) * i.valor) * I.QUANT) = 0 then 0
            else (((i.valor - (i.desconto / 100) * i.valor) * I.QUANT) - 
                 (c.custo * i.QUANT + i.valoricm +
                 (I.NFE_VFRETE + I.NFE_VSEGURO + I.NFE_VDESPESAS) +
                 iif( i.NFE_VFRETE = 0, (i.baseicm / n.totmerc) * n.valor_frete_pago, i.NFE_VFRETE ) +
                 (i.valor_pis + i.valor_cofins) + 
                 ((((i.valor - (i.desconto / 100) * i.valor)) * I.QUANT) * (i.comissao / 100))))
        end as decimal(15,2)
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
   n.DATA BETWEEN ? and ?
--n.DATA = '16.01.2025'
    -- n.nota =  80
 -- m.codigo='IB117'
   -- and   n.nota = 1015
   -- and (c.custo * i.QUANT) is not null
    and n.situacao <> 'C'
   and v.registro in  ( 01,70,71,79,83,98,120,122,129,143,154,156,160,164,179,181,184,223,224,22)