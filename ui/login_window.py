# ui/login_window.py

import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QInputDialog
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal
import qtawesome as qta


class LoginWindow(QWidget):
    """
    Una nueva ventana de bienvenida que se muestra al inicio.
    Permite al usuario iniciar sesión o continuar como invitado.
    """

    # Señales para avisar a app.py la decisión del usuario
    login_success = Signal()
    login_skipped = Signal()

    def __init__(self, service, app_icon, is_authenticated):  # <--- CAMBIO AQUÍ
        super().__init__()
        self.service = service
        self.app_icon = app_icon
        self.is_authenticated = is_authenticated  # <--- CAMBIO AQUÍ
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Bienvenido a YTMusic Client")
        self.setWindowIcon(self.app_icon)
        self.setFixedSize(400, 450)  # Tamaño fijo para la ventana de login

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # 1. Icono/Logo
        icon_label = QLabel()
        pixmap = self.app_icon.pixmap(128, 128)
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # 2. Título
        title_label = QLabel("YTMusic Minimal Client")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        layout.addWidget(title_label)

        # 3. Créditos
        credits_label = QLabel("by RainySen & Moonshine")
        credits_label.setAlignment(Qt.AlignCenter)
        credits_label.setStyleSheet("font-size: 14px; color: #b3b3b3;")
        layout.addWidget(credits_label)

        layout.addStretch(1)  # Espaciador

        # 4. Botón de Iniciar Sesión
        self.login_button = QPushButton()
        self.login_button.setIcon(qta.icon('fa5s.user-circle', color='white'))
        self.login_button.setText(" Iniciar Sesión")
        self.login_button.clicked.connect(self.start_login)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #03adb7; color: white; border: none;
                padding: 12px; border-radius: 6px; font-weight: bold; font-size: 16px;
            }
            QPushButton:hover { background-color: #00dfe5; }
        """)
        layout.addWidget(self.login_button)

        # 5. Botón de Continuar (Saltar)
        self.skip_button = QPushButton("Continuar sin sesión")
        self.skip_button.clicked.connect(self.login_skipped.emit)
        self.skip_button.setStyleSheet("""
            QPushButton {
                background-color: #2a3738; color: white; border: none;
                padding: 10px; border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background-color: #3a4748; }
        """)
        layout.addWidget(self.skip_button)

        # --- INICIO DE LA NUEVA LÓGICA ---
        # Revisa si el usuario ya está autenticado
        if self.is_authenticated:
            self.login_button.hide()  # Oculta el botón de "Iniciar Sesión"
            self.skip_button.setText("Continuar")  # Cambia el texto del botón
            self.skip_button.setDefault(True)  # Hace que 'Enter' presione este botón
        else:
            self.login_button.setDefault(True)
        # --- FIN DE LA NUEVA LÓGICA ---

        # Estilo de la ventana
        self.setStyleSheet("background-color: #060d0e;")

    def start_login(self):
        """
        Muestra el diálogo para obtener las cabeceras e intenta autenticarse.
        """
        headers_raw = self.get_login_headers()
        if headers_raw:
            # Llama al servicio para intentar el login
            success = self.service.setup_authentication(headers_raw)

            if success:
                QMessageBox.information(self, "Éxito", "¡Inicio de sesión completado!")
                self.login_success.emit()  # Avisa a app.py que el login fue exitoso
            else:
                QMessageBox.warning(self, "Error",
                                    "No se pudo completar el inicio de sesión. Por favor, verifica las cabeceras e inténtalo de nuevo.")
        # Si el usuario cancela, simplemente no hace nada y se queda en esta ventana.

    def get_login_headers(self):
        """
        Muestra el QInputDialog con las instrucciones.
        """
        instructions = """
            Para iniciar sesión, sigue estos pasos con atención:

            1. Abre YouTube Music en tu navegador (Chrome, Firefox, Opera).
            2. **IMPORTANTE: Asegúrate de haber iniciado sesión con tu cuenta.**
            3. Abre las herramientas de desarrollador (con F12).
            4. Ve a la pestaña "Red" (o "Network").
            5. **IMPORTANTE: Haz una recarga forzada de la página (Ctrl + Shift + R)** para evitar la caché.
            6. En el filtro, escribe `browse` para encontrar la petición correcta.
            7. Busca la petición a `music.youtube.com/youtubei...`, haz clic derecho sobre ella.
            8. Ve a "Copiar" -> "Copiar como cURL (bash)".
            9. Pega el texto completo en el campo de abajo.
        """
        text, ok = QInputDialog.getMultiLineText(self, 'Iniciar Sesión - Obtener Credenciales', instructions, text="")

        if ok and text:
            # Esta es la misma lógica de parseo que ya tenías
            unwrapped_text = re.sub(r'[\^\\]\s*\n', ' ', text)
            unwrapped_text = unwrapped_text.replace('\n', ' ')
            headers_list = []

            h_matches = re.findall(r"-H\s+(['\"])(.*?)\1", unwrapped_text)
            if h_matches:
                headers_list.extend([match[1] for match in h_matches])

            cookie_match = re.search(r"(--cookie|-b)\s+(['\"])(.*?)\2", unwrapped_text)
            if cookie_match:
                cookie_data = cookie_match.group(3)
                headers_list.append(f"Cookie: {cookie_data}")

            return "\n".join(headers_list)
        return None