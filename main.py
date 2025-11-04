import sys
import numpy as np 
# Importe PySide6 PRIMEIRO
# teste
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
    QDockWidget, QListWidget, QGraphicsItem, QGraphicsPathItem,
    QGraphicsEllipseItem, QWidget, QVBoxLayout, QLabel,
    QMenu, QPushButton, QSpinBox, QFormLayout, QLineEdit, 
    QErrorMessage, QFileDialog
)
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QPen, QBrush, QPainterPath, QColor, QTransform, QFont, QAction,
    QImage, QPixmap 
)

# Importe qimage2ndarray DEPOIS
import qimage2ndarray 

# --- 1. CLASSE NodeConnector ---

class NodeConnector(QGraphicsEllipseItem):
    def __init__(self, parent_block, is_input):
        super().__init__(-5, -5, 10, 10, parent_block) 
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
        self.width = 160
        self.height = 80 
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
        """ Desenha a aparência base do bloco. """
        painter.setBrush(QBrush(QColor(240, 240, 240)))
        painter.setPen(QPen(Qt.GlobalColor.black, 2 if self.isSelected() else 1))
        painter.drawRoundedRect(0, 0, self.width, self.height, 5, 5)
        
        # Título
        title_font = QFont()
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.drawText(QRectF(5, 5, self.width - 10, 20), self.title)
        
        # Rótulos dos Conectores
        painter.setFont(QFont()) 
        for conn, label in self.inputs:
            painter.drawText(QRectF(15, conn.y() - 10, self.width - 30, 20), label)
        for conn, label in self.outputs:
            painter.drawText(QRectF(15, conn.y() - 10, self.width - 30, 20), Qt.AlignmentFlag.AlignRight, label)

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
                # Converte NumPy array para QImage, depois QPixmap
                image = qimage2ndarray.array2qimage(image_data, normalize=True)
                self.pixmap = QPixmap.fromImage(image)
                print("BlockDisplay: Pixmap criado.")
            except Exception as e:
                print(f"BlockDisplay: Erro ao converter imagem: {e}")
                self.pixmap = None
        else:
            print("BlockDisplay: Sem dados de entrada.")
            self.pixmap = None
        
        # Força um redesenho do bloco (chamará o 'paint' abaixo)
        self.update() 

    def boundingRect(self):
        """ Atualiza o bounding box para o novo tamanho. """
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None):
        """ Sobrescreve o 'paint' para desenhar a imagem. """
        # 1. Desenha o fundo e o título (copiado do NodeBlock.paint)
        painter.setBrush(QBrush(QColor(240, 240, 240)))
        painter.setPen(QPen(Qt.GlobalColor.black, 2 if self.isSelected() else 1))
        painter.drawRoundedRect(0, 0, self.width, self.height, 5, 5)
        
        title_font = QFont()
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.drawText(QRectF(5, 5, self.width - 10, 20), self.title)
        
        # 2. Desenha rótulos dos conectores
        painter.setFont(QFont()) 
        for conn, label in self.inputs:
            painter.drawText(QRectF(15, conn.y() - 10, self.width - 30, 20), label)
        # (Este bloco não tem saídas)
        
        # 3. Define a área de desenho da imagem (abaixo do título)
        img_rect = QRectF(10, 30, self.width - 20, self.height - 35)

        # 4. Desenha a imagem (se existir)
        if self.pixmap:
            # Mantém a proporção da imagem dentro do retângulo
            scaled_pixmap = self.pixmap.scaled(img_rect.size().toSize(), 
                                               Qt.AspectRatioMode.KeepAspectRatio, 
                                               Qt.TransformationMode.SmoothTransformation)
            # Centraliza o pixmap escalonado
            pixmap_rect = scaled_pixmap.rect()
            pixmap_rect.moveCenter(img_rect.center().toPoint())
            painter.drawPixmap(pixmap_rect, scaled_pixmap)
            
        else:
            # Se não houver imagem, desenha um placeholder
            painter.setPen(QPen(Qt.GlobalColor.gray))
            painter.drawText(img_rect, Qt.AlignmentFlag.AlignCenter, "Sem imagem")

