# Projecto IA 2026 - Grupo 05 (Laboral)

P5 - Drone de pulverização agrícola em terreno 3D com vento. Algoritmo avançado: ARA*.

O drone parte da base, pulveriza todas as parcelas no nível 1 e regressa à base,
gastando o mínimo de energia. A busca tem em conta o relevo, as zonas proibidas,
o vento, a bateria (com recarga na base e em duas estações) e o tanque
(reabastecido só na base).

## Requisitos

- Windows 10 ou 11
- Python 3.10 ou superior (testado com 3.14)
- Bibliotecas: `pytest`, `matplotlib`, `pandas` (em `requirements.txt`, com versões mínimas).
  Testado com Python 3.14.7, pytest 9.2.0, matplotlib 3.11.2 e pandas 3.1.0.

## Instalação (PowerShell)

Na pasta do projecto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Se o PowerShell recusar o `Activate.ps1` por causa da política de execução, corre
uma vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` ou usa directamente
`.\.venv\Scripts\python.exe` em vez de `python` nos comandos seguintes.

Na Linha de Comandos (cmd) a activação é `.venv\Scripts\activate.bat`.

Se os acentos aparecerem trocados na consola, corre `chcp 65001` antes do programa.

## Execução

| Comando | O que faz |
|---|---|
| `python main.py` | Menu: escolher instância (ficheiro ou gerada), algoritmo, heurística e limites; mostra métricas e a solução passo a passo |
| `python gerador.py` | Gera as 30 instâncias (`instancias/pequena_XX.json`, `media_XX.json`, `grande_XX.json`) com a semente 202605 |
| `python experiencias.py` | Corre todos os algoritmos em todas as instâncias e gera CSV e gráficos em `resultados/` |
| `python experiencias.py --niveis pequena` | Só um nível (`base`, `pequena`, `media`, `grande`) |
| `python experiencias.py --estudo-delta` | Mesmas instâncias com Δ = 0,25; 0,5 e 1 (`resultados/estudo_delta.csv`) |
| `python experiencias.py --estudo-vento` | Mesmo mapa com quatro direcções de vento (`resultados/estudo_vento.csv`) |
| `python experiencias.py --graficos` | Refaz gráficos e tabelas a partir dos CSV existentes |
| `python -m pytest` | Corre os testes |

Cada execução tem limite de 60 s e 2 GB. Uma execução que excede o limite fica
registada como `falhou_tempo` ou `falhou_memoria`; o ARA* que já tenha uma
solução fica como `limite`, com o respectivo ε'. Como muitas execuções só param
no limite de 60 s, a bateria completa é longa; convém corrê-la sem outros
programas pesados abertos, porque os tempos medidos dependem da carga da máquina.

`resultados/execucao_<modo>.json` regista a data, a versão do Python, o commit e se
havia alterações por commitar quando as experiências correram.

## Estrutura

| Ficheiro | Conteúdo |
|---|---|
| `problema.py` | Classe abstracta `Problema`, classe `No` e `caminho(no)` |
| `dominio.py` | `DronePulverizacao`: estado, acções, transições, custos, poda e desenho ASCII |
| `heuristicas.py` | h1 e h2 (limite do percurso por programação dinâmica em subconjuntos) |
| `buscas.py` | BFS, DFS, IDS, UCS, Gulosa, A*, ARA*, controlo de limites e métricas |
| `gerador.py` | Geração de instâncias com a semente do grupo |
| `experiencias.py` | Bateria de experiências, CSV e gráficos |
| `main.py` | Menu |
| `instancias/` | `base.json` e as instâncias geradas |
| `resultados/` | CSV e gráficos das experiências |
| `tests/` | Testes `pytest` |

## Modelo (resumo)

Os valores abaixo que não estão no enunciado são decisões do grupo e estão
justificados no relatório.

- Grelha 20 × 20 × 5. `x` cresce para Este, `y` para Norte, níveis 1 a 5.
- Estado: `(x, y, z, bateria, litros, feitas)`, com a bateria em unidades de
  Δ = 0,25 e `feitas` como máscara de bits das parcelas.
- Acções: 8 movimentos horizontais, subir, descer, pulverizar, recarregar, reabastecer.
- Custo de um movimento horizontal: `|m| · (1 + 0,5 cos θ)`, θ entre o movimento e
  o vento contrário. O vento é indicado pela direcção de onde vem: `"vento": "E"`
  é vento de Leste e voar para Este custa 1,5. Subir custa 2 e descer 0,5.
- Recarregar, pulverizar e reabastecer custam 0 de energia. O enunciado só dá
  a duração da recarga (15 unidades de tempo) e não a dos movimentos, por isso
  não se calcula tempo de voo; o custo do caminho é a energia total.
- Cada acção gasta `ceil(custo/Δ)` unidades de bateria. Os "custos óptimos"
  referem-se a este modelo discreto.
- Não são gerados estados a partir dos quais a bateria já não chega a nenhum
  ponto de recarga (a solução tem de acabar na base).

### Heurísticas

- **h1** não usa a direcção do vento: cada movimento horizontal vale 0,5 por
  unidade de comprimento (o menor factor possível).
- **h2** usa o custo real de cada movimento, com o vento da instância.

As duas calculam, por programação dinâmica, o melhor plano para pulverizar as
parcelas pendentes e regressar à base ignorando só a bateria: os troços usam
distâncias mínimas com obstáculos e relevo (Dijkstra sobre as posições) e o
plano inclui os regressos à base para reabastecer.
São admissíveis e consistentes (provas no relatório; verificadas pelos testes
em todos os estados alcançáveis de instâncias reduzidas). h2 ≥ h1.

## Instância base

`instancias/base.json` foi **criada pelo grupo**; o enunciado não fornece mapa
para o P5. Tem 6 parcelas, base, duas estações, aldeia, linha de alta tensão,
relevo e vento de Leste.

Custo óptimo (energia, Δ = 0,25): **119,0122**, com 111 acções. Obtido por A\*(h2)
e confirmado pelo ARA\*(h2), que termina com ε' = 1 e o mesmo custo.

## Testes

```powershell
python -m pytest
```

Os testes usam instâncias reduzidas (definidas em `tests/conftest.py`) para
poder enumerar todos os estados. Não são instâncias experimentais.
