# Vinted: recolha e validação

O adaptador `scrapers.vinted.VintedScraper` produz anúncios brutos através da interface comum. Não classifica componentes nem estima preços. Pesquisa a API web pública de Vinted.pt, com paginação limitada, e solicita detalhes quando o catálogo não inclui a descrição. O limite padrão é de 20 pedidos de detalhe por pesquisa; o diagnóstico indica quando a cobertura fica limitada. Falhas HTTP interrompem a pesquisa, sem tentativas de contornar bloqueios. Os resultados obtidos antes de uma falha continuam disponíveis através do coletor base.

A API web não é documentada como API pública estável. A integração foi testada com respostas sintéticas quanto ao contrato e à gestão de falhas; a compatibilidade com o serviço ao vivo **não foi validada**. Não é necessário nem solicitado um cookie privado. Se o serviço bloquear o acesso, fica indisponível e isso deve aparecer no diagnóstico.

A moeda vem do anúncio; não é assumido EUR. O preço é `price.amount`, nunca o valor com Proteção do Comprador. Etiquetas de estado são conservadas literalmente na descrição como “Estado anunciado (Vinted)”. Apenas etiquetas conhecidas em português e inglês são mapeadas para estado de venda `new` ou `used`; etiquetas ausentes, numéricas ou desconhecidas ficam `unknown`. “Muito bom” não é prova de funcionamento: a condição funcional continua a exigir evidência textual explícita no classificador partilhado. Artigos vendidos, ocultos, reservados ou fechados são omitidos quando estes indicadores existem. Não existem operações de compra ou mensagens.

## Evidência real e limitações (2026-09-18)

Tentativa direta: `https://www.vinted.pt/api/v2/catalog/items?search_text=placa+grafica&per_page=2&page=1` devolveu **HTTP 403 Forbidden** após uma primeira tentativa sem acesso DNS no sandbox. As páginas individuais também não abriram na ferramenta web. Não foram feitas tentativas de contornar o bloqueio.

A pesquisa web encontrou dois anúncios reais portugueses no índice histórico, guardados em `tests/fixtures/vinted/real_indexed.json` com URL, data de observação, excertos mínimos e limitações:

- [RX 5700 com defeito](https://www.vinted.pt/items/6538968398-placa-grafica-rx-5700-8gb-gddr6-defeito): preço anunciado indexado de 80 EUR, defeito explícito. O índice mostra o artigo retirado. Serve como caso histórico de linguagem portuguesa, nunca como inventário atual.
- [Gigabyte RTX 3080 10GB](https://www.vinted.pt/items/6538912763-gigabyte-rtx-3080-10gb): só título recuperável, sem preço nem descrição. O preço fica nulo e não pode alimentar comparações.

O índice indicava recolha há 1,2 anos; a data exata da publicação não foi recuperada. Estes exemplos não são respostas da API, não demonstram disponibilidade atual e não foram submetidos a um modelo real pelo agente Vinted. A fixture não deve ser importada como anúncio ativo. Os onze testes de transporte/contrato são sintéticos; o décimo segundo verifica apenas a integridade da evidência histórica, não a classificação por IA.

## Executar no Nobara

A partir da raiz da branch integrada:

```bash
python -m unittest discover -s tests -p test_vinted_adapter.py -v
python -m scrapers.vinted --query 'placa grafica' --max-details 3
python -m scrapers.vinted --query 'rtx 3080' --max-details 3
```

O probe só imprime JSON bruto e diagnósticos, não grava na base de dados nem chama os modelos. Em caso de bloqueio termina com código 1; não interpretar isto como ausência de anúncios. Para testar os modelos, usar o comando de classificação/validação documentado na integração partilhada, com os exemplos reais explicitamente marcados como históricos e os testes sintéticos separados.
