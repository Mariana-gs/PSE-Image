import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
    QDockWidget, QListWidget, QGraphicsItem, QGraphicsPathItem,
    QGraphicsEllipseItem, QWidget, QVBoxLayout, QLabel,
    QMenu
)
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QPen, QBrush, QPainterPath, QColor, QTransform, QFont, QAction
)

# --- 1. O Conector (Ponto de Entrada/Saída) ---

class NodeConnector(QGraphicsEllipseItem):
    """ Representa o pequeno círculo (socket) de entrada ou saída em um Bloco. """
    def __init__(self, parent_block, is_input):
        super().__init__(-5, -5, 10, 10, parent_block) # x, y, w, h
        self.parent_block = parent_block
        self.is_input = is_input
        self.wires = [] # Lista de fios conectados a este conector

        # Define a cor baseada no tipo (Entrada/Saída)
        color = QColor("blue") if is_input else QColor("red")
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.GlobalColor.black))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges)

    def mousePressEvent(self, event):
        """ Inicia a criação de um fio quando o conector é clicado. """
        if event.button() == Qt.MouseButton.LeftButton:
            # Informa à cena para iniciar um "fio de rascunho"
            self.scene().start_connection(self)
            event.accept()

    def itemChange(self, change, value):
        """ Quando a posição do conector (ou seu pai) muda, atualiza os fios. """
        if change == QGraphicsItem.GraphicsItemChange.ItemScenePositionHasChanged:
            for wire in self.wires:
                wire.update_path()
        return value

# --- 2. O Bloco (Nó Arrastável) ---

class NodeBlock(QGraphicsItem):
    """ Representa o bloco de processamento arrastável. """
    def __init__(self, title, scene):
        super().__init__()
        self.title = title
        self.width = 160
        self.height = 80 # Altura inicial
        
        self.inputs = []
        self.outputs = []
        
        # O Bloco é móvel e selecionável
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        scene.addItem(self)

    def add_connector(self, label, is_input):
        """ Adiciona um conector de entrada ou saída ao bloco. """
        connector = NodeConnector(self, is_input)
        
        # Posiciona o conector
        if is_input:
            y_pos = 35 + len(self.inputs) * 20
            connector.setPos(0, y_pos) # Lado esquerdo
            self.inputs.append((connector, label))
        else:
            y_pos = 35 + len(self.outputs) * 20
            connector.setPos(self.width, y_pos) # Lado direito
            self.outputs.append((connector, label))
            
        # Ajusta a altura do bloco se necessário para caber os conectores
        self.height = max(self.height, y_pos + 15)
        self.update() # Força o redesenho com a nova altura
        return connector

    def boundingRect(self):
        """ Define a área "clicável" do item. """
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None):
        """ Desenha a aparência do bloco. """
        # Corpo
        painter.setBrush(QBrush(QColor(240, 240, 240)))
        # Borda mais grossa se selecionado
        painter.setPen(QPen(Qt.GlobalColor.black, 2 if self.isSelected() else 1))
        painter.drawRoundedRect(0, 0, self.width, self.height, 5, 5)
        
        # Título
        title_font = QFont()
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.drawText(QRectF(5, 5, self.width - 10, 20), self.title)
        
        # Rótulos dos Conectores
        painter.setFont(QFont()) # Reseta para fonte padrão
        for conn, label in self.inputs:
            painter.drawText(QRectF(15, conn.y() - 10, self.width - 30, 20), label)
        for conn, label in self.outputs:
            # Alinha o texto à direita
            painter.drawText(QRectF(15, conn.y() - 10, self.width - 30, 20), Qt.AlignmentFlag.AlignRight, label)

    def itemChange(self, change, value):
        """ Quando o bloco se move, força os conectores a se atualizarem. """
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for conn, _ in self.inputs + self.outputs:
                for wire in conn.wires:
                    wire.update_path()
        return super().itemChange(change, value)

# --- 3. O Fio de Conexão ---

