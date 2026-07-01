\# Video AI Cutter 🎬🤖



Este projeto automatiza completamente o processo de mineração e corte de melhores momentos (Shorts/Reels/TikToks) a partir de vídeos longos ou transmissões ao vivo. Ele utiliza inteligência artificial local para transcrever o áudio, analisar o contexto semântico e fatiar os arquivos de mídia com precisão física e geração de legendas dinâmicas.



\## 🚀 Funcionalidades



\- \*\*Transcrição Offline de Alta Precisão:\*\* Usa o `Faster-Whisper` localmente para mapear diálogos e carimbos de tempo palavra por palavra.

\- \*\*Análise Semântica Avançada:\*\* Segmenta a transcrição e utiliza LLMs locais (via LM Studio) com inteligência de sobreposição (\*overlap\*) para encontrar ganchos de retenção sem cortar frases pela metade.

\- \*\*Corte Físico Ultra Rápido:\*\* Utiliza o `FFmpeg` por cópia direta de fluxo (`-c copy`), realizando os cortes quase instantaneamente e com perda zero de qualidade.

\- \*\*Legendas Dinâmicas Estilo Shorts:\*\* Gera arquivos `.srt` sincronizados automaticamente, agrupando as palavras de 3 em 3 para gerar alto impacto visual.

\- \*\*Blindagem de Rede:\*\* Configurado para ignorar variáveis de proxy locais que costumam travar requisições de APIs internas.



\---



\## 🛠️ Pré-requisitos



Antes de rodar o script, certifique-se de ter instalado e configurado na sua máquina:



1\. \*\*Python 3.8 ou superior\*\*

2\. \*\*LM Studio\*\* rodando localmente com um modelo de sua preferência (ex: `Llama 3`, `Mistral`, etc.) e o servidor de inferência local ativo em `http://127.0.0.1:1234`.

3\. \*\*Pasta do Modelo Whisper:\*\* O script espera uma pasta chamada `./modelo\_whisper` na raiz do projeto contendo os arquivos binários do modelo (como `model.bin`).



\---



\## 📦 Instalação e Configuração



Abra o terminal na pasta do projeto e siga os passos abaixo:



\### 1. Instalar as Dependências do Python

```powershell

pip install faster-whisper requests ffmpeg-python ffmpeg-downloader

2\. Baixar e Registrar o Executável do FFmpeg

Para garantir que o Windows encontre o cortador de vídeo corretamente sem depender das Variáveis de Ambiente globais do sistema, execute o downloader oficial do ecossistema:



PowerShell

python -m ffmpeg\_downloader install --add-path

Nota: O script já está configurado para ler o caminho absoluto padrão onde este utilitário salva o arquivo ffmpeg.exe.



⚙️ Como Usar

Cole o seu arquivo de vídeo longo na raiz da pasta e mude o nome dele para video\_original.mp4 (ou mude a variável VIDEO\_PATH no topo do código).



Certifique-se de que o LM Studio está aberto com o servidor local ligado.



Execute o script principal:



PowerShell

python .\\gerar\_cortes.py

📁 Resultado

Após o processamento terminar, uma nova pasta chamada Cortes\_Prontos\_IA/ será criada na raiz. Dentro dela, você encontrará os arquivos emparelhados:



001 - Titulo\_do\_Corte.mp4 (O corte de vídeo físico pronto)



001 - Titulo\_do\_Corte.srt (A legenda dinâmica sincronizada com o início do corte)



📄 Estrutura do Repositório



video-ai-cutter/

│

├── gerar\_cortes.py       # Script principal de automação

├── .gitignore            # Bloqueador de mídias pesadas e caches para o Git

└── README.md             # Documentação do projeto

