# processing_utils.py
import numpy as np
from io import BytesIO

def ensure_uint8(img):
    """Garante que o array seja np.uint8 e 2D (grayscale)."""
    if img is None:
        return None
    a = np.array(img)
    if a.ndim == 3 and a.shape[2] in (3,4):
        # converte para grayscale simples pela média
        a = np.mean(a[..., :3], axis=2)
    a = np.clip(a, 0, 255)
    return a.astype(np.uint8)

def adjust_brightness(img, delta):
    """Adiciona delta (pode ser negativo)."""
    img = ensure_uint8(img)
    if img is None: return None
    out = img.astype(np.int16) + int(delta)
    out = np.clip(out, 0, 255).astype(np.uint8)
    return out

def threshold(img, t, high_value=255, low_value=0):
    """Limiar binário: >= t -> high_value else low_value."""
    img = ensure_uint8(img)
    if img is None: return None
    out = np.where(img >= t, high_value, low_value).astype(np.uint8)
    return out

def pad_for_kernel(img, k_h, k_w, mode='edge'):
    pad_h = k_h // 2
    pad_w = k_w // 2
    return np.pad(img, ((pad_h, pad_h), (pad_w, pad_w)), mode=mode)

def convolve2d(img, kernel):
    """Convolução 2D simples (sem dependências externas)."""
    img = ensure_uint8(img)
    if img is None: return None
    kernel = np.array(kernel, dtype=np.float64)
    kh, kw = kernel.shape
    ih, iw = img.shape
    padded = pad_for_kernel(img, kh, kw, mode='edge').astype(np.float64)
    out = np.zeros((ih, iw), dtype=np.float64)
    # Convolução direta (ineficiente mas simples)
    for r in range(ih):
        for c in range(iw):
            region = padded[r:r+kh, c:c+kw]
            out[r, c] = np.sum(region * kernel)
    # Normalização se necessário: se kernel soma 1, fica ok; caso contrário, normalizamos para faixa 0..255
    # Mas mantemos valores sem normalização por padrão; apenas clip e uint8
    out = np.clip(out, 0, 255).astype(np.uint8)
    return out

def median_filter(img, ksize):
    """Filtro de mediana com janela quadrada ksize (ímpar)."""
    img = ensure_uint8(img)
    if img is None: return None
    if ksize % 2 == 0:
        ksize += 1
    kh = kw = ksize
    ih, iw = img.shape
    padded = pad_for_kernel(img, kh, kw, mode='edge')
    out = np.zeros_like(img)
    for r in range(ih):
        for c in range(iw):
            region = padded[r:r+kh, c:c+kw]
            out[r, c] = np.median(region)
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
    diff = np.abs(a.astype(np.int16) - b.astype(np.int16)).astype(np.uint8)
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64))**2)
    psnr = None
    if mse == 0:
        psnr = float('inf')
    else:
        PIXEL_MAX = 255.0
        psnr = 10 * np.log10((PIXEL_MAX**2) / mse)
    # SNR simples
    signal_power = np.mean(a.astype(np.float64)**2)
    noise_power = np.mean((a.astype(np.float64) - b.astype(np.float64))**2)
    snr = None
    if noise_power == 0:
        snr = float('inf')
    else:
        snr = 10 * np.log10(signal_power / noise_power)
    metrics = {"mse": float(mse), "psnr": float(psnr) if psnr is not None else None, "snr": float(snr) if snr is not None else None}
    return diff, metrics

def compute_histogram(img, bins=256):
    """Retorna histograma (counts, bin_edges)."""
    img = ensure_uint8(img)
    if img is None: return None, None
    hist, edges = np.histogram(img.flatten(), bins=bins, range=(0, 255))
    return hist, edges

def kernel_from_text(text):
    """Parseia texto com linhas de números em uma matriz numpy."""
    try:
        rows = [row.strip() for row in text.strip().splitlines() if row.strip()]
        mat = []
        for r in rows:
            parts = [float(x) for x in r.strip().split()]
            mat.append(parts)
        arr = np.array(mat, dtype=np.float64)
        return arr
    except Exception:
        return None