class ConnectionWire(QGraphicsPathItem):
    """ O fio (curvado) que conecta dois NodeConnectors. """
    def __init__(self, start_connector, scene):
        super().__init__()
        self.start_conn = start_connector
        self.end_conn = None
        self._end_pos = start_connector.scenePos() # Posição final temporária (para rascunho)
        
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        scene.addItem(self)
        self.setZValue(-1) # Garante que o fio fique atrás dos blocos

    def set_end_connector(self, connector):
        """ Define o conector final e "trava" o fio. """
        self.end_conn = connector
        # Adiciona este fio às listas de ambos os conectores
        self.start_conn.wires.append(self)
        self.end_conn.wires.append(self)
        self.update_path()

    def update_temp_end_pos(self, pos):
        """ Atualiza a ponta do fio para seguir o mouse. """
        self._end_pos = pos
        self.update_path()

    def update_path(self):
        """ Redesenha o caminho (curva de Bézier) entre os conectores. """
        p1 = self.start_conn.scenePos()
        p2 = self.end_conn.scenePos() if self.end_conn else self._end_pos
        
        path = QPainterPath()
        path.moveTo(p1)
        
        # Lógica da curva de Bézier (saída horizontal)
        dx = p2.x() - p1.x()
        c1 = QPointF(p1.x() + dx * 0.5, p1.y())
        c2 = QPointF(p2.x() - dx * 0.5, p2.y())
        
        path.cubicTo(c1, c2, p2)
        self.setPath(path)

    def disconnect(self):
        """ Remove o fio dos conectores. """
        if self.start_conn:
            self.start_conn.wires.remove(self)
        if self.end_conn:
            self.end_conn.wires.remove(self)


# --- 4.  Canvas ---

