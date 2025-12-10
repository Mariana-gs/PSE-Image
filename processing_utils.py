# processing_utils.py
import numpy as np
from io import BytesIO

def ensure_uint8(img):
    """Garante que o array seja np.uint8 e 2D (grayscale)."""
    if img is None:
        return None
    a = np.array(img) # converte para array numpy
    if a.ndim == 3 and a.shape[2] in (3,4): # RGB ou RGBA
        # converte para grayscale simples pela média
        a = np.mean(a[..., :3], axis=2) # ignora alpha se presente
    a = np.clip(a, 0, 255) # limita valores
    return a.astype(np.uint8)

def adjust_brightness(img, delta):
    """Adiciona delta (pode ser negativo)."""
    img = ensure_uint8(img)
    if img is None: return None
    out = img.astype(np.int16) + int(delta) #soma delta a cada pixel
    out = np.clip(out, 0, 255).astype(np.uint8) #limita para 0-255
    return out

def threshold(img, t, high_value=255, low_value=0):
    """Limiar binário: >= t -> high_value else low_value."""
    img = ensure_uint8(img)
    if img is None: return None
    out = np.where(img >= t, high_value, low_value).astype(np.uint8) # aplica limiar t
    return out

def pad_for_kernel(img, k_h, k_w, mode='edge'):
    # O Padding cria uma borda artificial para que o centro do kernel possa passar por todos os pixels originais
    # repete a borda (edge), constant (preto), criaria uma moldura escura artificial ao redor da imagem filtrad
    pad_h = k_h // 2 # metade da altura do kernel
    pad_w = k_w // 2 # metade da largura do kernel
    return np.pad(img, ((pad_h, pad_h), (pad_w, pad_w)), mode=mode) # pad com borda repetida

def convolve2d(img, kernel):
    """Convolução 2D simples"""
    img = ensure_uint8(img)
    if img is None: return None
    kernel = np.array(kernel, dtype=np.float64)
    kh, kw = kernel.shape # dimensões do kernel
    ih, iw = img.shape # dimensões da imagem
    padded = pad_for_kernel(img, kh, kw, mode='edge').astype(np.float64) # pad e converte para float64
    out = np.zeros((ih, iw), dtype=np.float64) # saída em float64
    # Convolução direta
    for r in range(ih):
        for c in range(iw):
            region = padded[r:r+kh, c:c+kw] # região da imagem
            out[r, c] = np.sum(region * kernel) # soma ponderada
    # Normalização se necessário: se kernel soma 1, fica ok; caso contrário, normalizamos para faixa 0..255
    # Mas mantemos valores sem normalização por padrão; apenas clip e uint8
    out = np.clip(out, 0, 255).astype(np.uint8) # limita para 0-255 e converte para uint8
    return out

def median_filter(img, ksize):
    """Filtro de mediana com janela quadrada ksize (ímpar)."""
    img = ensure_uint8(img)
    if img is None: return None
    if ksize % 2 == 0: # garante que ksize é ímpar
        ksize += 1 # torna ímpar
    kh = kw = ksize # kernel quadrado
    ih, iw = img.shape # dimensões da imagem
    padded = pad_for_kernel(img, kh, kw, mode='edge') # pad com borda repetida
    out = np.zeros_like(img)# saída
    for r in range(ih):
        for c in range(iw):
            region = padded[r:r+kh, c:c+kw] # região da imagem
            out[r, c] = np.median(region) # mediana da região
    return out.astype(np.uint8)

def img_diff(a, b):
    """Retorna imagem diferença (abs) e métricas (MSE, PSNR approximado)."""
    if a is None or b is None:
        return None, {}
    a = ensure_uint8(a)
    b = ensure_uint8(b)
    # se formas diferentes, tenta ajustar recortando ao menor
    if a.shape != b.shape:
        min_h = min(a.shape[0], b.shape[0])
        min_w = min(a.shape[1], b.shape[1])
        a = a[:min_h, :min_w]
        b = b[:min_h, :min_w]
    diff = np.abs(a.astype(np.int16) - b.astype(np.int16)).astype(np.uint8) # diferença absoluta
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64))**2) # erro quadrático médio
    psnr = None
    if mse == 0:
        psnr = float('inf') # imagens idênticas
    else:
        PIXEL_MAX = 255.0 # valor máximo do pixel
        psnr = 10 * np.log10((PIXEL_MAX**2) / mse) # PSNR - Peak Signal-to-Noise Ratio
    # SNR simples
    signal_power = np.mean(a.astype(np.float64)**2) # potência do sinal
    noise_power = np.mean((a.astype(np.float64) - b.astype(np.float64))**2) # potência do ruído
    snr = None
    if noise_power == 0:
        snr = float('inf') # sem ruído
    else:
        snr = 10 * np.log10(signal_power / noise_power) # SNR - Signal-to-Noise Ratio
    metrics = {"mse": float(mse), "psnr": float(psnr) if psnr is not None else None, "snr": float(snr) if snr is not None else None}
    return diff, metrics

def compute_histogram(img, bins=256):
    """Retorna histograma (counts, bin_edges)."""
    img = ensure_uint8(img)
    if img is None: return None, None
    hist, edges = np.histogram(img.flatten(), bins=bins, range=(0, 255)) # histograma e edges
    return hist, edges

def kernel_from_text(text):
    """Parseia texto com linhas de números em uma matriz numpy."""
    try:
        rows = [row.strip() for row in text.strip().splitlines() if row.strip()] # linhas não vazias
        mat = [] # matriz temporária
        for r in rows:
            parts = [float(x) for x in r.strip().split()] # converte para float
            mat.append(parts) # adiciona linha
        arr = np.array(mat, dtype=np.float64) # converte para array numpy
        return arr
    except Exception:
        return None