class BlockPunctual(NodeBlock):
    """ Bloco de Processamento Pontual. """
    def process(self):
        print(f"Processando {self.title}...")
        super().process() # Lógica padrão (pass-through)

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
        
        self.output_data = img_a # Apenas passa A por enquanto


# --- 4. CLASSE ConnectionWire ---
class ConnectionWire(QGraphicsPathItem):
    def __init__(self, start_connector, scene):
        super().__init__()
        self.start_conn = start_connector
        self.end_conn = None
        self._end_pos = start_connector.scenePos() 
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
            self.start_conn.wires.remove(self)
        if self.end_conn:
            self.end_conn.parent_block.remove_input(self.end_conn)
            self.end_conn.wires.remove(self)


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
            block = NodeBlock(block_name, self) 
            block.add_connector("Img Entrada", is_input=True)
            
        elif block_name == "Processamento Pontual":
            block = BlockPunctual(block_name, self)
            block.add_connector("Img Entrada", is_input=True)
            block.add_connector("Img Saída", is_input=False)

        elif block_name == "Máscara de Convolução":
            block = NodeBlock(block_name, self) 
            block.add_connector("Img Entrada", is_input=True)
            block.add_connector("Img Saída", is_input=False)
            
        elif block_name == "Plotagem de Histograma":
            block = NodeBlock(block_name, self) 
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
        if event.key() == Qt.Key.Key_Delete:
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