class FlowScene(QGraphicsScene):
    """ Gerencia a lógica de interação, como criar conexões e blocos. """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.draft_wire = None # O fio que está sendo desenhado no momento
        self.setBackgroundBrush(QBrush(QColor(50, 50, 50))) # Fundo escuro

    def start_connection(self, connector):
        """ Chamado por um NodeConnector quando é clicado. """
        self.draft_wire = ConnectionWire(connector, self)

    def mouseMoveEvent(self, event):
        """ Se estivermos desenhando um fio, atualiza sua ponta para o mouse. """
        if self.draft_wire:
            self.draft_wire.update_temp_end_pos(event.scenePos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """ Tenta finalizar a conexão quando o mouse é solto. """
        if self.draft_wire:
            # Verifica se soltamos o mouse sobre um item
            item = self.itemAt(event.scenePos(), QTransform())
            
            if isinstance(item, NodeConnector):
                # Verifica se é uma conexão válida (ex: Saída -> Entrada)
                if self.is_valid_connection(self.draft_wire.start_conn, item):
                    # Conexão válida: Trava o fio
                    self.draft_wire.set_end_connector(item)
                    self.draft_wire = None
                    return
            
            # Conexão inválida: Remove o fio de rascunho
            self.removeItem(self.draft_wire)
            self.draft_wire = None
            
        super().mouseReleaseEvent(event)

    def is_valid_connection(self, start_conn, end_conn):
        """ Regra simples de conexão: não pode ser do mesmo tipo. """
        if start_conn == end_conn:
            return False
        if start_conn.is_input == end_conn.is_input:
            return False
        return True

    def create_block(self, block_name, position):
        """
        Factory para criar novos blocos baseados no nome.
        Esta é a função chamada pelo menu de contexto do View.
        """
        block = NodeBlock(block_name, self)
        
        # Define as "portas" (conectores) de cada bloco
        if block_name == "Leitura de arquivo RAW":
            block.add_connector("Img Saída", is_input=False)
        
        elif block_name == "Exibição de imagem":
            block.add_connector("Img Entrada", is_input=True)
        
        elif block_name == "Gravação de arquivo RAW":
            block.add_connector("Img Entrada", is_input=True)
            
        elif block_name == "Processamento Pontual":
            block.add_connector("Img Entrada", is_input=True)
            block.add_connector("Img Saída", is_input=False)

        elif block_name == "Máscara de Convolução":
            block.add_connector("Img Entrada", is_input=True)
            block.add_connector("Img Saída", is_input=False)
            
        elif block_name == "Plotagem de Histograma":
            block.add_connector("Img Entrada", is_input=True)
            # Este bloco pode não ter saída de imagem
            
        elif block_name == "Diferença entre Imagens":
            block.add_connector("Img A", is_input=True)
            block.add_connector("Img B", is_input=True)
            block.add_connector("Img Saída", is_input=False)
            
        else:
            # Bloco desconhecido (não deve acontecer com o menu)
            self.removeItem(block)
            return None
            
        block.setPos(position)
        return block

    def keyPressEvent(self, event):
        """ Gerencia a exclusão de itens com a tecla 'Delete'. """
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
        """ Helper para excluir um fio e limpar referências. """
        wire.disconnect()
        self.removeItem(wire)

    def delete_block(self, block):
        """ Helper para excluir um bloco e seus fios. """
        # Itera sobre uma cópia da lista, pois vamos modificá-la
        for conn, _ in block.inputs + block.outputs:
            for wire in list(conn.wires): 
                self.delete_wire(wire)
        self.removeItem(block)


# --- 5. O View (O "Canvas" Interativo) ---

class FlowView(QGraphicsView):
    """ O widget que exibe a cena e gerencia o menu de contexto. """
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        
        # Define o modo de arrastar padrão como "Nenhum"
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setRenderHint(self.renderHints().Antialiasing)
        
        # Lista de blocos disponíveis (para o menu)
        self.available_blocks = [
            "Leitura de arquivo RAW",
            "Exibição de imagem",
            "Gravação de arquivo RAW",
            "Processamento Pontual",
            "Máscara de Convolução",
            "Plotagem de Histograma",
            "Diferença entre Imagens"
        ]
        
        # Posição onde o menu foi aberto
        self._context_menu_pos = QPointF()

    def mousePressEvent(self, event):
        """ Altera o modo de arrastar: Mão (Scroll) com botão do meio. """
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        elif event.button() == Qt.MouseButton.LeftButton:
            # Borracha (RubberBand) para seleção
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """ Reseta o modo de arrastar após soltar o clique. """
        super().mouseReleaseEvent(event)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def contextMenuEvent(self, event):
        """ Chamado ao clicar com o botão direito. """
        
        # Salva a posição do clique (em coordenadas da Cena)
        self._context_menu_pos = self.mapToScene(event.pos())
        
        # Cria o menu
        menu = QMenu(self)
        
        # Adiciona as ações
        for block_name in self.available_blocks:
            action = QAction(block_name, self)
            
            # Conecta a ação a um "slot" (função)
            # Usamos lambda para passar o nome do bloco para o slot
            action.triggered.connect(
                lambda checked=False, name=block_name: self.on_context_menu_triggered(name)
            )
            menu.addAction(action)
            
        # Mostra o menu na posição global do cursor
        menu.exec(event.globalPos())

    def on_context_menu_triggered(self, block_name):
        """ Slot chamado quando um item do menu é clicado. """
        # Chama a factory da cena para criar o bloco na posição salva
        self.scene().create_block(block_name, self._context_menu_pos)


# --- 6. A Janela Principal ---

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PSE-Image (PUC Minas)")
        self.setGeometry(100, 100, 1200, 800)

        # Configura a Cena e o View personalizado
        self.scene = FlowScene()
        self.view = FlowView(self.scene, self)
        
        self.setCentralWidget(self.view)
        
        # Adiciona Docks
        self.create_block_library_dock()
        self.create_properties_dock()
        self.create_viewer_dock()
        
    def create_block_library_dock(self):
        """ 
        Cria o painel lateral para a lista de blocos.
        (Agora é apenas uma referência visual).
        """
        block_dock = QDockWidget("Biblioteca de Blocos", self)
        block_list = QListWidget()
        
        # Adiciona os blocos requeridos pelo trabalho
        block_list.addItem("Leitura de arquivo RAW")
        block_list.addItem("Exibição de imagem")
        block_list.addItem("Gravação de arquivo RAW")
        block_list.addItem("Processamento Pontual")
        block_list.addItem("Máscara de Convolução")
        block_list.addItem("Plotagem de Histograma")
        block_list.addItem("Diferença entre Imagens")
        
        block_dock.setWidget(block_list)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, block_dock)

    def create_properties_dock(self):
        """ Cria o painel lateral para editar parâmetros dos blocos. """
        props_dock = QDockWidget("Propriedades", self)
        
        # O conteúdo aqui mudará dependendo do bloco selecionado
        props_widget = QWidget()
        props_layout = QVBoxLayout()
        props_layout.addWidget(QLabel("Selecione um bloco para ver suas propriedades."))
        props_widget.setLayout(props_layout)
        
        props_dock.setWidget(props_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, props_dock)

    def create_viewer_dock(self):
        """ Cria o painel para o 'Bloco de exibição'. """
        viewer_dock = QDockWidget("Visualizador", self)
        
        # Este widget será o alvo do bloco "Exibição de imagem"
        viewer_label = QLabel("A saída dos blocos 'Exibição' aparecerá aqui.")
        viewer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        viewer_dock.setWidget(viewer_label)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, viewer_dock)


# --- Bloco de Execução Principal ---

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())