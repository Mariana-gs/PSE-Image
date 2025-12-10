import sys
import numpy as np 
import os    
import math
from io import BytesIO
from PIL import Image

# Importações necessárias para o gráfico de histograma
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
    QDockWidget, QListWidget, QGraphicsItem, QGraphicsPathItem,
    QGraphicsEllipseItem, QWidget, QVBoxLayout, QLabel,
    QMenu, QPushButton, QSpinBox, QFormLayout, QLineEdit, 
    QErrorMessage, QFileDialog, QComboBox, QDialog, QHBoxLayout, QTextEdit
)
from PySide6.QtCore import Qt, QPointF, QRectF, QByteArray
from PySide6.QtGui import (
    QPen, QBrush, QPainterPath, QColor, QTransform, QFont, QAction,
    QImage, QPixmap 
)

import qimage2ndarray 
import processing_utils as pu

# --- 1. CLASSE NodeConnector ---

class NodeConnector(QGraphicsEllipseItem):
    def __init__(self, parent_block, is_input):
        super().__init__(-10, -10, 20, 20, parent_block) 
        self.parent_block = parent_block
        self.is_input = is_input
        self.wires = [] 
        color = QColor("blue") if is_input else QColor("red")
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.GlobalColor.black))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges)
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.scene().start_connection(self)
            event.accept()
    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemScenePositionHasChanged:
            for wire in self.wires:
                wire.update_path()
        return value

# --- 2. CLASSE NodeBlock  ---

class NodeBlock(QGraphicsItem):
    """ Classe base para todos os blocos de processamento. """
    def __init__(self, title, scene):
        super().__init__()
        self.title = title
        self.width = 200
        self.height = 100 
        self.inputs = []
        self.outputs = []
        
        self.output_data = None 
        self.parameters = {}    
        self.input_connections = {} 
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        scene.addItem(self)

    def register_input(self, input_connector, connected_output_block):
        self.input_connections[input_connector] = connected_output_block
        print(f"Bloco {self.title} registrou entrada do {connected_output_block.title}")

    def remove_input(self, input_connector):
        if input_connector in self.input_connections:
            del self.input_connections[input_connector]
            
    def process(self):
        """ Lógica de processamento padrão (pass-through). """
        if self.inputs:
            input_conn = self.inputs[0][0] 
            if input_conn in self.input_connections:
                input_block = self.input_connections[input_conn]
                self.output_data = input_block.output_data
                print(f"Processando {self.title}: dados copiados.")
            
    def add_connector(self, label, is_input):
        connector = NodeConnector(self, is_input)
        if is_input:
            y_pos = 35 + len(self.inputs) * 20
            connector.setPos(0, y_pos)
            self.inputs.append((connector, label))
        else:
            y_pos = 35 + len(self.outputs) * 20
            connector.setPos(self.width, y_pos)
            self.outputs.append((connector, label))
        self.height = max(self.height, y_pos + 15)
        self.update() 
        return connector

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None):
        """ Desenha a aparência base do bloco com borda laranja se selecionado. """
        if self.isSelected():
            # Borda Laranja e mais grossa (3px)
            painter.setPen(QPen(QColor("orange"), 3))
        else:
            # Borda Preta normal (1px)
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            
        painter.setBrush(QBrush(QColor(240, 240, 240)))
        painter.drawRoundedRect(0, 0, self.width, self.height, 5, 5)
        
        # Título (sempre preto)
        title_font = QFont()
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.drawText(QRectF(5, 5, self.width - 10, 20), self.title)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for conn, _ in self.inputs + self.outputs:
                for wire in conn.wires:
                    wire.update_path()
        return super().itemChange(change, value)

# --- 3. SUBCLASSES DE BLOCOS ---

class BlockRawInput(NodeBlock):
    """ Bloco de Leitura RAW. """
    def process(self):
        if self.output_data is not None:
            print(f"Processando {self.title}: Dados prontos.")
        else:
            print(f"Processando {self.title}: Sem dados.")


class BlockRawOutput(NodeBlock):
    """ Bloco de Gravação RAW. Recebe dados e os prepara para salvar. """
    def __init__(self, title, scene):
        super().__init__(title, scene)
        self.data_to_save = None # Variável para guardar o que será salvo

    def process(self):
        print(f"Processando {self.title}...")
        self.data_to_save = None
        
        # Pega dados da entrada
        if self.inputs:
            input_conn = self.inputs[0][0] 
            if input_conn in self.input_connections:
                input_block = self.input_connections[input_conn]
                # Copia os dados da entrada para a variável interna
                self.data_to_save = input_block.output_data
                # Também define como output_data (caso queira ligar algo depois)
                self.output_data = self.data_to_save 
        
        if self.data_to_save is not None:
            print(f"{self.title}: Dados prontos para salvar ({self.data_to_save.shape}).")
        else:
            print(f"{self.title}: Sem dados de entrada.")

    def save_to_file(self, path):
        """ Chamado pelo botão 'Salvar agora' na interface. """
        if self.data_to_save is None:
            raise ValueError("Não há dados processados para salvar. Execute o fluxo primeiro.")
        
        try:
            # Garante que os dados sejam uint8 antes de salvar
            # Usa astype do numpy para converter
            data_uint8 = self.data_to_save.astype(np.uint8)
            data_uint8.tofile(path)
            return True
        except Exception as e:
            raise RuntimeError(f"Erro ao escrever arquivo: {e}")