# --- 6. CLASSE FlowView  ---
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

        # Configura a Cena e o View
        self.scene = FlowScene()
        self.view = FlowView(self.scene, self)
        
        self.setCentralWidget(self.view)
        
        self.error_dialog = QErrorMessage(self)
        
        # Barra de Ferramentas de Execução
        toolbar = self.addToolBar("Execução")
        self.process_button = QPushButton("Processar Fluxo")
        self.process_button.clicked.connect(self.process_flow)
        toolbar.addWidget(self.process_button)
        
        # Adiciona Docks
        self.create_properties_dock() 
        
        self.scene.selectionChanged.connect(self.on_selection_changed)
        
    def create_properties_dock(self):
        self.props_dock = QDockWidget("Propriedades", self)
        self.props_container = QWidget()
        self.props_layout = QVBoxLayout(self.props_container)
        
        # --- MUDANÇA AQUI ---
        # Texto inicial com instruções
        self.props_layout.addWidget(QLabel(
            "Bem-vindo ao PSE-Image!\n\n"
            "Clique com o botão direito no canvas\n"
            "para adicionar um novo bloco."
        ))
        # --- FIM DA MUDANÇA ---
        
        self.props_layout.addStretch() 
        self.props_dock.setWidget(self.props_container)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.props_dock)

    # --- MUDANÇA AQUI (CORREÇÃO DO BUG) ---
    def clear_properties_layout(self):
        """ Limpa recursivamente todos os widgets E layouts do painel. """
        while self.props_layout.count():
            item = self.props_layout.takeAt(0)
            
            widget = item.widget()
            if widget is not None:
                widget.deleteLater() # Deleta o widget
            
            layout = item.layout()
            if layout is not None:
                self.clear_nested_layout(layout) # Chama o helper recursivo
                layout.deleteLater() # Deleta o layout

    def clear_nested_layout(self, layout):
        """ Helper para limpar layouts aninhados (como QFormLayout). """
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            
            sub_layout = item.layout()
            if sub_layout is not None:
                self.clear_nested_layout(sub_layout)
    # --- FIM DA MUDANÇA ---

    def on_selection_changed(self):
        self.clear_properties_layout()
        selected = self.scene.selectedItems()
        
        if len(selected) == 1 and isinstance(selected[0], NodeBlock):
            block = selected[0]
            self.build_properties_for_block(block)
        else:
            # --- MUDANÇA AQUI ---
            # Texto quando nada está selecionado
            label = QLabel(
                "Clique com o botão direito no canvas\n"
                "para adicionar um novo bloco.\n\n"
                "Selecione um único bloco para ver\n"
                "suas propriedades."
            )
            label.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.props_layout.addWidget(label)
            # --- FIM DA MUDANÇA ---
            self.props_layout.addStretch()

    def build_properties_for_block(self, block):
        self.props_layout.addWidget(QLabel(f"Propriedades: {block.title}"))
        
        if block.title == "Leitura de arquivo RAW":
            self.build_raw_loader_properties(block)
        elif block.title == "Processamento Pontual":
            self.props_layout.addWidget(QLabel("Opções de brilho/limiar aqui..."))
        else:
            self.props_layout.addWidget(QLabel("Este bloco não tem parâmetros."))
            
        self.props_layout.addStretch()

    def build_raw_loader_properties(self, block):
        # ATENÇÃO: QFormLayout precisa ser limpo corretamente
        form_layout = QFormLayout()
        
        self.filepath_label = QLineEdit(block.parameters.get("filepath", "Nenhum arquivo carregado"))
        self.filepath_label.setReadOnly(True)
        form_layout.addRow("Arquivo:", self.filepath_label)
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 8192)
        self.width_spin.setValue(block.parameters.get("width", 256))
        form_layout.addRow("Largura (W):", self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 8192)
        self.height_spin.setValue(block.parameters.get("height", 256))
        form_layout.addRow("Altura (H):", self.height_spin)
        
        self.props_layout.addLayout(form_layout)
        
        load_button = QPushButton("Carregar Arquivo RAW")
        load_button.clicked.connect(lambda: self.load_raw_file(
            block, 
            self.width_spin, 
            self.height_spin, 
            self.filepath_label
        ))
        self.props_layout.addWidget(load_button)

    def load_raw_file(self, block, width_spin, height_spin, filepath_label):
        filepath, _ = QFileDialog.getOpenFileName(self, "Abrir Arquivo RAW", "", "RAW Files (*.raw);;All Files (*)")
        if not filepath:
            return
        width = width_spin.value()
        height = height_spin.value()
        try:
            img_data = np.fromfile(filepath, dtype=np.uint8)
            expected_size = width * height
            if img_data.size != expected_size:
                self.error_dialog.showMessage(
                    f"Erro de Dimensão: O arquivo tem {img_data.size} bytes, "
                    f"mas as dimensões {width}x{height} exigem {expected_size} bytes."
                )
                return
            block.output_data = img_data.reshape((height, width))
            block.parameters["filepath"] = filepath
            block.parameters["width"] = width
            block.parameters["height"] = height
            filepath_label.setText(filepath)
            print(f"Sucesso: Imagem {filepath} carregada.")
        except Exception as e:
            self.error_dialog.showMessage(f"Falha ao ler o arquivo: {e}")

            
    def process_flow(self):
        """ Executa o processamento do grafo (fluxo). """
        print("\n--- INICIANDO PROCESSAMENTO DO FLUXO ---")
        
        all_blocks = [item for item in self.scene.items() if isinstance(item, NodeBlock)]
        
        # 1. Encontra os nós iniciais (sem entradas conectadas)
        root_nodes = [b for b in all_blocks if not b.input_connections]
        
        if not root_nodes:
            print("Processamento falhou: Nenhum nó inicial (como Leitura RAW) encontrado.")
            return
            
        # 2. Faz uma "busca em largura" (BFS) para processar em ordem
        queue = list(root_nodes)
        processed = set()
        
        max_iterations = len(all_blocks) * 2
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


# --- Bloco de Execução Principal ---

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())