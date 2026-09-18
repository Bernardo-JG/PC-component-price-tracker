# Hardware flipping tracker — OLX.pt / Vinted.pt

Tracker local para **revisão manual**, sem mensagens a vendedores ou compras.
Python 3.10+ no Linux/Nobara, biblioteca padrão. A aplicação ativa está na raiz;
`gpu_tracker/` é uma versão antiga, não usar para este pipeline.

## Executar

```bash
export TRACKER_OLLAMA_URL=http://127.0.0.1:11434
export TRACKER_TEXT_MODEL=qwen3.8-27b-iq3s
python main.py --sites olx --queries 'RX 6600' --pages 1 --db /tmp/tracker-test.db --out /tmp/tracker-report --no-open
python main.py --sites vinted --queries 'placa grafica' --pages 1 --no-open
python main.py report --no-open
```

Por defeito recolhe OLX, com as pesquisas de `config.py`. Cada anúncio exige uma
inferência local; começar por uma pesquisa/página. Vinted pode devolver 403: fica
registado no estado da recolha e não há bypass. `--sites olx vinted` ativa ambas.
Preços são preços pedidos, não preços de transações, sem portes/taxas.

## Pipeline comum

1. Regex produz candidatos, nunca uma decisão definitiva.
2. Ollama interpreta título/descrição em português (incluindo objeto vendido vs compatibilidade).
3. Visão opcional apenas quando o modelo pede ajuda e falta identificação/especificação necessária.
4. Validação fechada do JSON e das citações; elegibilidade calculada pelo código e revalidada na escrita.

Contrato em `classification/schema.py`. Modelo devolve `kind` (component, accessory,
bundle, wanted, ambiguous), categoria, marca/modelo ou null, especificações nullable,
`functional_condition` (unknown, untested, working, defective), evidências por campo,
`needs_visual` e `abstain`. Evidência textual é excerto literal; evidência visual inclui
índice de imagem e texto lido na etiqueta. Identificação visual não substitui texto
explícito, não demonstra funcionamento e não promove um anúncio ambíguo a venda confirmada.

O resultado armazenado acrescenta versão, modelo usado, data, hash de entrada,
candidatos das regras, erro, estado da visão e `comparison` com elegibilidade,
motivo de exclusão e chave de comparação. **Preço nunca é pedido ao modelo**.
A base conserva texto, imagens e resultado JSON para auditoria.

Entram nas medianas apenas componentes identificados, sem abstenção/erros, com
funcionamento explicitamente anunciado, estado new/used conhecido e especificações
necessárias. GPU exige VRAM explícita; RAM exige geração/capacidade/layout/velocidade/formato.
CPU exige modelo explícito. Desconhecido, não testado, avaria, acessórios, bundles e
procura ficam para revisão manual, excluídos. Campos desconhecidos continuam null.
As comparações separam plataforma, moeda EUR, categoria, modelo, especificações,
estado de venda e funcional. Exigem quatro anúncios no período de 30 dias;
um ID contribui apenas uma vez. O relatório inclui também os excluídos e os motivos.
As declarações do vendedor e a interpretação dos modelos ainda exigem confirmação humana.

## Memória e backend visual

Uma fila/bloqueio partilhado por threads e processos permite **uma inferência** de
cada vez. `TRACKER_INFERENCE_LOCK` pode configurar o ficheiro de bloqueio (todos os
processos devem usar o mesmo). O cliente usa `keep_alive: 0`, pede descarregamento e
verifica `/api/ps`. Recusa iniciar se outro modelo Ollama estiver residente ou se o
endpoint visual estiver ocupado. Outros programas externos não seguem este bloqueio:
não executar inferências paralelas fora do tracker.

O tracker inicia e termina o llama-server por pedido visual. Nunca assume que texto
e visão cabem simultaneamente. Configurar um comando JSON, sem shell:

```bash
export TRACKER_VISUAL_URL=http://127.0.0.1:8080
export TRACKER_VISUAL_MODEL=local-vision
export TRACKER_VISUAL_COMMAND='["llama-server","-m","/caminho/model.gguf","--mmproj","/caminho/mmproj.gguf","--host","127.0.0.1","--port","8080","-c","8192","-ngl","99","--alias","local-vision"]'
export TRACKER_MODEL_TIMEOUT=240
```

Usar o binário/argumentos que já funcionam no Nobara. `-ngl` e contexto podem precisar
de ajuste para 16 GB. Sem comando, visão fica desativada e lacunas necessárias
excluem o anúncio. Erro visual exclui a classificação; abstenção mantém desconhecidos.
No máximo duas imagens, 8 MB cada, de hosts OLX/Vinted, sem redirects.
O servidor externo já aberto deve ser parado pelo utilizador; o tracker só encerra
processos que iniciou. Falha de limpeza bloqueia inferências seguintes nesse cliente.

## Dados existentes

Fazer cópia de segurança antes do primeiro uso com a base existente. Migração aditiva,
sem apagar preços/histórico. Anúncios antigos não entram nas medianas sem nova validação:

```bash
python main.py reclassify --limit 20 --no-open
```

A reclassificação não altera a data da última recolha nem inventa nova observação.
O relatório anterior só é substituído quando executar o programa. Não executar a versão
antiga sobre a base migrada. As alterações locais pré-existentes de base/relatório não
fazem parte desta implementação.

## Testes reproduzíveis

```bash
python -m unittest discover -s tests -v
python scripts/validate_models.py tests/fixtures/synthetic/cases.json --out /tmp/synthetic-results.json
python scripts/validate_models.py tests/fixtures/olx/*.json --out /tmp/olx-results.json
python scripts/validate_models.py tests/fixtures/vinted/real_indexed.json --out /tmp/vinted-historical-results.json
python -m scrapers.vinted --query 'placa grafica' --max-details 3
```

Os testes unitários usam doubles de modelos e não provam a qualidade da inferência.
O script de validação chama os modelos reais, guarda os resultados incrementalmente e
retorna código 1 em erros/divergências das expectativas. Fixtures OLX guardam respostas
reais da API com URL/data; Vinted guarda excertos **históricos indexados**, separados
porque a API devolveu 403 e os anúncios já estavam retirados. Não são inventário atual.
Casos sintéticos são explicitamente identificados em `tests/fixtures/synthetic/`.
Ver `docs/olx-validation.md`, `docs/vinted-validation.md` e `docs/validation.md`.

Referências do cliente: [Ollama chat](https://docs.ollama.com/api/chat),
[Ollama unload](https://docs.ollama.com/api/generate),
[llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server).
