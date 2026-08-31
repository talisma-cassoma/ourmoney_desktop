from PyQt5 import QtCore
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout,
                             QLineEdit, QFormLayout, QHBoxLayout, QFrame, QPushButton, 
                             QLabel, QComboBox, QProgressBar, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, QMenu,
                             QDialog, QDateEdit, QToolButton, QWidgetAction, QCheckBox, QWidget, QStackedWidget
                             )

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QPixmap, QIcon, QPainter
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtSvg import QSvgRenderer


from datetime import datetime
import time
import logging
import random
from household_view import HouseHoldList
from bot_ui import BotUI

# Configuração do logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')


Total_font = QFont()
Total_font.setPointSize(14)  # Set the font size to 14 (adjust as needed)
Total_font.setBold(True)  # Make the text bold

from PyQt5.QtCore import QThread, pyqtSignal

def create_checkbox_menu_button(title, options, selected_options_set):
    """
    Cria um botão com menu suspenso contendo checkboxes.
    
    :param title: Título do botão principal.
    :param options: Lista de strings (opções).
    :param callback: Função chamada quando checkbox é clicado.
    :param selected_options_set: Set externo compartilhado para controle de seleção.
    :return: QPushButton
    """
    button = QPushButton(title)
    button.setStyleSheet("background-color: #333; font-size: 12px; color: white;")
    button.setCursor(Qt.PointingHandCursor)

    menu = QMenu()
    menu.setStyleSheet("""
        QMenu {
            color: white;
            border: 1px solid rgb(41, 41, 46);
            padding: 4px;
        }
        QMenu::item {
            padding: 4px 10px;
            color: white;          
        }
    """)

    for option in options:
        checkbox = QCheckBox(option)
        checkbox.setChecked(option in selected_options_set)

        def toggle_option(checked, opt=option):
            if checked:
                selected_options_set.add(opt)
            else:
                selected_options_set.discard(opt)

        checkbox.stateChanged.connect(toggle_option)

        action = QWidgetAction(menu)
        action.setDefaultWidget(checkbox)
        menu.addAction(action)

    button.setMenu(menu)
    return button

class StatusCheckerThread(QThread):
    status_signal = pyqtSignal(bool)  # Signal to emit the online status

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.running = True  # Flag to control thread execution

    def run(self):
        while self.running:
            # Check the status
            online = self.controller.is_online()
            self.status_signal.emit(online)
            self.msleep(5000)  # Wait for 5 seconds between checks

    def stop(self):
        self.running = False

class SyncThread(QThread):
    progress_signal = pyqtSignal(int)  # Sinal para atualizar a barra de progresso
    finished_signal = pyqtSignal()  # Sinal para enviar os dados sincronizados

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    def run(self):
       
        for i in range(0, 101, 10):  # Simula progresso
            self.progress_signal.emit(i)
            self.msleep(100)
        
        # Executa o processo de sincronização
        self.controller.synchronize_data()
        self.finished_signal.emit()
        
