# CALVIN Failure Analysis

[简体中文](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/README.md) · [English](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.en.md) · [日本語](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.ja.md) · [Deutsch](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.de.md) · [Français](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.fr.md) · [Español](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.es.md) · **Português**

Em qual etapa um robô falha quando nenhuma sequência de cinco passos é concluída? O estudo usa o simulador CALVIN e um modelo MCIL público para investigar desvios nas ações e testar a recuperação após falhas. Inclui figuras, dados e um relatório em chinês.

Python · CALVIN · MCIL · [Ver relatório do experimento](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/report.pdf)

Este é um projeto de pesquisa de pequena escala baseado no ambiente de simulação [CALVIN](https://github.com/mees/calvin) e no modelo oficial de pré-treinamento MCIL.

O projeto se concentra nas seguintes questões: **Quando a taxa de sucesso de uma tarefa de robô de longa distância é 0, onde exatamente o robô falha, por que falha e se pode se recuperar após a falha?**

A taxa de sucesso tradicional em nível de tarefa retém apenas o sucesso ou fracasso final e não consegue distinguir entre as seguintes situações:

- O modelo não começa no primeiro passo;
- O modelo pode completar algumas etapas, mas os erros se acumulam nas tarefas subsequentes;
- O modelo compreende a tarefa, mas o controle contínuo se afasta gradualmente;
- O modelo tem sucesso apenas em alguns estados iniciais;
- O modelo não pode se recuperar sozinho após uma falha.

## Processo experimental

1. Reproduza a trajetória real da demonstração para verificar o ambiente, o formato da ação e a determinação do sucesso.
2. Foram testadas três tarefas únicas de abertura do LED, movimentação da porta deslizante para a esquerda e abertura da gaveta respectivamente.
3. Execute 100 sequências fixas de programa de cinco etapas e grave SR@1 em SR@5.
4. Substitua o elo de falha direta do posicionamento através da posição, atitude e ação da garra.
5. Corrigida nova tentativa e continuidade do diagnóstico após falha.

## Principais resultados

| experimentar | resultado |
|---|---:|
| Ligue o LED | 2/9 |
| porta deslizante esquerda | 0/9 |
| gaveta aberta | 0/9 |
| 100 sequências de cinco etapas concluídas com sucesso | 0/100 |
| SR@1 | 1% |
| SR@2—SR@5 | 0% |
| Recuperação de nova tentativa corrigida | 0/10 |
| Continuar a execução após falha | 0/50 passos |

Uma condição de sucesso do LED ainda é concluída na 94ª etapa de ação após a execução independente, indicando que o modelo não é completamente incapaz, mas é sensível ao estado inicial. A comparação dos componentes de ação mostrou que todos os três tipos de tarefas falharam após apenas substituir a ação de posição; quando executado livremente, a distância entre a ação de posição e a trajetória de demonstração expandiu para 72,9-194,2 mm. A caixa de LED também mostrou orientação inconsistente da pinça em etapas importantes.

Resultados experimentais de nível de processo ![](../../figures/process_level_results.png)

## Casos de sucesso e fracasso

| Histórias de sucesso de LED: primeiros passos | História de sucesso de LED: Fim |
|---|---|
| ![](../../figures/led_success_start.png) | ![](../../figures/led_success_end.png) |

| Caso de falha de LED: primeiros passos | Caso de falha do LED: após executar 360 etapas |
|---|---|
| ![](../../figures/led_failure_start.png) | ![](../../figures/led_failure_end.png) |

## Conclusão

Este experimento mostra que a taxa de sucesso no nível da tarefa é adequada para medir a conclusão final, mas não é suficiente para explicar o processo de falha da tarefa a longo prazo. No mínimo, a primeira etapa falhada, a duração da conclusão contínua, o desvio do componente de movimento e os resultados da recuperação também devem ser registrados.

As evidências atuais sustentam que “o desvio de posição em circuito fechado é um elo direto de falha comum aos três tipos de tarefas”, mas não pode ser usado para determinar a única causa dentro do modelo. Esta conclusão se aplica apenas aos pesos públicos, dados de depuração e condições experimentais utilizados neste projeto.

## Estrutura do projeto

```text
.
├── README.md
├── docs/
│   ├── report.pdf                  # Relatório de laboratório chinês
│   └── internship-summary.md       # Resumo do estágio de pesquisa científica
├── figures/                        # Diagrama de resumo e capturas de tela do caso
├── results/                        # Resultados do experimento JSON vs. CSV
└── src/                            # Código de avaliação e diagnóstico
```

Relatório chinês completo: [docs/report.pdf](../../docs/report.pdf)

Para a seleção de questões de pesquisa, trabalhos realizados por mim, processo de depuração e limitações de pesquisa durante o estágio de pesquisa científica, consulte: [docs/internship-summary.md](../../docs/internship-summary.md)

## Instruções de reprodução

O código precisa ser executado no ambiente oficial CALVIN e preparar:

- Ambiente CALVIN com `calvin_models`;
- Dados do ambiente D ou dados oficiais de depuração;
- Ponto de verificação oficial `D_D_static_rgb_baseline` MCIL;
- Python 3.8, PyTorch 1.13.1, PyTorch Lightning 1.8.6 e Hydra 1.1.1.

Entrada principal:

```bash
python src/run_calvin_mcil_cpu.py \
  --dataset-path /path/to/calvin_dataset \
  --train-folder /path/to/D_D_static_rgb_baseline \
  --checkpoint /path/to/mcil_baseline.ckpt \
  --num-sequences 100 \
  --output results/evaluation.json
```

Para fins de avaliação de tarefa única e vários scripts de diagnóstico, consulte [src/README.md](../../src/README.md). Este repositório não redistribui o conjunto de dados CALVIN ou pesos de modelo.

## limites da pesquisa

- Apenas um posto de controle público MCIL foi testado;
- Usa aproximadamente 1,3 GB de dados de depuração, não o conjunto de dados completo;
- Usando inferência de CPU, nenhum experimento real com robôs foi realizado;
- Os resultados são estudos de estágio reproduzíveis e não representam os resultados da classificação oficial da CALVIN.

## Agradecimentos

Este projeto utiliza o ambiente de benchmark CALVIN e seus modelos públicos. Por favor, respeite a licença original do projeto e cite o artigo da CALVIN ao usar dados, ambientes ou modelos relevantes:

> Mees et al., *CALVIN: A Benchmark for Language-Conditioned Policy Learning for Long-Horizon Robot Manipulation Tasks*, IEEE Robotics and Automation Letters, 2022.