class BlockDisplay(NodeBlock):
    """ Bloco de Exibição. Desenha a imagem de entrada em si mesmo. """
    def __init__(self, title, scene):
        super().__init__(title, scene)
        # Define um tamanho maior para o bloco de exibição
        self.width = 256 + 20 # 256px para imagem + 10px padding de cada lado
        self.height = 256 + 40 # 256px para imagem + 30px título + 10px padding
        self.pixmap = None # O QPixmap a ser desenhado

    def process(self):
        """ Pega os dados da entrada e os converte em um QPixmap. """
        print(f"Processando {self.title}...")
        image_data = None
        
        if self.inputs:
            input_conn = self.inputs[0][0] 
            if input_conn in self.input_connections:
                input_block = self.input_connections[input_conn]
                image_data = input_block.output_data 
        
        if image_data is not None:
            try:
                image = qimage2ndarray.array2qimage(image_data, normalize=False)
                
                self.pixmap = QPixmap.fromImage(image)
                print("BlockDisplay: Pixmap criado.")
            except Exception as e:
                print(f"BlockDisplay: Erro ao converter imagem: {e}")
                self.pixmap = None
        else:
            print("BlockDisplay: Sem dados de entrada.")
            self.pixmap = None
        
        # Força um redesenho do bloco
        self.update()

    def boundingRect(self):
        """ Atualiza o bounding box para o novo tamanho. """
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None):
        """ Desenha o bloco de imagem com borda laranja se selecionado. """
        if self.isSelected():
            painter.setPen(QPen(QColor("orange"), 3))
        else:
            painter.setPen(QPen(Qt.GlobalColor.black, 1))

        painter.setBrush(QBrush(QColor(240, 240, 240)))
        painter.drawRoundedRect(0, 0, self.width, self.height, 5, 5)
        
        # Título
        title_font = QFont()
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.drawText(QRectF(5, 5, self.width - 10, 20), self.title)
        
        # Desenha a imagem
        img_rect = QRectF(10, 30, self.width - 20, self.height - 35)
        if self.pixmap:
            scaled_pixmap = self.pixmap.scaled(img_rect.size().toSize(), 
                                               Qt.AspectRatioMode.KeepAspectRatio, 
                                               Qt.TransformationMode.SmoothTransformation)
            pixmap_rect = scaled_pixmap.rect()
            pixmap_rect.moveCenter(img_rect.center().toPoint())
            painter.drawPixmap(pixmap_rect, scaled_pixmap)
        else:
            painter.setPen(QPen(Qt.GlobalColor.gray))
            painter.drawText(img_rect, Qt.AlignmentFlag.AlignCenter, "Sem imagem")
 
class BlockPunctual(NodeBlock):
    """ Bloco de Processamento Pontual. """
    def __init__(self, title, scene):
        super().__init__(title, scene)
        self.parameters.setdefault("operation", "Brilho")
        self.parameters.setdefault("brightness", 0)
        self.parameters.setdefault("threshold", 128)

    def process(self):
        print(f"Processando {self.title}...")
        super().process()
        img = self.output_data
        if img is None and self.inputs:
            input_conn = self.inputs[0][0]
            if input_conn in self.input_connections:
                img = self.input_connections[input_conn].output_data

        if img is None:
            self.output_data = None
            print(f"{self.title}: sem imagem de entrada.")
            return

        op = self.parameters.get("operation", "Brilho")
        if op == "Brilho":
            delta = int(self.parameters.get("brightness", 0))
            self.output_data = pu.adjust_brightness(img, delta)
        elif op == "Limiar":
            t = int(self.parameters.get("threshold", 128))
            self.output_data = pu.threshold(img, t)
        else:
            self.output_data = img
        print(f"{self.title}: operação {op} aplicada.")

