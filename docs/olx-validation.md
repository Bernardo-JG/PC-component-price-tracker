# OLX.pt: captura e validação

Em 2026-09-18 foram consultados anúncios públicos reais em português através de HTTP GET do endpoint `https://www.olx.pt/api/v1/offers/{id}/`. Os três pedidos responderam HTTP 200. A primeira tentativa no sandbox falhou por DNS; os pedidos com acesso de rede autorizado funcionaram. A pesquisa web serviu apenas para descobrir URLs; os fixtures são excertos das respostas reais da API, não transcrições inventadas nem payloads construídos a partir de snippets.

| Fixture | URL | Preço recolhido | Caso |
| --- | --- | --- | --- |
| cooler_accessory.json | https://www.olx.pt/d/anuncio/capa-cooler-rtx-3080-msi-ventus-3x-IDJqzWK.html | 10 EUR | Capa plástica de cooler; não uma RTX 3080 completa |
| water_damaged_gpu.json | https://www.olx.pt/d/anuncio/rtx-2060-avariada-IDJfZ36.html | 60 EUR | RTX 2060 explicitamente avariada por água |
| complete_pc_bundle.json | https://www.olx.pt/d/anuncio/pc-gaming-rtx-3060-i7-12700kf-16gb-ram-1tb-ssd-water-cooler-IDIIGR1.html | 790 EUR | PC completo; preço não atribuível isoladamente à RTX 3060 |

Os fixtures em `tests/fixtures/olx/` guardam URL, data de consulta, título, descrição, preço e outros campos necessários ao adaptador. Foram omitidos identidade/contacto do vendedor e campos não relevantes. `expected` contém anotação humana do caso; não representa saída de modelo nem comprovação de inferência. A descrição original, incluindo HTML e especificações truncadas pelo próprio anunciante, é preservada. As imagens são URLs reais da API, com dimensões de template resolvidas pelo adaptador e dimensão máxima de 1024 px; não foram usadas para afirmar marca ou especificações.

## O que foi testado

`python -m unittest discover -s tests -p test_olx_adapter.py -v`

6 testes passaram. Um teste percorre os três payloads reais e verifica preço/descrição/imagens entregues à interface comum. Os restantes são explicitamente sintéticos: estado ausente, URLs inválidos, preço não monetário, anúncios de acessórios/procura/bundles encaminhados para classificação e paginação simulada. O método partilhado `build_listing` é substituído por um spy nestes testes para isolar o contrato do adaptador. Isto **não valida o modelo de linguagem ou o modelo visual**.

Os anúncios reais servem para reprodução offline; podem entretanto expirar ou mudar de preço. Não se atribui a um anúncio real texto inventado de casos como «caixa de RTX 2060» ou «procuro RX 6600»: estes casos são sintéticos.

## Repetir no Nobara

```bash
python -m unittest discover -s tests -p test_olx_adapter.py -v
curl --fail --max-time 25 'https://www.olx.pt/api/v1/offers/671269768/' -o /tmp/olx-cooler-current.json
curl --fail --max-time 25 'https://www.olx.pt/api/v1/offers/668744716/' -o /tmp/olx-broken-current.json
curl --fail --max-time 25 'https://www.olx.pt/api/v1/offers/660809951/' -o /tmp/olx-pc-current.json
```

A avaliação real com Ollama/llama.cpp usa o comando comum documentado no README da integração. Os testes aqui descritos não contactam os modelos locais.
