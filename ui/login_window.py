import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QInputDialog, QTextEdit, QDialog
)
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt, Signal
import qtawesome as qta


class ImprovedLoginDialog(QDialog):
    """Diálogo mejorado para login con instrucciones paso a paso"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Iniciar Sesión - YouTube Music")
        self.setModal(True)
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Título
        title = QLabel("🔐 Autenticación con Cookies")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Instrucciones paso a paso
        instructions = self._create_instructions()
        layout.addWidget(instructions)

        # Área de texto para pegar el cURL
        input_label = QLabel("📋 Pega aquí el comando cURL completo:")
        input_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(input_label)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Pega el comando cURL completo aquí...")
        self.text_input.setMinimumHeight(200)
        self.text_input.setStyleSheet("""
            QTextEdit {
                background: #1a1a1a;
                border: 2px solid #2a2a2a;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
            QTextEdit:focus {
                border-color: #FF0000;
            }
        """)
        layout.addWidget(self.text_input)

        # Botones
        buttons_layout = QHBoxLayout()

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.setFixedHeight(40)
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #2a2a2a;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-weight: bold;
            }
            QPushButton:hover { background: #3a3a3a; }
        """)

        self.login_btn = QPushButton("🔓 Iniciar Sesión")
        self.login_btn.setFixedHeight(40)
        self.login_btn.clicked.connect(self.accept)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: #FF0000;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover { background: #E60000; }
        """)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.login_btn)

        layout.addLayout(buttons_layout)

    def _create_instructions(self):
        """Crear widget con instrucciones detalladas"""
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background: #1a1a1a;
                border-radius: 8px;
                padding: 16px;
            }
        """)

        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        steps = [
            ("1️⃣", "Abre YouTube Music", "Ve a https://music.youtube.com en tu navegador"),
            ("2️⃣", "Inicia Sesión", "Asegúrate de estar logueado con tu cuenta de Google"),
            ("3️⃣", "Abre DevTools", "Presiona F12 o Ctrl+Shift+I (Cmd+Opt+I en Mac)"),
            ("4️⃣", "Ve a la pestaña Network", "Busca la pestaña 'Red' o 'Network' en DevTools"),
            ("5️⃣", "Filtra por 'browse'", "En el campo de filtro, escribe: browse"),
            ("6️⃣", "Haz clic en Biblioteca", "⚠️ Click en 'Biblioteca' o reproduce una canción"),
            ("7️⃣", "Encuentra la petición", "Busca POST a 'youtubei/v1/browse' con status 200"),
            ("8️⃣", "Copia como cURL", "Clic derecho → Copy → Copy as cURL (bash)"),
        ]

        for emoji, title, description in steps:
            step_widget = self._create_step(emoji, title, description)
            layout.addWidget(step_widget)

        # Nota importante
        note = QLabel(
            "⚠️ Las peticiones 'browse' NO aparecen en la página principal.\nHaz clic en 'Biblioteca' o reproduce una canción PRIMERO.")
        note.setStyleSheet("""
            color: #FF9800;
            font-weight: bold;
            padding: 8px;
            background: rgba(255, 152, 0, 0.1);
            border-radius: 4px;
        """)
        note.setWordWrap(True)
        layout.addWidget(note)

        return container

    def _create_step(self, emoji, title, description):
        """Crear widget para un paso individual"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Emoji
        emoji_label = QLabel(emoji)
        emoji_label.setStyleSheet("font-size: 20px;")
        emoji_label.setFixedWidth(30)

        # Texto
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 13px; color: white;")

        desc_label = QLabel(description)
        desc_label.setStyleSheet("font-size: 12px; color: #999;")
        desc_label.setWordWrap(True)

        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)

        layout.addWidget(emoji_label)
        layout.addLayout(text_layout, stretch=1)

        return widget

    def get_curl_text(self):
        """Obtener el texto del cURL ingresado"""
        return self.text_input.toPlainText().strip()


class LoginWindow(QWidget):
    """Ventana de bienvenida mejorada"""

    login_success = Signal()
    login_skipped = Signal()

    def __init__(self, service, app_icon, is_authenticated):
        super().__init__()
        self.service = service
        self.app_icon = app_icon
        self.is_authenticated = is_authenticated
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Bienvenido a YTMusic Client")
        self.setWindowIcon(self.app_icon)
        self.setFixedSize(400, 500)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Icono
        icon_label = QLabel()
        pixmap = self.app_icon.pixmap(128, 128)
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # Título
        title_label = QLabel("YTMusic Minimal Client")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        layout.addWidget(title_label)

        # Créditos
        credits_label = QLabel("by Seiny & Moonshine")
        credits_label.setAlignment(Qt.AlignCenter)
        credits_label.setStyleSheet("font-size: 14px; color: #b3b3b3;")
        layout.addWidget(credits_label)

        # Estado de autenticación
        if self.is_authenticated:
            auth_status = self.service.get_auth_status()
            status_text = auth_status.get('message', 'Sesión activa')

            status_label = QLabel(f"✅ {status_text}")
            status_label.setAlignment(Qt.AlignCenter)
            status_label.setStyleSheet("""
                font-size: 13px; 
                color: #00ff00; 
                background: rgba(0, 255, 0, 0.1);
                padding: 8px;
                border-radius: 6px;
            """)
            layout.addWidget(status_label)

            if auth_status.get('days_since_auth'):
                days = auth_status['days_since_auth']
                info_text = f"Sesión activa ({days} día{'s' if days != 1 else ''})"
                info_label = QLabel(info_text)
                info_label.setAlignment(Qt.AlignCenter)
                info_label.setStyleSheet("font-size: 11px; color: #999;")
                layout.addWidget(info_label)

        layout.addStretch(1)

        # Botón de login
        self.login_button = QPushButton()
        self.login_button.setIcon(qta.icon('fa5s.user-circle', color='white'))

        if self.is_authenticated:
            self.login_button.setText(" Cambiar Cuenta")
            self.login_button.setStyleSheet("""
                QPushButton {
                    background-color: #2a3738; color: white; border: none;
                    padding: 10px; border-radius: 6px; font-weight: bold; font-size: 14px;
                }
                QPushButton:hover { background-color: #3a4748; }
            """)
        else:
            self.login_button.setText(" Iniciar Sesión")
            self.login_button.setStyleSheet("""
                QPushButton {
                    background-color: #FF0000; color: white; border: none;
                    padding: 12px; border-radius: 6px; font-weight: bold; font-size: 16px;
                }
                QPushButton:hover { background-color: #E60000; }
            """)

        self.login_button.clicked.connect(self.start_login)
        layout.addWidget(self.login_button)

        # Botón continuar
        self.skip_button = QPushButton("Continuar" if self.is_authenticated else "Continuar sin sesión")
        self.skip_button.clicked.connect(self.login_skipped.emit)
        self.skip_button.setStyleSheet("""
            QPushButton {
                background-color: #2a3738; color: white; border: none;
                padding: 10px; border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background-color: #3a4748; }
        """)
        layout.addWidget(self.skip_button)

        # Info de persistencia
        if not self.is_authenticated:
            persistence_info = QLabel("💡 Tu sesión se mantendrá activa por semanas")
            persistence_info.setAlignment(Qt.AlignCenter)
            persistence_info.setStyleSheet("font-size: 11px; color: #666; margin-top: 8px;")
            layout.addWidget(persistence_info)

        # Establecer botón por defecto
        if self.is_authenticated:
            self.skip_button.setDefault(True)
        else:
            self.login_button.setDefault(True)

        self.setStyleSheet("background-color: #060d0e;")

    def start_login(self):
        """Iniciar proceso de login con diálogo mejorado"""

        # Si ya está autenticado, preguntar si quiere cambiar
        if self.is_authenticated:
            reply = QMessageBox.question(
                self,
                "Cambiar Cuenta",
                "¿Deseas cerrar la sesión actual e iniciar con otra cuenta?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            self.service.logout()

        # Mostrar diálogo mejorado
        dialog = ImprovedLoginDialog(self)

        if dialog.exec() == QDialog.Accepted:
            curl_text = dialog.get_curl_text()

            if not curl_text:
                QMessageBox.warning(
                    self,
                    "Error",
                    "Por favor pega el comando cURL en el campo de texto."
                )
                return

            # Intentar autenticar
            success = self.service.setup_authentication(curl_text)

            if success:
                self._show_success_message()
                self.login_success.emit()
            else:
                self._show_error_message()

    def _show_success_message(self):
        """Mostrar mensaje de éxito detallado"""
        auth_status = self.service.get_auth_status()

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("¡Éxito!")
        msg.setText("✅ Inicio de sesión completado")
        msg.setInformativeText(
            "Tu sesión se ha guardado de forma segura y permanecerá activa.\n\n"
            "📁 Archivos guardados:\n"
            "  • oauth.json (credenciales principales)\n"
            "  • browser.json (respaldo para recuperación)\n\n"
            "⏰ Duración: Semanas o meses\n"
            "🔄 Auto-recuperación: Activada\n\n"
            f"📊 Estado: {auth_status.get('message', 'Activo')}"
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

    def _show_error_message(self):
        """Mostrar mensaje de error con ayuda"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Error de Autenticación")
        msg.setText("❌ No se pudo completar el inicio de sesión")
        msg.setInformativeText(
            "Posibles causas:\n\n"
            "1. ❌ El comando cURL está incompleto\n"
            "   → Asegúrate de copiar TODO el comando\n\n"
            "2. ❌ No estás en YouTube Music\n"
            "   → Usa music.youtube.com, no youtube.com\n\n"
            "3. ❌ La sesión del navegador expiró\n"
            "   → Cierra sesión y vuelve a iniciar\n\n"
            "4. ❌ Las cookies no son válidas\n"
            "   → Verifica que la petición sea de 'browse'\n\n"
            "💡 Consejo: Intenta en modo incógnito para\n"
            "   evitar conflictos con extensiones."
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()