class BlockConvolution(NodeBlock):
    """ Máscara de Convolução / filtros. """
    def __init__(self, title, scene):
        super().__init__(title, scene)
        self.parameters.setdefault("kernel_text", "1 1 1\n1 1 1\n1 1 1")
        self.parameters.setdefault("preset", "Média")
        self.parameters.setdefault("median_size", 3)

    def process(self):
        print(f"Processando {self.title}...")
        img = None
        if self.inputs:
            input_conn = self.inputs[0][0]
            if input_conn in self.input_connections:
                img = self.input_connections[input_conn].output_data
        if img is None:
            self.output_data = None
            print(f"{self.title}: sem imagem de entrada.")
            return

        preset = self.parameters.get("preset", "Média")
        if preset == "Média":
            k = np.ones((3,3), dtype=np.float64) / 9.0
            out = pu.convolve2d(img, k)
        elif preset == "Laplaciano":
            k = np.array([[0,1,0],[1,-4,1],[0,1,0]], dtype=np.float64)
            out = pu.convolve2d(img, k)
        elif preset == "Mediana":
            size = int(self.parameters.get("median_size", 3))
            out = pu.median_filter(img, size)
        elif preset == "Personalizado":
            text = self.parameters.get("kernel_text", "")
            k = pu.kernel_from_text(text)
            if k is None:
                print("Kernel inválido; passando imagem sem alteração.")
                out = img
            else:
                out = pu.convolve2d(img, k)
        else:
            out = img
        self.output_data = out
        print(f"{self.title}: filtro '{preset}' aplicado.")

