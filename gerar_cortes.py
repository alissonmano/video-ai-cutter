import os
import json
import xml.etree.ElementTree as ET
from faster_whisper import WhisperModel
import requests
import subprocess
import sys

# =====================================================================
# BLINDAGEM DE REDE: Limpa totalmente variáveis de proxy no ambiente
# =====================================================================
for env_var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    if env_var in os.environ:
        del os.environ[env_var]
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
# =====================================================================

# ==========================================
# CONFIGURAÇÕES - AJUSTE AQUI
# ==========================================
VIDEO_PATH = "video_original.mp4"       # Seu vídeo de 1h+
XML_OUTPUT = "cortes_timeline.xml"       # Arquivo final para o DaVinci

# Caminho para a pasta local com os arquivos do Whisper (model.bin, etc.)
MODELO_WHISPER = "./modelo_whisper" 

# Configurações do LM Studio Local
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODELO_LLM = "llama3" 

# Configuração de hardware para o Whisper
DEVICE = "cpu" 
COMPUTE_TYPE = "int8"

# CONFIGURAÇÃO SEMÂNTICA: Tamanho do bloco e margem de contexto repetido
TAMANHO_FATIA = 15000 
OVERLAP_TEXTO = 2500  # Mantém os últimos caracteres do bloco anterior para não perder o gancho
# ==========================================

print("--- Passo 1: Transcrevendo Vídeo Longo (Faster-Whisper Offline) ---")
model = WhisperModel(MODELO_WHISPER, device=DEVICE, compute_type=COMPUTE_TYPE)

segments, info = model.transcribe(VIDEO_PATH, beam_size=5, word_timestamps=True)

transcricao_completa = []
texto_corrido = ""

print("Processando áudio e mapeando diálogos locais...")
for segment in segments:
    texto_corrido += f"[{round(segment.start, 1)}s] {segment.text}\n"
    for word in segment.words:
        transcricao_completa.append({
            "word": word.word.strip(),
            "start": round(word.start, 2),
            "end": round(word.end, 2)
        })

with open("timestamps_cache.json", "w", encoding="utf-8") as f:
    json.dump(transcricao_completa, f, indent=4, ensure_ascii=False)

print(f"Transcrição concluída offline! Total de palavras: {len(transcricao_completa)}")


print("\n--- Passo 2: Análise Semântica Avançada no LM Studio ---")

session = requests.Session()
session.proxies = {'http': '', 'https': ''}

# LÓGICA DE OVERLAP: Fatiamento inteligente com sobreposição contextual
fatias_texto = []
inicio = 0
while inicio < len(texto_corrido):
    fim = inicio + TAMANHO_FATIA
    fatias_texto.append(texto_corrido[inicio:fim])
    inicio += TAMANHO_FATIA - OVERLAP_TEXTO  

cortes_sugeridos = []
print(f"O conteúdo foi segmentado em {len(fatias_texto)} blocos com sobreposição contextual.")

for idx, fatia in enumerate(fatias_texto):
    print(f"-> Analisando bloco {idx + 1} de {len(fatias_texto)} no LM Studio...")
    
    prompt_bloco = f"""
    Você é um editor de vídeo profissional e estrategista de retenção para Shorts, TikTok e Reels.
    Sua missão é rastrear a transcrição abaixo e isolar os melhores momentos de destaque.

    CRITÉRIOS RIGOROSOS DE CORTE E SEMÂNTICA:
    1. INTEGRIDADE DO ASSUNTO: Um corte NUNCA pode terminar no meio de um raciocínio. Identifique o momento exato em que o falante conclui a explicação, responde à pergunta por completo ou muda drasticamente de assunto. É preferível deixar o vídeo um pouco mais longo do que cortá-lo de forma abrupta.
    2. DURAÇÃO ALVO: Busque estruturar trechos consistentes que durem entre 40 e 60 segundos (limite mínimo de 30 segundos).
    3. PONTO DE ENTRADA: O 'tempo_estimado_inicio' deve coincidir perfeitamente com o início de uma frase impactante ou introdução do tópico.

    Transcrição do Trecho:
    {fatia}

    Sua resposta deve ser EXCLUSIVAMENTE um JSON válido no formato de lista, sem textos explicativos adicionais:
    [
      {{"titulo": "Nome Curto e Chamativo", "tempo_estimado_inicio": "120.5", "tempo_estimado_fim": "180.0"}}
    ]
    """
    
    payload = {
        "model": MODELO_LLM,
        "messages": [{"role": "user", "content": prompt_bloco}],
        "temperature": 0.2
    }
    
    try:
        response = session.post(LM_STUDIO_URL, json=payload, timeout=120)
        response.raise_for_status()
        
        resposta_json = response.json()
        resposta_bruta = resposta_json['choices'][0]['message']['content'].strip()
        
        texto_json = resposta_bruta
        if "[" in texto_json:
            texto_json = "[" + texto_json.split("[", 1)[1]
        if "]" in texto_json:
            texto_json = texto_json.rsplit("]", 1)[0] + "]"
            
        dados = json.loads(texto_json)
        
        if isinstance(dados, list):
            cortes_sugeridos.extend(dados)
        elif isinstance(dados, dict):
            for chave, valor in dados.items():
                if isinstance(valor, list):
                    cortes_sugeridos.extend(valor)
                    break
                
    except Exception as e:
        print(f"⚠️ Erro ao processar o bloco {idx + 1}. Pulando bloco...")
        continue

