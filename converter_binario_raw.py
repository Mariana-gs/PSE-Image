import numpy as np

def converter_texto_para_binario(input_path, output_path):
    try:
        # 1. Lê o arquivo como texto normal
        with open(input_path, 'r') as f:
            content = f.read()

        # 2. Remove tags estranhas se houver (como "") 
        # e converte tudo que é número para uma lista
        # (O split() separa por qualquer espaço ou quebra de linha)
        numeros_texto = content.replace('', '').split()
        
        # Filtra apenas o que é dígito (para evitar erros com palavras soltas)
        pixels = []
        for x in numeros_texto:
            # Tenta converter para inteiro se parecer um número
            if x.replace('.', '', 1).isdigit(): 
                pixels.append(int(float(x))) # float para garantir caso tenha ponto

        # 3. Converte para array numpy de 8 bits (uint8)
        array_pixels = np.array(pixels, dtype=np.uint8)

        # 4. Salva como binário puro (.raw)
        array_pixels.tofile(output_path)
        
        print(f"Sucesso! Arquivo convertido.")
        print(f"Tamanho original (texto): {len(content)} caracteres")
        print(f"Tamanho novo (binário): {len(array_pixels)} bytes")
        
        # Tenta adivinhar dimensão para te avisar
        import math
        raiz = math.sqrt(len(array_pixels))
        if int(raiz) * int(raiz) == len(array_pixels):
            print(f"Parece ser uma imagem {int(raiz)}x{int(raiz)}")
            
    except Exception as e:
        print(f"Erro: {e}")

converter_texto_para_binario('circulo.raw', 'circulo_binario.raw')