class BlockHistogram(NodeBlock):
    """ Bloco que calcula e EXIBE o histograma internamente. """
    def __init__(self, title, scene):
        super().__init__(title, scene)
        self.width = 300 
        self.height = 220 
        self.pixmap = None 

    def process(self):
        print(f"Processando {self.title}...")
        img = None
        self.pixmap = None 
        
        if self.inputs:
            input_conn = self.inputs[0][0]
            if input_conn in self.input_connections:
                img = self.input_connections[input_conn].output_data
                
        if img is None:
            self.output_data = None
            print(f"{self.title}: sem imagem de entrada.")
            self.update() 
            return

        self.output_data = img  
        
        hist, edges = pu.compute_histogram(img, bins=256)
        
        try:
            fig = Figure(figsize=(3.5, 2.2), dpi=80) 
            ax = fig.add_subplot(111)
            
            ax.bar(edges[:-1], hist, width=1.0, color='#333333')
            
            ax.set_title("Histograma", fontsize=10)
            ax.tick_params(axis='both', which='major', labelsize=8)
            ax.set_xlim(-25, 280)
            fig.tight_layout()
            
            buf = BytesIO()
            fig.savefig(buf, format='png', transparent=True)
            buf.seek(0)
            
            self.pixmap = QPixmap()
            self.pixmap.loadFromData(buf.getvalue())
            
            print(f"{self.title}: Gráfico gerado.")
            
        except Exception as e:
            print(f"Erro ao gerar gráfico: {e}")

        self.update() 

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None):
        """ Desenha o bloco de histograma com borda laranja se selecionado. """
        if self.isSelected():
            painter.setPen(QPen(QColor("orange"), 3))
        else:
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            
        painter.setBrush(QBrush(QColor(240, 240, 240)))
        painter.drawRoundedRect(0, 0, self.width, self.height, 5, 5)
        
        # Título
        title_font = QFont()
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.drawText(QRectF(5, 5, self.width - 10, 20), self.title)
        
        # Desenha o gráfico
        graph_rect = QRectF(10, 35, self.width - 20, self.height - 45)
        
        if self.pixmap:
            scaled = self.pixmap.scaled(
                graph_rect.size().toSize(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            x = graph_rect.x() + (graph_rect.width() - scaled.width()) / 2
            y = graph_rect.y() + (graph_rect.height() - scaled.height()) / 2
            painter.drawPixmap(int(x), int(y), scaled)
        else:
            painter.setPen(QPen(Qt.GlobalColor.gray))
            painter.drawText(graph_rect, Qt.AlignmentFlag.AlignCenter, "Sem dados\nExecute o fluxo")

class BlockDifference(NodeBlock):
    """ Bloco de Diferença. """
    def process(self):
        print(f"Processando {self.title}...")
        img_a = None
        img_b = None
        
        if len(self.inputs) > 0:
            conn_a = self.inputs[0][0]
            if conn_a in self.input_connections:
                img_a = self.input_connections[conn_a].output_data
                
        if len(self.inputs) > 1:
            conn_b = self.inputs[1][0]
            if conn_b in self.input_connections:
                img_b = self.input_connections[conn_b].output_data
        
        if img_a is None or img_b is None:
            self.output_data = None
            print(f"{self.title}: falta A ou B.")
            return
        
        diff_img, metrics = pu.img_diff(img_a, img_b)
        self.output_data = diff_img
        self.parameters['metrics'] = metrics
        print(f"{self.title}: diferença calculada. MSE={metrics.get('mse'):.2f}, PSNR={metrics.get('psnr')}")

# --- 4. CLASSE ConnectionWire ---
class ConnectionWire(QGraphicsPathItem):
    def __init__(self, start_connector, scene):
        super().__init__()
        self.start_conn = start_connector
        self.end_conn = None
        self._end_pos = start_connector.scenePos() 
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        scene.addItem(self)
        self.setZValue(-1) 
        
    def set_end_connector(self, connector):
        self.end_conn = connector
        self.start_conn.wires.append(self)
        self.end_conn.wires.append(self)
        
        self.end_conn.parent_block.register_input(
            self.end_conn, 
            self.start_conn.parent_block
        )
        self.update_path()

    def update_temp_end_pos(self, pos):
        self._end_pos = pos
        self.update_path()

    def update_path(self):
        p1 = self.start_conn.scenePos()
        p2 = self.end_conn.scenePos() if self.end_conn else self._end_pos
        path = QPainterPath()
        path.moveTo(p1)
        dx = p2.x() - p1.x()
        c1 = QPointF(p1.x() + dx * 0.5, p1.y())
        c2 = QPointF(p2.x() - dx * 0.5, p2.y())
        path.cubicTo(c1, c2, p2)
        self.setPath(path)
        
    def disconnect(self):
        if self.start_conn:
            try:
                self.start_conn.wires.remove(self)
            except ValueError:
                pass
        if self.end_conn:
            try:
                self.end_conn.parent_block.remove_input(self.end_conn)
            except Exception:
                pass
            try:
                self.end_conn.wires.remove(self)
            except ValueError:
                pass

    def paint(self, painter, option, widget=None):
        # Verifica se o item está selecionado
        if self.isSelected():
            pen = QPen(QColor("orange"), 3) # Mais grosso e laranja
        else:
            pen = QPen(QColor("black"), 2)  # Padrão
            
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.path())

# --- 5. CLASSE FlowScene ---
class FlowScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.draft_wire = None 
        self.setBackgroundBrush(QBrush(QColor(50, 50, 50)))

    def start_connection(self, connector):
        self.draft_wire = ConnectionWire(connector, self)

    def mouseMoveEvent(self, event):
        if self.draft_wire:
            self.draft_wire.update_temp_end_pos(event.scenePos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.draft_wire:
            item = self.itemAt(event.scenePos(), QTransform())
            if isinstance(item, NodeConnector):
                if self.is_valid_connection(self.draft_wire.start_conn, item):
                    self.draft_wire.set_end_connector(item)
                    self.draft_wire = None
                    return
            self.removeItem(self.draft_wire)
            self.draft_wire = None
        super().mouseReleaseEvent(event)

    def is_valid_connection(self, start_conn, end_conn):
        if start_conn == end_conn: return False
        if start_conn.is_input == end_conn.is_input: return False
        return True

    def create_block(self, block_name, position):
        """ Factory que cria as SUBCLASSES de blocos corretas. """
        block = None
        
        if block_name == "Leitura de arquivo RAW":
            block = BlockRawInput(block_name, self)
            block.add_connector("Img Saída", is_input=False)
        
        elif block_name == "Exibição de imagem":
            block = BlockDisplay(block_name, self)
            block.add_connector("Img Entrada", is_input=True)
        
        elif block_name == "Gravação de arquivo RAW":
            block = BlockRawOutput(block_name, self) 
            block.add_connector("Img Entrada", is_input=True)
            
        elif block_name == "Processamento Pontual":
            block = BlockPunctual(block_name, self)
            block.add_connector("Img Entrada", is_input=True)
            block.add_connector("Img Saída", is_input=False)

        elif block_name == "Máscara de Convolução":
            block = BlockConvolution(block_name, self) 
            block.add_connector("Img Entrada", is_input=True)
            block.add_connector("Img Saída", is_input=False)
            
        elif block_name == "Plotagem de Histograma":
            block = BlockHistogram(block_name, self) 
            block.add_connector("Img Entrada", is_input=True)
            
        elif block_name == "Diferença entre Imagens":
            block = BlockDifference(block_name, self)
            block.add_connector("Img A", is_input=True)
            block.add_connector("Img B", is_input=True)
            block.add_connector("Img Saída", is_input=False)
            
        else:
            return None
            
        block.setPos(position)
        return block

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            selected_items = self.selectedItems()
            for item in selected_items:
                if isinstance(item, NodeBlock):
                    self.delete_block(item)
                elif isinstance(item, ConnectionWire):
                    self.delete_wire(item)
            event.accept()
        else:
            super().keyPressEvent(event)

    def delete_wire(self, wire):
        wire.disconnect()
        self.removeItem(wire)

    def delete_block(self, block):
        for conn, _ in block.inputs + block.outputs:
            for wire in list(conn.wires): 
                self.delete_wire(wire)
        self.removeItem(block)

# --- 6. CLASSE FlowView ---
class FlowView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setRenderHint(self.renderHints().Antialiasing)
        self.available_blocks = [
            "Leitura de arquivo RAW", "Exibição de imagem", "Gravação de arquivo RAW",
            "Processamento Pontual", "Máscara de Convolução",
            "Plotagem de Histograma", "Diferença entre Imagens"
        ]
        self._context_menu_pos = QPointF()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        elif event.button() == Qt.MouseButton.LeftButton:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        super().mousePressEvent(event)
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
    def contextMenuEvent(self, event):
        self._context_menu_pos = self.mapToScene(event.pos())
        menu = QMenu(self)
        for block_name in self.available_blocks:
            action = QAction(block_name, self)
            action.triggered.connect(
                lambda checked=False, name=block_name: self.on_context_menu_triggered(name)
            )
            menu.addAction(action)
        menu.exec(event.globalPos())
    def on_context_menu_triggered(self, block_name):
        self.scene().create_block(block_name, self._context_menu_pos)

# --- 7. CLASSE MainWindow ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PSE-Image (PUC Minas)")
        self.setGeometry(100, 100, 1200, 800)

        self.scene = FlowScene()
        self.view = FlowView(self.scene, self)
        
        self.setCentralWidget(self.view)
        
        self.error_dialog = QErrorMessage(self)
        
        toolbar = self.addToolBar("Execução")
        self.process_button = QPushButton("Processar Fluxo")
        self.process_button.clicked.connect(self.process_flow)
        toolbar.addWidget(self.process_button)
        
        self.create_properties_dock() 
        
        self.scene.selectionChanged.connect(self.on_selection_changed)
        
    def create_properties_dock(self):
        self.props_dock = QDockWidget("Propriedades", self)
        self.props_dock.setMinimumWidth(300)
        self.props_dock.setMaximumWidth(500)
        self.props_container = QWidget()
        self.props_layout = QVBoxLayout(self.props_container)
        
        self.props_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.props_container.setStyleSheet("QLabel { qproperty-alignment: AlignLeft; }")
        
        self.props_layout.addWidget(QLabel(
            "Bem-vindo ao PSE-Image!\n\n"
            "Clique com o botão direito no canvas para adicionar um novo bloco."
        ))
        
        self.props_layout.addStretch() 
        self.props_dock.setWidget(self.props_container)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.props_dock)

    def clear_properties_layout(self):
        while self.props_layout.count():
            item = self.props_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            layout = item.layout()
            if layout is not None:
                self.clear_nested_layout(layout)
                layout.deleteLater()

    def clear_nested_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            sub_layout = item.layout()
            if sub_layout is not None:
                self.clear_nested_layout(sub_layout)

    def on_selection_changed(self):
        self.clear_properties_layout()
        selected = self.scene.selectedItems()
        
        if len(selected) == 1 and isinstance(selected[0], NodeBlock):
            block = selected[0]
            self.build_properties_for_block(block)
        else:
            label = QLabel(
                "Clique com o botão direito no canvas para adicionar um novo bloco.\n\n"
                "Selecione um único bloco para ver suas propriedades."
            )
            
            label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            
            self.props_layout.addWidget(label)
            self.props_layout.addStretch()

    def build_properties_for_block(self, block):
        self.props_layout.addWidget(QLabel(f"Propriedades: {block.title}"))
        
        if block.title == "Leitura de arquivo RAW":
            self.build_raw_loader_properties(block)
        elif block.title == "Processamento Pontual":
            self.build_punctual_properties(block)
        
        elif block.title == "Gravação de arquivo RAW":
            self.build_raw_saver_properties(block)
            
        elif block.title == "Máscara de Convolução":
            self.build_convolution_properties(block)
        elif block.title == "Plotagem de Histograma":
            self.build_histogram_properties(block)
        elif block.title == "Diferença entre Imagens":
            self.build_difference_properties(block)
        else:
            self.props_layout.addWidget(QLabel("Este bloco não tem parâmetros."))
            
        self.props_layout.addStretch()

    # --- Leitura RAW ---
    def build_raw_loader_properties(self, block):
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        # 1. Seletor de Formato
        self.format_combo = QComboBox()
        # Define os modos de leitura disponíveis
        self.format_combo.addItems([
            "RAW (Binário Padrão)", 
            "Texto/ASCII", 
            "Imagem (JPG/PNG)"
        ])
        # Tenta recuperar o último formato usado ou define padrão
        current_fmt = block.parameters.get("format_index", 0)
        self.format_combo.setCurrentIndex(current_fmt)
        
        # Salva a escolha no bloco quando mudar
        def on_fmt_change(idx):
            block.parameters["format_index"] = idx
        self.format_combo.currentIndexChanged.connect(on_fmt_change)
        
        form_layout.addRow("Formato:", self.format_combo)

        # 2. Caminho do Arquivo
        self.filepath_label = QLineEdit(block.parameters.get("filepath", "Nenhum arquivo..."))
        self.filepath_label.setReadOnly(True)
        self.filepath_label.setMinimumHeight(40)
        form_layout.addRow(QLabel("Arquivo:"))
        form_layout.addRow(self.filepath_label)
        
        # 3. Lista de Resoluções (para RAW e Texto)
        self.res_combo = QComboBox()
        form_layout.addRow("Possíveis Resoluções:", self.res_combo)
        self.res_combo.currentIndexChanged.connect(
            lambda index: self.on_resolution_combo_changed(index, block)
        )

        # 4. Dimensões Manuais
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 65535) 
        self.width_spin.setValue(block.parameters.get("width", 256))
        form_layout.addRow("Largura (W):", self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 65535)
        self.height_spin.setValue(block.parameters.get("height", 256))
        form_layout.addRow("Altura (H):", self.height_spin)
        
        self.props_layout.addLayout(form_layout)
        
        # 5. Botão de Carga Inteligente
        load_button = QPushButton("Carregar Arquivo")
        load_button.clicked.connect(lambda: self.load_raw_file(block))
        self.props_layout.addWidget(load_button)
    
    def on_resolution_combo_changed(self, index, block): 
        data = self.res_combo.itemData(index) 
        if data:
            w, h = data
            self.width_spin.blockSignals(True)
            self.height_spin.blockSignals(True)
            self.width_spin.setValue(w)
            self.height_spin.setValue(h)
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(False)
            
            block.parameters["width"] = w
            block.parameters["height"] = h
            
            if block.output_data is not None:
                try:
                    flat_data = block.output_data.flatten()
                    block.output_data = flat_data.reshape((h, w))
                    print(f"Dados do bloco reformatados em memória para {w}x{h}")
                except ValueError as e:
                    print(f"Erro ao reformatar imagem: {e}")
    
    def load_raw_file(self, block):
        # Descobre qual modo o usuário quer usar
        mode_index = self.format_combo.currentIndex()
        
        # Configura o filtro do diálogo baseado no modo
        if mode_index == 2: # Imagem JPG/PNG
            filter_str = "Images (*.jpg *.jpeg *.png *.bmp);;All Files (*)"
        elif mode_index == 1: # Texto
            filter_str = "Text/RAW (*.txt *.raw);;All Files (*)"
        else: # RAW Binário
            filter_str = "RAW Files (*.raw);;All Files (*)"

        filepath, _ = QFileDialog.getOpenFileName(self, "Abrir Arquivo", "", filter_str)
        if not filepath:
            return
            
        try:
            img_data = None
            
            # --- CASO A: RAW Binário Padrão ---
            if mode_index == 0:
                img_data = np.fromfile(filepath, dtype=np.uint8)
                print("Modo: Leitura Binária Direta")

            # --- CASO B: Texto/ASCII (circulo.raw) ---
            elif mode_index == 1:
                print("Modo: Conversão Texto -> Binário")
                with open(filepath, 'r') as f:
                    content = f.read()
                
                numeros_texto = content.replace('', '').split()
                
                pixels = []
                for x in numeros_texto:
                    # Filtra apenas o que parece número
                    clean_x = x.replace('.', '', 1) 
                    if clean_x.isdigit() or (clean_x.startswith('-') and clean_x[1:].isdigit()):
                        pixels.append(int(float(x)))
                
                img_data = np.array(pixels, dtype=np.uint8)

            # --- CASO C: Imagem JPG/PNG (Pillow) ---
            elif mode_index == 2:
                print("Modo: Conversão Imagem (PIL) -> Array")
                pil_img = Image.open(filepath).convert('L') # Converte para Escala de Cinza
                img_data = np.array(pil_img, dtype=np.uint8)
                
                # Imagens JPG/PNG já têm largura e altura definidas
                h, w = img_data.shape
                
                # Pula a lógica de fatoração e vai direto para o set
                block.output_data = img_data
                block.parameters["filepath"] = filepath
                block.parameters["width"] = w
                block.parameters["height"] = h
                
                # Atualiza UI
                self.width_spin.setValue(w)
                self.height_spin.setValue(h)
                self.filepath_label.setText(filepath)
                self.res_combo.clear()
                self.res_combo.addItem(f"{w} x {h} (Nativo)", (w, h))
                print(f"Sucesso: Imagem carregada ({w}x{h})")
                return

            # --- Lógica Comum para RAW e Texto (Adivinhar Resolução) ---
            # Se chegamos aqui, temos um array 1D (tripa de bytes) e precisamos descobrir W e H
            if img_data is not None:
                file_size = img_data.size
                
                possible_res = []
                # Tenta fatorar
                limit = int(math.sqrt(file_size)) + 1
                for w in range(1, limit):
                    if file_size % w == 0:
                        h = file_size // w
                        possible_res.append((w, h))
                        if w != h:
                            possible_res.append((h, w))
                
                possible_res.sort(key=lambda x: x[0])
                
                # Atualiza Combo Box
                self.res_combo.blockSignals(True)
                self.res_combo.clear()
                
                best_index = 0
                min_diff = float('inf')
                
                for i, (w, h) in enumerate(possible_res):
                    self.res_combo.addItem(f"{w} x {h}", (w, h))
                    diff = abs(w - h)
                    if diff < min_diff:
                        min_diff = diff
                        best_index = i

                self.res_combo.setCurrentIndex(best_index)
                self.res_combo.blockSignals(False)
                
                # Configura dados iniciais com a melhor aposta
                if possible_res:
                    w_best, h_best = possible_res[best_index]
                    block.output_data = img_data.reshape((h_best, w_best))
                    block.parameters["width"] = w_best
                    block.parameters["height"] = h_best
                    # Atualiza spinners via callback simulado
                    self.on_resolution_combo_changed(best_index, block)
                else:
                    # Fallback se não achar fatores
                    block.output_data = img_data.reshape((1, file_size))
                    print("Aviso: Não foi possível determinar dimensões retangulares.")

                block.parameters["filepath"] = filepath
                self.filepath_label.setText(filepath)
                print(f"Sucesso: Dados carregados.")

        except Exception as e:
            self.error_dialog.showMessage(f"Falha ao ler o arquivo: {e}")
    
    
    # --- Gravação RAW ---
    def build_raw_saver_properties(self, block):
        self.props_layout.addWidget(QLabel("Gravação de Arquivo RAW"))
        
        if block.data_to_save is not None:
            h, w = block.data_to_save.shape
            status_text = f"Status: Dados prontos ({w}x{h})"
            status_style = "color: green; font-weight: bold;"
            enable_btn = True
        else:
            status_text = "Status: Aguardando processamento"
            status_style = "color: orange; font-weight: bold;"
            enable_btn = False
            
        status_label = QLabel(status_text)
        status_label.setStyleSheet(status_style)
        self.props_layout.addWidget(status_label)
        
        self.props_layout.addSpacing(10)
        
        save_btn = QPushButton("Salvar Arquivo (.RAW)")
        save_btn.setEnabled(enable_btn)
        save_btn.setMinimumHeight(40) 
        
        save_btn.clicked.connect(lambda: self.action_save_raw(block))
        
        self.props_layout.addWidget(save_btn)
        
        if not enable_btn:
            info = QLabel("\n1. Conecte uma imagem na entrada.\n2. Clique em 'Processar Fluxo'.\n3. Volte aqui para salvar.")
            info.setStyleSheet("color: gray; font-style: italic;")
            self.props_layout.addWidget(info)

    def action_save_raw(self, block):
        """ Função auxiliar para abrir o diálogo e salvar. """
        if block.data_to_save is None:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, 
            "Salvar Arquivo RAW", 
            "imagem_processada.raw", 
            "RAW Files (*.raw);;All Files (*)"
        )
        
        if not filepath:
            return 
            
        try:
            block.save_to_file(filepath)
            print(f"Salvo com sucesso: {filepath}")
        except Exception as e:
            self.error_dialog.showMessage(f"Erro ao salvar: {e}")

    # --- Processamento Pontual ---
    def build_punctual_properties(self, block):
        form_layout = QFormLayout()
        
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        op_combo = QComboBox()
        op_combo.addItems(["Brilho", "Limiar"])
        op_combo.setCurrentText(block.parameters.get("operation", "Brilho"))
        form_layout.addRow("Operação:", op_combo)

        brightness_spin = QSpinBox()
        brightness_spin.setRange(-255, 255)
        brightness_spin.setValue(int(block.parameters.get("brightness", 0)))
        form_layout.addRow("Brilho (delta):", brightness_spin)

        threshold_spin = QSpinBox()
        threshold_spin.setRange(0, 255)
        threshold_spin.setValue(int(block.parameters.get("threshold", 128)))
        form_layout.addRow("Limiar (T):", threshold_spin)

        self.props_layout.addLayout(form_layout)

        def apply_params():
            block.parameters["operation"] = op_combo.currentText()
            block.parameters["brightness"] = int(brightness_spin.value())
            block.parameters["threshold"] = int(threshold_spin.value())
            print(f"Parâmetros do '{block.title}' atualizados: {block.parameters}")

        apply_btn = QPushButton("Aplicar parâmetros")
        apply_btn.clicked.connect(apply_params)
        self.props_layout.addWidget(apply_btn)

    # --- Convolução ---
    def build_convolution_properties(self, block):
        form_layout = QFormLayout()
        
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        preset_combo = QComboBox()
        preset_combo.addItems(["Média", "Laplaciano", "Mediana", "Personalizado"])
        preset_combo.setCurrentText(block.parameters.get("preset", "Média"))
        form_layout.addRow("Preset:", preset_combo)

        median_spin = QSpinBox()
        median_spin.setRange(1, 21)
        median_spin.setValue(int(block.parameters.get("median_size", 3)))
        form_layout.addRow("Tamanho (mediana):", median_spin)

        kernel_text = QTextEdit()
        kernel_text.setPlainText(block.parameters.get("kernel_text", "1 1 1\n1 1 1\n1 1 1"))
        kernel_text.setFixedHeight(80)
        form_layout.addRow("Kernel (linhas):", kernel_text)

        self.props_layout.addLayout(form_layout)

        def apply_conv_params():
            block.parameters["preset"] = preset_combo.currentText()
            block.parameters["median_size"] = int(median_spin.value())
            block.parameters["kernel_text"] = kernel_text.toPlainText()
            print(f"Parâmetros de convolução atualizados: {block.parameters}")
        apply_btn = QPushButton("Aplicar parâmetros")
        apply_btn.clicked.connect(apply_conv_params)
        self.props_layout.addWidget(apply_btn)

    # --- Histograma ---
    def build_histogram_properties(self, block):
        self.props_layout.addWidget(QLabel("Visualização do Histograma"))
        
        if block.pixmap:
            status_label = QLabel("Status: Gráfico gerado!")
            status_label.setStyleSheet("color: green")
            enable_btn = True
        else:
            status_label = QLabel("Status: Aguardando processamento")
            status_label.setStyleSheet("color: orange")
            enable_btn = False
            
        self.props_layout.addWidget(status_label)
        
        save_btn = QPushButton("Baixar Gráfico (PNG)")
        save_btn.setEnabled(enable_btn) 
        save_btn.clicked.connect(lambda: self.save_histogram_chart(block))
        
        self.props_layout.addWidget(save_btn)
        
        if not enable_btn:
            self.props_layout.addWidget(QLabel("\nClique em 'Processar Fluxo'\npara gerar o gráfico."))
    
    def save_histogram_chart(self, block):
        if not block.pixmap:
            self.error_dialog.showMessage("Não há gráfico gerado para salvar.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, 
            "Salvar Gráfico", 
            "histograma.png", 
            "Images (*.png *.jpg *.bmp);;All Files (*)"
        )
        
        if not filepath:
            return
            
        try:
            success = block.pixmap.save(filepath)
            if success:
                print(f"Gráfico salvo com sucesso em: {filepath}")
            else:
                self.error_dialog.showMessage("Falha desconhecida ao salvar a imagem.")
        except Exception as e:
            self.error_dialog.showMessage(f"Erro ao salvar gráfico: {e}")

    # --- Diferença ---
    def build_difference_properties(self, block):
        self.props_layout.addWidget(QLabel("Este bloco calcula diferença absoluta entre A e B."))
        show_metrics_btn = QPushButton("Mostrar métricas (após processar)")
        def show_metrics():
            metrics = block.parameters.get('metrics', None)
            if metrics is None:
                self.error_dialog.showMessage("Sem métricas (execute 'Processar Fluxo' antes).")
                return
            text = "\n".join(f"{k}: {v}" for k,v in metrics.items())
            dlg = QDialog(self)
            dlg.setWindowTitle("Métricas - Diferença")
            layout = QVBoxLayout(dlg)
            layout.addWidget(QLabel(text))
            dlg.exec()
        show_metrics_btn.clicked.connect(show_metrics)
        self.props_layout.addWidget(show_metrics_btn)

    def process_flow(self):
        print("\n--- INICIANDO PROCESSAMENTO DO FLUXO ---")
        
        all_blocks = [item for item in self.scene.items() if isinstance(item, NodeBlock)]
        root_nodes = [b for b in all_blocks if not b.input_connections]
        
        if not root_nodes:
            print("Processamento falhou: Nenhum nó inicial (como Leitura RAW) encontrado.")
            return
            
        queue = list(root_nodes)
        processed = set()
        
        max_iterations = len(all_blocks) * 4
        count = 0
        
        while queue and count < max_iterations:
            block = queue.pop(0)
            count += 1
            
            if block in processed:
                continue
                
            dependencies = block.input_connections.values()
            
            if all(dep in processed for dep in dependencies):
                block.process()
                processed.add(block)
                
                for conn, _ in block.outputs:
                    for wire in conn.wires:
                        next_block = wire.end_conn.parent_block
                        if next_block not in processed:
                            queue.append(next_block)
            else:
                queue.append(block)
                
        if count >= max_iterations and queue:
            print("Erro de processamento: Possível loop ou dependência circular detectada.")
        print("--- PROCESSAMENTO DO FLUXO CONCLUÍDO ---")
        
        self.scene.update() 

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())