# Remove duplicatas caso o overlap faça a IA pescar o mesmo corte idêntico duas vezes
cortes_unicos = []
vistos = set()
for c in cortes_sugeridos:
    chave_corte = f"{c.get('tempo_estimado_inicio')}-{c.get('tempo_estimated_fim')}"
    if chave_corte not in vistos:
        vistos.add(chave_corte)
        cortes_unicos.append(c)

print(f"\nVarredura contextual finalizada. Total de cortes semanticamente refinados: {len(cortes_unicos)}")


print("\n--- Passo 3: Processamento de Vídeos e Legendas via FFmpeg ---")

def encontrar_segundo_exato(tempo_estimado, mapa_palavras, busca_fim=False):
    try:
        tempo_alvo = float(tempo_estimado)
    except:
        return 0.0
    if not mapa_palavras:
        return tempo_alvo
    palavra_proxima = min(mapa_palavras, key=lambda x: abs(x["start"] - tempo_alvo))
    return palavra_proxima["end"] if busca_fim else palavra_proxima["start"]

def formatar_tempo_srt(segundos_totais):
    horas = int(segundos_totais // 3600)
    minutos = int((segundos_totais % 3600) // 60)
    segundos = int(segundos_totais % 60)
    milisegundos = int(round((segundos_totais - int(segundos_totais)) * 1000))
    if milisegundos >= 1000:
        milisegundos = 999
    return f"{horas:02d}:{minutos:02d}:{segundos:02d},{milisegundos:03d}"

def gerar_legenda_srt(mapa_palavras, t_inicio, t_fim, arquivo_srt_saida):
    palavras_do_corte = [w for w in mapa_palavras if w["start"] >= t_inicio and w["end"] <= t_fim]
    if not palavras_do_corte:
        return

    linhas_srt = []
    indice = 1
    palavras_por_linha = 3 
    
    for i in range(0, len(palavras_do_corte), palavras_por_linha):
        grupo = palavras_do_corte[i:i+palavras_por_linha]
        start_relativo = max(0.0, grupo[0]["start"] - t_inicio)
        end_relativo = max(0.0, grupo[-1]["end"] - t_inicio)
        texto_linha = " ".join([w["word"] for w in grupo])
        
        linhas_srt.append(f"{indice}")
        linhas_srt.append(f"{formatar_tempo_srt(start_relativo)} --> {formatar_tempo_srt(end_relativo)}")
        linhas_srt.append(f"{texto_linha}\n")
        indice += 1

    with open(arquivo_srt_saida, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas_srt))

def cortar_videos_diretamente(video_path, lista_cortes, mapa_palavras):
    if not lista_cortes:
        print("❌ Nenhum corte foi minerado para processamento.")
        return

    pasta_saida = "Cortes_Prontos_IA"
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)

    ffmpeg_bin = r"C:\Users\m1730308\AppData\Local\ffmpegio\ffmpeg-downloader\ffmpeg\bin\ffmpeg.exe"
    cortes_exportados = 0

    for idx, corte in enumerate(lista_cortes):
        try:
            bruto_in = corte.get("tempo_estimado_inicio", corte.get("tempo_estimated_inicio", 0))
            bruto_out = corte.get("tempo_estimado_fim", corte.get("tempo_estimated_fim", 0))
            
            t_in_seg = encontrar_segundo_exato(bruto_in, mapa_palavras, busca_fim=False)
            t_out_seg = encontrar_segundo_exato(bruto_out, mapa_palavras, busca_fim=True)
            
            if t_out_seg <= t_in_seg:
                continue
                
            # Margem de folga integrada para garantir transições limpas
            FOLGA_INICIO = 1.0  
            FOLGA_FIM = 2.0     
            
            t_in_refinado = max(0, t_in_seg - FOLGA_INICIO)
            t_out_refinado = t_out_seg + FOLGA_FIM
            duracao_seg = t_out_refinado - t_in_refinado
            
            titulo_limpo = "".join([c for c in corte.get('titulo', f'Corte_{idx}') if c.isalnum() or c in (' ', '_', '-')]).rstrip()
            nome_base = os.path.join(pasta_saida, f"{cortes_exportados+1:03d} - {titulo_limpo}")
            
            nome_arquivo_saida = f"{nome_base}.mp4"
            nome_arquivo_srt = f"{nome_base}.srt"
            
            comando = [
                ffmpeg_bin, '-y',
                '-ss', str(t_in_refinado),
                '-i', video_path,
                '-t', str(duracao_seg),
                '-c', 'copy',
                nome_arquivo_saida
            ]
            subprocess.run(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            gerar_legenda_srt(mapa_palavras, t_in_refinado, t_out_refinado, nome_arquivo_srt)
            
            print(f"🎬 Pronto: '{nome_arquivo_saida}' (Refinado e Legendado) [{duracao_seg:.1f}s]")
            cortes_exportados += 1
            
        except Exception as e:
            print(f"⚠️ Não foi possível processar o trecho {idx+1}: {e}")
            continue

    print(f"\n✅ Concluído! {cortes_exportados} vídeos gerados (sem exclusão de tamanho) na pasta: .\\{pasta_saida}\\")

cortar_videos_diretamente(VIDEO_PATH, cortes_unicos, transcricao_completa)