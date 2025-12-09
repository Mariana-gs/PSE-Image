# Manual de Uso: PSE-Image 

O **PSE-Image** é uma ferramenta visual para processamento de imagens baseada em fluxo (pipeline). O usuário constrói um algoritmo conectando blocos que realizam operações sequenciais sobre imagens digitais.

---

## 1. Comandos Básicos e Interface

A interface é composta por uma área de trabalho (canvas) central e um painel de "Propriedades" à esquerda.

* **Adicionar Blocos:** Clique com o **Botão Direito** no fundo da área de trabalho para abrir o menu de blocos disponíveis.
* **Mover o Canvas:** Clique e segure o **Botão do Meio (Scroll)** do mouse para arrastar a visualização.
* **Seleção:** Clique com o **Botão Esquerdo** em um bloco ou fio para selecioná-lo (itens selecionados ficam com borda laranja).
* **Apagar:** Selecione um bloco ou fio e pressione `Delete` ou `Backspace`.
* **Conectar:** Clique em um conector (bolinha vermelha/azul) e arraste até outro conector compatível para criar um fio.

---

## 2. Passo a Passo: Criando um Fluxo

### Passo 1: Carregar a Imagem
1.  Adicione o bloco **"Leitura de arquivo RAW"**.
2.  Com o bloco selecionado, vá ao painel de **Propriedades**:
    * **Formato:** Escolha *Imagem (JPG/PNG)* para imagens comuns ou *RAW* para arquivos binários puros.
    * **Resolução:** Se usar RAW, defina a `Largura` e `Altura` manualmente (ou use a lista de resoluções sugeridas).
3.  Clique em **"Carregar Arquivo"**.

### Passo 2: Adicionar Filtros e Processamento
1.  Adicione um bloco de processamento (ex: **"Máscara de Convolução"** ou **"Processamento Pontual"**).
2.  Conecte a saída do bloco de *Leitura* na entrada do bloco de *Processamento*.
3.  Ajuste os parâmetros no painel lateral (ex: escolha um preset "Laplaciano") e clique em **"Aplicar parâmetros"**.

### Passo 3: Visualizar 
1.  Adicione o bloco **"Exibição de imagem"**.
2.  Conecte a saída do seu último bloco na entrada deste.
3.  **Importante:** Clique no botão **"Processar Fluxo"** na barra de ferramentas superior para executar a lógica. A imagem só aparecerá após o processamento.

### Passo 4: Salvar o Resultado
1.  Adicione o bloco **"Gravação de arquivo RAW"** ao final do fluxo.
2.  Execute o fluxo novamente (**"Processar Fluxo"**).
3.  Selecione o bloco de gravação e verifique se o status é "Dados prontos".
4.  Clique em **"Salvar Arquivo (.RAW)"**.

---

## 3. Detalhes dos Blocos

### Processamento Pontual
Realiza operações matemáticas pixel a pixel.
* **Brilho:** Soma um valor constante aos pixels (clarear/escurecer).
* **Limiar (Threshold):** Binariza a imagem. Pixels acima do limiar viram brancos (255), abaixo viram pretos (0).

### Máscara de Convolução (Filtros Espaciais)
Aplica uma matriz (kernel) sobre a imagem.
* **Média:** Suavização (blur).
* **Mediana:** Remoção de ruído (tipo sal e pimenta).
* **Laplaciano:** Detecção de bordas.
* **Personalizado:** Permite digitar uma matriz manual na caixa de texto.

### Diferença entre Imagens
Compara duas imagens (Entrada A e B).
* Gera uma imagem resultante da subtração absoluta (`|A - B|`).
* **Métricas:** No painel lateral, é possível visualizar o **MSE** (Erro Quadrático Médio) e **PSNR** após o processamento.

### Plotagem de Histograma
Analisa a distribuição de tons de cinza.
* Gera um gráfico de barras estatístico.
* O gráfico pode ser salvo como imagem PNG através do botão **"Baixar Gráfico"**.

---