class MainWindow(QMainWindow):
    def __init__(self,):
        super().__init__()
        self.controller = None
        self.last_date = None
        #self.last_added_transaction = {'price': 0.0, 'type': '' }
        self.fetching = False
        self.total_of_income = 0
        self.total_of_outcome = 0

        # Create and start the thread for status updates
        self.status_thread = None

        self.sync_thread = None

        self.filters = {
            "keyword": "",
            "category": set(),
            "type": set(),
            "status": set(),
            "start_date": None,
            "end_date": None,
        }

    def set_controller(self, controller):
        """Define o controlador para a GUI."""
        self.controller = controller
        self.total_of_income, self.total_of_outcome = self.controller.get_total_of_transactions(self.filters)
        
        self.initUI()
        
        # Create and start the thread for status updates
        self.status_thread = StatusCheckerThread(self.controller)
        self.status_thread.status_signal.connect(self.update_status_label)
        self.status_thread.start()

    def update_status_label(self, online):
        if online:
            self.status_label.setText("Status: Online")
        else:
            self.status_label.setText("Status: Offline")

    def closeEvent(self, event):
        # Ensure the thread stops when the application closes
        self.status_thread.stop()
        self.status_thread.wait()
        super().closeEvent(event)

    def initUI(self):
        self.setWindowTitle("OUR-MONKEY")
        self.setGeometry(100, 100, 950, 750)

        # Layout horizontal principal
        self.outer_layout = QHBoxLayout()
        outer_widget = QWidget()
        outer_widget.setLayout(self.outer_layout)
        outer_widget.setStyleSheet("background-color: rgb(61, 61, 66); color: #D3D3D3;")
        self.setCentralWidget(outer_widget)

        # --- SIDEBAR ---
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(160)
        self.sidebar.setStyleSheet("""
            QFrame {
                background-color: rgb(41, 41, 46);
                border-radius: 12px;
                padding: 5px 5px;
            }
            QPushButton {
                text-align: left;
                background-color: transparent;
                color: #D3D3D3;
                border: none;
                font-size: 14px;
                height: 30px;
                padding: 10px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgb(61, 61, 61);;
            }
            QPushButton:checked {
                background-color: #3A3A45;
                color: #FFFFFF;
            }
            """)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(10)

        # Botão de navegação 1
        home_btn = QPushButton("Home")  # pode substituir por ícones
        home_btn.setIcon(self.svg_icon(
            '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" stroke="#fff0f0" data-darkreader-inline-stroke="" style="--darkreader-inline-stroke: var(--darkreader-text-2b2b2b, #cdc8c2);"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"> <path d="M22 12.2039V13.725C22 17.6258 22 19.5763 20.8284 20.7881C19.6569 22 17.7712 22 14 22H10C6.22876 22 4.34315 22 3.17157 20.7881C2 19.5763 2 17.6258 2 13.725V12.2039C2 9.91549 2 8.77128 2.5192 7.82274C3.0384 6.87421 3.98695 6.28551 5.88403 5.10813L7.88403 3.86687C9.88939 2.62229 10.8921 2 12 2C13.1079 2 14.1106 2.62229 16.116 3.86687L18.116 5.10812C20.0131 6.28551 20.9616 6.87421 21.4808 7.82274" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" data-darkreader-inline-stroke="" style="--darkreader-inline-stroke: var(--darkreader-text-ffffff, #e8e6e3);"></path> <path d="M15 18H9" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" data-darkreader-inline-stroke="" style="--darkreader-inline-stroke: var(--darkreader-text-ffffff, #e8e6e3);"></path> </g></svg>'''
        ))
        home_btn.setStyleSheet("height: 30px; text-align: left; padding: 10px; border-radius: 6px;")
        home_btn.clicked.connect(lambda: self.switch_section(0))
        self.sidebar_layout.addWidget(home_btn)

        # Botão de navegação 2
        house_hold_list_btn = QPushButton("lista de compras")
        #btn2.setStyleSheet("color: white; background-color: transparent; border: none;")
        house_hold_list_btn.clicked.connect(lambda: self.switch_section(1))
        #house_hold_list_btn.setStyleSheet("padding: 5px")
        self.sidebar_layout.addWidget(house_hold_list_btn)

        # Botão de navegação 3
        bot_ui_btn = QPushButton("Chatbot")
        bot_ui_btn.setIcon(self.svg_icon(
            '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" stroke="#fff" data-darkreader-inline-stroke="" style="--darkreader-inline-stroke: var(--darkreader-text-292828, #fff);"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"> <path d="M12 15V7" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" data-darkreader-inline-stroke="" style="--darkreader-inline-stroke: var(--darkreader-text-ffffff, #e8e6e3);"></path> <path d="M8 13V9" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" data-darkreader-inline-stroke="" style="--darkreader-inline-stroke: var(--darkreader-text-ffffff, #e8e6e3);"></path> <path d="M16 13V9" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" data-darkreader-inline-stroke="" style="--darkreader-inline-stroke: var(--darkreader-text-ffffff, #e8e6e3);"></path> <path d="M13.0867 21.3877L13.7321 21.7697L13.0867 21.3877ZM13.6288 20.4718L12.9833 20.0898L13.6288 20.4718ZM10.3712 20.4718L9.72579 20.8539H9.72579L10.3712 20.4718ZM10.9133 21.3877L11.5587 21.0057L10.9133 21.3877ZM1.25 10.5C1.25 10.9142 1.58579 11.25 2 11.25C2.41421 11.25 2.75 10.9142 2.75 10.5H1.25ZM3.07351 15.6264C2.915 15.2437 2.47627 15.062 2.09359 15.2205C1.71091 15.379 1.52918 15.8177 1.68769 16.2004L3.07351 15.6264ZM7.78958 18.9915L7.77666 19.7413L7.78958 18.9915ZM5.08658 18.6194L4.79957 19.3123H4.79957L5.08658 18.6194ZM21.6194 15.9134L22.3123 16.2004V16.2004L21.6194 15.9134ZM16.2104 18.9915L16.1975 18.2416L16.2104 18.9915ZM18.9134 18.6194L19.2004 19.3123H19.2004L18.9134 18.6194ZM19.6125 2.7368L19.2206 3.37628L19.6125 2.7368ZM21.2632 4.38751L21.9027 3.99563V3.99563L21.2632 4.38751ZM4.38751 2.7368L3.99563 2.09732V2.09732L4.38751 2.7368ZM2.7368 4.38751L2.09732 3.99563H2.09732L2.7368 4.38751ZM9.40279 19.2098L9.77986 18.5615L9.77986 18.5615L9.40279 19.2098ZM13.7321 21.7697L14.2742 20.8539L12.9833 20.0898L12.4412 21.0057L13.7321 21.7697ZM9.72579 20.8539L10.2679 21.7697L11.5587 21.0057L11.0166 20.0898L9.72579 20.8539ZM12.4412 21.0057C12.2485 21.3313 11.7515 21.3313 11.5587 21.0057L10.2679 21.7697C11.0415 23.0767 12.9585 23.0767 13.7321 21.7697L12.4412 21.0057ZM10.5 2.75H13.5V1.25H10.5V2.75ZM21.25 10.5V11.5H22.75V10.5H21.25ZM7.8025 18.2416C6.54706 18.2199 5.88923 18.1401 5.37359 17.9265L4.79957 19.3123C5.60454 19.6457 6.52138 19.7197 7.77666 19.7413L7.8025 18.2416ZM1.68769 16.2004C2.27128 17.6093 3.39066 18.7287 4.79957 19.3123L5.3736 17.9265C4.33223 17.4951 3.50486 16.6678 3.07351 15.6264L1.68769 16.2004ZM21.25 11.5C21.25 12.6751 21.2496 13.5189 21.2042 14.1847C21.1592 14.8438 21.0726 15.2736 20.9265 15.6264L22.3123 16.2004C22.5468 15.6344 22.6505 15.0223 22.7007 14.2868C22.7504 13.5581 22.75 12.6546 22.75 11.5H21.25ZM16.2233 19.7413C17.4786 19.7197 18.3955 19.6457 19.2004 19.3123L18.6264 17.9265C18.1108 18.1401 17.4529 18.2199 16.1975 18.2416L16.2233 19.7413ZM20.9265 15.6264C20.4951 16.6678 19.6678 17.4951 18.6264 17.9265L19.2004 19.3123C20.6093 18.7287 21.7287 17.6093 22.3123 16.2004L20.9265 15.6264ZM13.5 2.75C15.1512 2.75 16.337 2.75079 17.2619 2.83873C18.1757 2.92561 18.7571 3.09223 19.2206 3.37628L20.0044 2.09732C19.2655 1.64457 18.4274 1.44279 17.4039 1.34547C16.3915 1.24921 15.1222 1.25 13.5 1.25V2.75ZM22.75 10.5C22.75 8.87781 22.7508 7.6085 22.6545 6.59611C22.5572 5.57256 22.3554 4.73445 21.9027 3.99563L20.6237 4.77938C20.9078 5.24291 21.0744 5.82434 21.1613 6.73809C21.2492 7.663 21.25 8.84876 21.25 10.5H22.75ZM19.2206 3.37628C19.7925 3.72672 20.2733 4.20752 20.6237 4.77938L21.9027 3.99563C21.4286 3.22194 20.7781 2.57144 20.0044 2.09732L19.2206 3.37628ZM10.5 1.25C8.87781 1.25 7.6085 1.24921 6.59611 1.34547C5.57256 1.44279 4.73445 1.64457 3.99563 2.09732L4.77938 3.37628C5.24291 3.09223 5.82434 2.92561 6.73809 2.83873C7.663 2.75079 8.84876 2.75 10.5 2.75V1.25ZM2.75 10.5C2.75 8.84876 2.75079 7.663 2.83873 6.73809C2.92561 5.82434 3.09223 5.24291 3.37628 4.77938L2.09732 3.99563C1.64457 4.73445 1.44279 5.57256 1.34547 6.59611C1.24921 7.6085 1.25 8.87781 1.25 10.5H2.75ZM3.99563 2.09732C3.22194 2.57144 2.57144 3.22194 2.09732 3.99563L3.37628 4.77938C3.72672 4.20752 4.20752 3.72672 4.77938 3.37628L3.99563 2.09732ZM11.0166 20.0898C10.8136 19.7468 10.6354 19.4441 10.4621 19.2063C10.2795 18.9559 10.0702 18.7304 9.77986 18.5615L9.02572 19.8582C9.07313 19.8857 9.13772 19.936 9.24985 20.0898C9.37122 20.2564 9.50835 20.4865 9.72579 20.8539L11.0166 20.0898ZM7.77666 19.7413C8.21575 19.7489 8.49387 19.7545 8.70588 19.7779C8.90399 19.7999 8.98078 19.832 9.02572 19.8582L9.77986 18.5615C9.4871 18.3912 9.18246 18.3215 8.87097 18.287C8.57339 18.2541 8.21375 18.2487 7.8025 18.2416L7.77666 19.7413ZM14.2742 20.8539C14.4916 20.4865 14.6287 20.2564 14.7501 20.0898C14.8622 19.936 14.9268 19.8857 14.9742 19.8582L14.2201 18.5615C13.9298 18.7304 13.7204 18.9559 13.5379 19.2063C13.3646 19.4441 13.1864 19.7468 12.9833 20.0898L14.2742 20.8539ZM16.1975 18.2416C15.7862 18.2487 15.4266 18.2541 15.129 18.287C14.8175 18.3215 14.5129 18.3912 14.2201 18.5615L14.9742 19.8582C15.0192 19.832 15.096 19.7999 15.2941 19.7779C15.5061 19.7545 15.7842 19.7489 16.2233 19.7413L16.1975 18.2416Z" fill="#fff" data-darkreader-inline-fill="#FFF" style="--darkreader-inline-fill: var(--darkreader-background-ffffff, #fff);"></path> </g></svg>'''
        ))
        #btn3.setStyleSheet("color: white; background-color: transparent; border: none;")
        bot_ui_btn.clicked.connect(lambda: self.switch_section(2))
        #bot_ui_btn.setStyleSheet("padding: 5px")
        self.sidebar_layout.addWidget(bot_ui_btn) 

        self.sidebar_layout.addStretch()
        self.outer_layout.addWidget(self.sidebar)

        # --- ÁREA DE CONTEÚDO ---
        self.stack = QStackedWidget()
        self.outer_layout.addWidget(self.stack)

        # Página 0: conteúdo atual
        self.main_frame = QFrame()
        self.main_layout = QVBoxLayout(self.main_frame)
        self.main_frame.setStyleSheet("background-color: rgb(61, 61, 66); color: #D3D3D3;")
        self.stack.addWidget(self.main_frame)

        # Página 1: futura seção        
        self.household_section = HouseHoldList()
        self.household_section.setStyleSheet("background-color: rgb(61, 61, 66); color: #D3D3D3;")
        self.stack.addWidget(self.household_section)


        self.bot_ui_section = BotUI()
        self.bot_ui_section.setStyleSheet("background-color: rgb(61, 61, 66); color: #D3D3D3;")
        self.stack.addWidget(self.bot_ui_section)
        

        # Status and sync area at the top
        self.status_frame = QFrame()
        self.status_layout = QHBoxLayout(self.status_frame)

        self.status_label = QLabel("Status: Checando...")
        self.status_layout.addWidget(self.status_label)

        self.sync_button = QPushButton("Sincronizar")
        self.sync_button.clicked.connect(self.sync_and_show_progress)
        self.status_layout.addWidget(self.sync_button)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setStyleSheet("background-color: black")
        self.progress_bar.setValue(0)
        self.status_layout.addWidget(self.progress_bar)

        """ save file """
        self.safe_file_label = QLabel("guardar em:")
        self.status_layout.addWidget(self.safe_file_label)

        self.file_type_input = QComboBox()
        self.file_type_input.setStyleSheet("color: white;")
        self.file_type_input.addItems(["json", "csv", "excel", "report"])
        # Connect signals to the methods.
        self.file_type_input.activated.connect(self.save_file)
        # # Add block 1 to thes status layout
        self.status_layout.addWidget(self.file_type_input)
    
        self.main_layout.addWidget(self.status_frame)

        # Two blocks (side by side) for transaction input and totals
        self.blocks_frame = QFrame()
        self.blocks_layout = QHBoxLayout(self.blocks_frame)
        self.blocks_frame.setStyleSheet("background-color: rgb(41, 41, 46); border-radius: 4px;")

        # Block 1: Transaction inputs
        self.transaction_inputs_frame = QFrame()
        self.transaction_inputs_frame.setFixedWidth(400)
        self.transaction_inputs_frame.setStyleSheet("background-color: rgb(61, 61, 66); border-radius: 4px; color: #D3D3D3;")
        self.transaction_inputs_layout = QFormLayout(self.transaction_inputs_frame)

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText('Descrição')

        self.type_input = QComboBox()
        self.type_input.setStyleSheet("color: white;")
        self.type_input.addItems(["saida", "entrada"])

        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText('Categoria')

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText('Preço')

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        today = datetime.today().strftime("%d-%m-%Y")
        self.date_input.setDate(QDate.fromString(today, "dd-MM-yyyy"))


        self.add_button = QPushButton(text="Adicionar Transação")
        self.add_button.clicked.connect(self.add_transaction)

        # Add widgets to the layout
        self.transaction_inputs_layout.addRow('Descrição:', self.description_input)
        self.transaction_inputs_layout.addRow('Tipo:', self.type_input)
        self.transaction_inputs_layout.addRow('Categoria:', self.category_input)
        self.transaction_inputs_layout.addRow('Preço:', self.price_input)
        self.transaction_inputs_layout.addRow('Data:', self.date_input)
        self.transaction_inputs_layout.addRow(self.add_button)

        # Add block 1 to the main layout
        self.blocks_layout.addWidget(self.transaction_inputs_frame)

        # Block 2: Total incomes and expenses
        self.totals_frame = QFrame()
        self.totals_frame.setStyleSheet("background-color: rgb(61, 61, 66); border-radius: 8px; padding: 10px;")
        self.totals_layout = QVBoxLayout(self.totals_frame)

        formatted_income = f"{self.total_of_income:,.2f}".replace(",", " ")
        formatted_outcome = f"{self.total_of_outcome:,.2f}".replace(",", " ")

        self.income_label = QLabel(f'Entradas: {formatted_income} DH$')
        self.income_label.setAlignment(QtCore.Qt.AlignCenter)
        self.income_label.setFont(Total_font)
        self.expense_label = QLabel(f'Saídas: {formatted_outcome} DH$')
        self.expense_label.setAlignment(QtCore.Qt.AlignCenter)
        self.expense_label.setFont(Total_font)
        self.income_label.setStyleSheet("color: rgb(79, 255, 203);")
        self.expense_label.setStyleSheet("color: rgb(247, 91, 105);")

        self.totals_layout.addWidget(self.income_label)
        self.totals_layout.addWidget(self.expense_label)

        # Add block 2 to the main layout
        self.blocks_layout.addWidget(self.totals_frame)

        self.main_layout.addWidget(self.blocks_frame)

  # --- search + filter area ---
        self.search_frame = QFrame()
        hl = QHBoxLayout(self.search_frame)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(5)


        # Campo de busca
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setStyleSheet("background-color: black; padding: 6px;")
        hl.addWidget(self.search_input, 1)
        
        # Botão de busca com SVG
        self.search_btn = QToolButton()
        self.search_btn.setIcon(self.svg_icon(
            '''<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="white"><path d="M784-120 532-372q-30 24-69 38t-83 14q-109 0-184.5-75.5T120-580q0-109 75.5-184.5T380-840q109 0 184.5 75.5T640-580q0 44-14 83t-38 69l252 252-56 56ZM380-400q75 0 127.5-52.5T560-580q0-75-52.5-127.5T380-760q-75 0-127.5 52.5T200-580q0 75 52.5 127.5T380-400Z"/></svg>'''
        ))
        self.search_btn.setAutoRaise(True)
        self.search_btn.clicked.connect(self.update_keyword_filter)
        hl.addWidget(self.search_btn)

        # Botão de filtro
        self.filter_btn = QToolButton()
        self.filter_btn.setIcon(self.svg_icon(
            '''<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="white"><path d="M440-120v-240h80v80h320v80H520v80h-80Zm-320-80v-80h240v80H120Zm160-160v-80H120v-80h160v-80h80v240h-80Zm160-80v-80h400v80H440Zm160-160v-240h80v80h160v80H680v80h-80Zm-480-80v-80h400v80H120Z"/></svg>'''
        ))
        self.filter_btn.setAutoRaise(True)
        self.filter_btn.clicked.connect(self.toggle_filters)
        hl.addWidget(self.filter_btn)

        self.main_layout.addWidget(self.search_frame)

        # Frame de filtros
        self.filter_frame = QFrame()
        self.filter_frame.setVisible(False)
        fl = QHBoxLayout(self.filter_frame)
        fl.setContentsMargins(0,0,0,0)
        fl.setSpacing(10)

        # Filtros fixos por categoria
        category_btn = create_checkbox_menu_button(
              title="categoria",
              options=["alimentaçao e casa", "internet", "saude", "bebida", "emprestimo", "divida", "roupas e calçados", "transporte", "gas"], 
                selected_options_set= self.filters["category"])

        
        fl.addWidget(category_btn)

        # Filtro de status
        status_button = create_checkbox_menu_button(
            title="status", 
            options=["sincronizado", "dessincronizado"], 
            selected_options_set = self.filters["status"]
        )
        fl.addWidget(status_button)

        #Filtro de tipo
        type_filter_button = create_checkbox_menu_button(
            title="tipo", 
            options=["entrada","saida"], 
            selected_options_set = self.filters["type"]
            )
                
        fl.addWidget(type_filter_button)

        #Filter start date
        self.start_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDisplayFormat("dd-MM-yyyy")
        self.start_date_input.setDate(QDate.fromString(today, "dd-MM-yyyy"))

        fl.addWidget(QLabel("De:"))
        fl.addWidget(self.start_date_input)

        #Filter end date
        self.end_date_input = QDateEdit()
        self.end_date_input.setCalendarPopup(True)
        self.end_date_input.setDisplayFormat("dd-MM-yyyy")
        self.end_date_input.setDate(QDate.fromString(today, "dd-MM-yyyy"))

        fl.addWidget(QLabel("Até:"))
        fl.addWidget(self.end_date_input)

       
        self.main_layout.addWidget(self.filter_frame)

        # Block 3: List of registered transactions using QTableWidget
        self.transaction_list_frame = QFrame()
        self.transaction_list_frame.setStyleSheet("background-color: rgb(41, 41, 46); border-radius: 2px;")
        self.transaction_list_layout = QVBoxLayout(self.transaction_list_frame)

        self.transactions_label = QLabel('Transações Registradas')
        self.transactions_label.setStyleSheet("color: white;")
        self.transaction_list_layout.addWidget(self.transactions_label)

        # Create the table widget
        self.transaction_table = QTableWidget()
        self.transaction_table.setColumnCount(7)  # Adjust number of columns based on the data
        self.transaction_table.setHorizontalHeaderLabels(['Descrição', 'Ações', 'Tipo', 'Categoria', 'Preço', 'Data', 'Sincronizado'])
        self.transaction_table.setStyleSheet("color: white; ")

        self.transaction_table.verticalScrollBar().valueChanged.connect(self.on_scroll) # Connect scroll event

        # Set fixed height for rows
        #self.transaction_table.setFixedHeight(300)  # Set a fixed height for the table
        self.transaction_table.verticalHeader().setDefaultSectionSize(50)  # Set a default row height
        # Hide the vertical row numbers
        self.transaction_table.verticalHeader().setVisible(False)

        self.transaction_table.setColumnWidth(0, 150)  # Make last column stretch
        self.transaction_table.setColumnWidth(1, 60) # 
        self.transaction_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  # Resize columns to fit the table
        self.transaction_list_layout.addWidget(self.transaction_table)

        self.main_layout.addWidget(self.transaction_list_frame)

        #self.setCentralWidget(self.main_frame)

        # Load registered transactions
        self.load_collection()
        
    def switch_section(self, index):
        self.stack.setCurrentIndex(index)

    def save_file(self, index):
        self.controller.export_file(index)

    def sync_and_show_progress(self):
        if self.sync_thread and self.sync_thread.isRunning():
            QMessageBox.warning(self, "Sincronização em andamento", "A sincronização já está em andamento!")
            return

        self.sync_thread = SyncThread(self.controller)
        self.sync_thread.progress_signal.connect(self.update_progress_bar)
        self.sync_thread.finished_signal.connect(self.sync_finished)

        self.progress_bar.setValue(0)
        self.sync_thread.start()

    def update_progress_bar(self, value):
        """Atualiza o valor da barra de progresso."""
        self.progress_bar.setValue(value)

    def sync_finished(self):
        """Executado quando a sincronização termina."""       
        self.controller.main_window.last_date = None
        self.controller.main_window.load_collection()
        self.progress_bar.setValue(100)

    def add_transaction(self):
        description = self.description_input.text().strip().lower()
        trans_type = self.type_input.currentText().lower()
        category = self.category_input.text().strip().lower()
        price_text = self.price_input.text().strip()
    
        # Monta data ISO: data do input + hora atual
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        now = datetime.utcnow()
        time_str = now.strftime("%H:%M:%S.%f")[:-3]
        date = f"{date_str}T{time_str}Z"
    
        # Permite expressões matemáticas simples (ex: 10+5)
        try:
            code = compile(price_text, "<string>", "eval")
        except SyntaxError:
            QMessageBox.warning(self, "Erro", "Expressão inválida no preço.")
            return
    
        if code.co_names:
            QMessageBox.warning(self, "Erro", "Expressão contém nomes não permitidos.")
            return
    
        try:
            input_result = eval(code, {"__builtins__": {}}, {})
            price = float(input_result)
        except Exception:
            QMessageBox.warning(self, "Erro", "Preço deve ser um número válido!")
            return
    
        # Validação dos campos
        if not description or not trans_type or not category or not price_text:
            QMessageBox.warning(self, "Erro", "Todos os campos são obrigatórios!")
            return
    
        # Insere a transação
        self.controller.insert_transaction(
            description,
            "income" if trans_type == "entrada" else "outcome",
            category,
            price,
            date=date
        )
    
        self.last_date = None
    
        # Atualiza os totais
        if trans_type == "entrada":
            self.total_of_income += price
            self.income_label.setText(
                f"Entradas: {self.total_of_income:,.2f} DH$".replace(",", " ")
            )
        else:
            self.total_of_outcome += price
            self.expense_label.setText(
                f"Saídas: {self.total_of_outcome:,.2f} DH$".replace(",", " ")
            )
    
        self.load_collection()
        self.clear_inputs()
            
    def load_collection(self, append=False):
        """
        Load transactions into the table. If `append` is True, add to the existing table.
        """
        # Set fetching flag to avoid duplicate fetches
        if self.fetching:
            return

        self.fetching = True

        # Fetch transactions
        transactions = self.controller.fetch_transactions(self.last_date, self.filters)

        if not append:
            self.transaction_table.setRowCount(0)  # Clear the table if not appending

        for transaction in transactions:
            row_position = self.transaction_table.rowCount()
            self.transaction_table.insertRow(row_position)

            # Map and populate transaction fields
            self.transaction_table.setItem(row_position, 0, QTableWidgetItem(transaction.description))  # Description
            type_item = QTableWidgetItem('entrada' if transaction.type == 'income' else 'saida')  # Type
            self.transaction_table.setItem(row_position, 2, type_item)

            self.transaction_table.setItem(row_position, 3, QTableWidgetItem(transaction.category))  # Category
            price_color = "rgb(79, 255, 203)" if transaction.type == "income" else "rgb(247, 91, 105)"
            price = QLabel(f'{transaction.price}')
            price.setStyleSheet(f'color: {price_color};')
            self.transaction_table.setCellWidget(row_position, 4, price)
            
            try:
                # Check if transaction[7] is not None or empty
                if not transaction.created_at:
                    raise ValueError("Empty or None date string")
                date = transaction.created_at

                self.transaction_table.setItem(row_position, 5, QTableWidgetItem(date))
            except Exception as e:
                logging.error(f'Unexpected error with id: {transaction.id} with date: {date} , error: {e}')

            # Display synced status
            synced_color = "rgb(79, 255, 203)" if transaction.status =='synced' else "rgb(128, 128, 128)"
            synced_status = QLabel("sincronizado" if transaction.status=='synced' else "desincronizado")
            synced_status.setStyleSheet(f'color: {synced_color};')
            self.transaction_table.setCellWidget(row_position, 6, synced_status)

            # Delete button with confirmation dialog
            # delete_button = QPushButton('Deletar')
            # delete_button.setStyleSheet("color: white;")
            # delete_button.clicked.connect(lambda _, trans_id=transaction.id: self.confirm_delete_transaction(trans_id))
            # self.transaction_table.setCellWidget(row_position, 6, delete_button)
            
            # Create ellipsis menu for actions
            ellipsis_button = QPushButton("⋮")
            ellipsis_button.setStyleSheet("background: transparent; font-size: 18px; color: white; width: 5px;")
            ellipsis_button.setCursor(Qt.PointingHandCursor)
            
            # Add menu to button
            menu = QMenu()
            menu.setStyleSheet("""
                QMenu {
                    background-color: rgb(61, 61, 66);
                    color: white;
                    border: 1px solid rgb(41, 41, 46);
                    padding: 4px;
                    width: 60px; /* Reduce width */
                }
                QMenu::item {
                    padding: 4px 10px; /* Adjust padding for compactness */
                    font-size: 12px; /* Smaller font size */
                }
                QMenu::item:selected {
                    background-color: rgb(79, 255, 203); /* Highlight color */
                    color: rgb(128, 128, 128)
                }
             """)
            edit_action = menu.addAction("Edit")
            delete_action = menu.addAction("Delete")
        
            ellipsis_button.setMenu(menu)
        
            # Connect actions
            edit_action.triggered.connect(lambda _,id = transaction.id,
                description=transaction.description,
                type=transaction.type,
                category=transaction.category,
                price= transaction.price,
                status= transaction.status,
                date=date: self.open_edit_dialog(id,description,type,category, price, status, date))
            delete_action.triggered.connect(lambda _, trans_id=transaction.id: self.confirm_delete_transaction(trans_id))
        
            # Add ellipsis button to table
            self.transaction_table.setCellWidget(row_position, 1, ellipsis_button)
        

            # Save the last transaction's date
            self.last_date = transaction.created_at
        
        self.fetching = False

    def on_scroll(self, value):
        """
        Detect when the user scrolls near the bottom and load more transactions.
        """
        scroll_bar = self.transaction_table.verticalScrollBar()
        if value == scroll_bar.maximum() and not self.fetching:
            self.load_collection(append=True)

    def confirm_delete_transaction(self, transaction_id):
        # Create a confirmation dialog
        reply = QMessageBox.question(self, 'Confirmação', "Você realmente quer deletar esta transação?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        # If user confirms, delete the transaction
        if reply == QMessageBox.Yes:
            self.delete_transaction(transaction_id)

    def delete_transaction(self, transaction_id):
        # Delete the transaction via the controller
        self.controller.delete_transaction(transaction_id)
        self.last_date = None

        # Recalculate totals using the active filter set
        self.total_of_income, self.total_of_outcome = self.controller.get_total_of_transactions(self.filters)

        # Format totals with space as a thousands separator
        formatted_income = f"{self.total_of_income:,.2f}".replace(",", " ")
        formatted_outcome = f"{self.total_of_outcome:,.2f}".replace(",", " ")

        # Update labels with formatted values
        self.income_label.setText(f"Entradas: {formatted_income} DH$")
        self.expense_label.setText(f"Saídas: {formatted_outcome} DH$")

        # Refresh the table after deletion
        self.load_collection()
    
    def open_edit_dialog(self, id,description,type,category,price, status, date):
        # Criar o diálogo
        dialog = QDialog(self)
        dialog.setWindowTitle("Editar Transação")
        dialog.setFixedWidth(400)

        # Layout do diálogo
        layout = QFormLayout(dialog)

        # Inputs
        description_input = QLineEdit(description)
        type_input = QComboBox()
        type_input.addItems(["saida", "entrada"])
        type_input.setCurrentText(type)
        category_input = QLineEdit(category)
        date_input = QDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDate(QDate.fromString(date, "dd-MM-yyyy"))
        price_input = QLineEdit(price.replace(" DH$", ""))
        
        # Botões
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Salvar")
        cancel_button = QPushButton("Cancelar")
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)

        # Adicionar ao layout
        layout.addRow("Descrição:", description_input)
        layout.addRow("Tipo:", type_input)
        layout.addRow("Categoria:", category_input)
        layout.addRow("Preço:", price_input)
        layout.addRow("Data:", date_input)
        layout.addRow(buttons_layout)

        # Conectar botões
        cancel_button.clicked.connect(dialog.reject)
        save_button.clicked.connect(lambda: self.save_edited_transaction(dialog, id, description_input, type_input, category_input, price_input.text().strip(), status, date_input))

        # Mostrar o diálogo
        dialog.exec_()

    def save_edited_transaction(
        self,
        dialog,
        id,
        description_input,
        type_input_widget,
        category_input,
        price,
        status,
        date_input
    ):
        self.last_date = None

        transaction_id = str(id)
        description = description_input.text()
        transaction_type = type_input_widget.currentText()
        category = category_input.text()

        # Garante conversão correta do preço
        price = float(str(price).replace(",", "."))

        status = str(status)

        date_str = date_input.date().toString("yyyy-MM-dd")

        now = datetime.utcnow()
        time_str = now.strftime("%H:%M:%S.%f")[:-3]

        date = f"{date_str}T{time_str}Z"

        self.controller.edit_transaction(
            transaction_id,
            description,
            transaction_type,
            category,
            price,
            status,
            date
        )

        dialog.accept()
        self.load_collection()
    

    def svg_icon(self, svg_str):
        """Converte string SVG em QIcon."""
        renderer = QSvgRenderer(bytearray(svg_str, encoding='utf-8'))
        pix = QPixmap(24, 24)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        renderer.render(painter)
        painter.end()
        return QIcon(pix)

    def toggle_filters(self):
        self.filter_frame.setVisible(not self.filter_frame.isVisible())

    def clear_inputs(self):
        self.description_input.clear()
        self.category_input.clear()
        self.price_input.clear()

    def update_date_filters(self):

        start_date = self.start_date_input.date()
        end_date = self.end_date_input.date()

        if start_date > end_date:
            QMessageBox.warning(
                self,
                "Período inválido",
                "A data inicial não pode ser posterior à data final."
            )
            return False
        
        self.filters["start_date"] = start_date
        self.filters["end_date"] = end_date

        return True

    def update_keyword_filter(self): 
        self.last_date = None

        self.filters["keyword"] = self.search_input.text().strip().lower()

        if not self.update_date_filters():
            return
    
        # Recalculate totals using the current active filters
        self.total_of_income, self.total_of_outcome = self.controller.get_total_of_transactions(self.filters)

        # Format totals with space as a thousands separator
        formatted_income = f"{self.total_of_income:,.2f}".replace(",", " ")
        formatted_outcome = f"{self.total_of_outcome:,.2f}".replace(",", " ")

        # Update labels with formatted values
        self.income_label.setText(f"Entradas: {formatted_income} DH$")
        self.expense_label.setText(f"Saídas: {formatted_outcome} DH$")

        self.load_collection()
        #clear keyword 
        #self.filters["keyword"] = ""