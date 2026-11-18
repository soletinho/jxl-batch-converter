# JXL Batch Converter ⚡

Um conversor e otimizador em lote de imagens para o formato de última geração **JPEG XL (.jxl)**, desenvolvido em Python para Windows, Linux e macOS.

Possui interface gráfica moderna (GUI) intuitiva e interface por linha de comando (CLI), oferecendo transcodificação sem perdas (lossless) para JPGs e PNGs, compressão personalizada de alta fidelidade e relatórios detalhados de economia de armazenamento (em HTML, CSV e terminal).

---

## Principais Recursos

- **Modo Lossless Transcoding:** Transcodifica arquivos JPEG existentes diretamente para JPEG XL sem nenhuma perda matemática de qualidade (*0 gen loss*), economizando tipicamente de 20% a 30% de espaço.
- **Suporte Amplo de Formatos:** Converte `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`, `.tif`, `.tiff`.
- **Interface Gráfica Desktop (GUI):**
  - Seleção de pasta de origem com suporte opcional a subpastas (recursivo).
  - Opção para salvar arquivos JXL na mesma pasta ou espelhar a estrutura em uma pasta separada.
  - Controle de qualidade (Lossless ou slider de qualidade visual 60–98).
  - Gestão de segurança dos originais: manter intactos ou excluir após conversão confirmada.
  - Barra de progresso em tempo real e tabela detalhada por arquivo.
- **Relatório Completo de Economia:**
  - Painel com espaço total economizado (em MB/GB) e percentual de redução.
  - Exportação de relatório em **HTML** moderno e interativo para abrir no navegador.
  - Exportação de relatório em planilha **CSV**.
- **Binários Automáticos:** No Windows, a aplicação detecta e obtém automaticamente as ferramentas estáticas oficiais do projeto `libjxl` (`cjxl.exe`).
- **Modo Linha de Comando (CLI):** Automatize conversões via scripts e terminal com argumentos flexíveis.

---

## Instalação e Execução

### 1. Clonar o repositório
```bash
git clone https://github.com/soletinho/jxl-batch-converter.git
cd jxl-batch-converter
```

### 2. Instalar dependências (opcional)
A aplicação foi projetada para rodar com a biblioteca padrão do Python. Para testes ou manipulações adicionais:
```bash
pip install -r requirements.txt
```

### 3. Iniciar a Interface Gráfica
Para abrir a janela do programa:
```bash
python main.py
```

---

## Uso por Linha de Comando (CLI)

Você também pode utilizar a ferramenta diretamente no terminal:

```bash
# Conversão sem perdas (lossless) em uma pasta:
python main.py -i "C:\MinhasFotos"

# Conversão com saída em outra pasta:
python main.py -i "C:\Origem" -o "D:\FotosJXL"

# Ajustar qualidade personalizada (ex.: 88) e exportar relatórios:
python main.py -i "C:\Imagens" -q 88 --report-html "relatorio.html" --report-csv "relatorio.csv"

# Ver todas as opções disponíveis:
python main.py --help
```

### Argumentos da CLI:
- `-i`, `--input`: Pasta contendo as imagens para converter (obrigatório).
- `-o`, `--output`: Pasta de destino dos arquivos `.jxl` (opcional).
- `-q`, `--quality`: `lossless` (padrão) ou valor entre 1 e 100.
- `-e`, `--effort`: Nível de esforço do encoder (1 a 10, padrão: 7).
- `--no-recursive`: Converte apenas a raiz da pasta, sem verificar subpastas.
- `--delete-originals`: Remove os arquivos originais após conversão bem-sucedida.
- `--report-html`: Gera relatório visual em HTML.
- `--report-csv`: Gera relatório em planilha CSV.

---

## Executando os Testes Automatizados

Para rodar a suíte de testes unitários e de integração:
```bash
python -m unittest tests/test_converter.py
```

---

## Licença

Distribuído sob a licença open-source MIT.
