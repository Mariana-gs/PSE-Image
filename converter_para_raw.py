import sys
import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication, QFileDialog

def converter_jpg_para_raw():
    """
    Abre um diálogo para selecionar um JPG/PNG, converte para 
    8-bit grayscale RAW e o salva.
    """
    
    # 1. Pergunta ao usuário qual JPG/PNG abrir
    input_path, _ = QFileDialog.getOpenFileName(
        None, 
        "Abrir Imagem (JPG, PNG)", 
        "", 
        "Imagens (*.jpg *.jpeg *.png)"
    )
    
    if not input_path:
        print("Operação cancelada.")
        return

    try:
        # 2. Abre a imagem e converte para 'L' (8-bit grayscale)
        print(f"Abrindo {input_path}...")
        img = Image.open(input_path).convert('L')
        
        width, height = img.size
        print(f"Imagem convertida para escala de cinza (8-bit).")
        print(f"Dimensões: Largura={width}, Altura={height}")

        # 3. Pergunta onde salvar o arquivo .raw
        output_path, _ = QFileDialog.getSaveFileName(
            None,
            "Salvar Como Arquivo RAW",
            "imagem_convertida.raw",
            "RAW Files (*.raw)"
        )
        
        if not output_path:
            print("Operação cancelada.")
            return

        # 4. Converte a imagem (Pillow) para um array (Numpy)
        #    Isso garante que temos os bytes puros em uint8
        img_array = np.array(img, dtype=np.uint8)

        # 5. Salva o array de bytes puros no arquivo .raw
        img_array.tofile(output_path)
        
        print(f"\n--- SUCESSO! ---")
        print(f"Arquivo RAW salvo em: {output_path}")
        print(f"Tamanho: {img_array.size} bytes.")
        print("\nIMPORTANTE:")
        print("Ao carregar este arquivo no seu PSE-Image, use:")
        print(f"  Largura: {width}")
        print(f"  Altura:  {height}")

    except Exception as e:
        print(f"Ocorreu um erro: {e}")

# --- Execução do Script ---
if __name__ == "__main__":
    # É necessário um QApplication para usar o QFileDialog
    app = QApplication(sys.argv)
    converter_jpg_para_raw()
    sys.exit()