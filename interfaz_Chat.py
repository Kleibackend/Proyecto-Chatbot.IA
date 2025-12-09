import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import PLN_Chatbot as backend  # Importamos tu archivo de lógica

class PCGamerBotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Hardware Assistant - RTX 5000 Ready")
        self.root.geometry("700x800")
        
        # --- Configuración de Estilos y Colores (Tema Dark Gamer) ---
        self.color_bg = "#121212"        # Fondo casi negro
        self.color_chat = "#1e1e1e"      # Fondo del chat
        self.color_user = "#3b8ed0"      # Azul para el usuario
        self.color_bot = "#00e676"       # Verde neón para el bot
        self.color_text = "#e0e0e0"      # Texto claro
        self.color_accent = "#6200ea"    # Morado para botones/bordes
        
        self.root.configure(bg=self.color_bg)
        
        # --- Inicialización de la Interfaz ---
        self._crear_encabezado()
        self._crear_area_chat()
        self._crear_area_entrada()
        
        # Mensaje de bienvenida
        self._mostrar_mensaje("Bot", "¡Sistema iniciado! 🚀\nPregúntame por builds con la RTX 5090, upgrades para AM5 o edición de video.", "bot")

    def _crear_encabezado(self):
        """Crea la barra superior"""
        header_frame = tk.Frame(self.root, bg="#1f1f1f", height=60)
        header_frame.pack(fill="x", side="top")
        
        lbl_title = tk.Label(
            header_frame, 
            text="🔧 PC BUILDER AI", 
            font=("Segoe UI", 16, "bold"), 
            bg="#1f1f1f", 
            fg=self.color_bot
        )
        lbl_title.pack(pady=15)

    def _crear_area_chat(self):
        """Crea el área scrolleable donde aparecen los mensajes"""
        frame_chat = tk.Frame(self.root, bg=self.color_bg)
        frame_chat.pack(fill="both", expand=True, padx=15, pady=10)

        self.chat_display = scrolledtext.ScrolledText(
            frame_chat, 
            wrap=tk.WORD, 
            bg=self.color_chat, 
            fg=self.color_text,
            font=("Consolas", 11), # Fuente monoespaciada para datos técnicos
            bd=0,
            padx=15,
            pady=15,
            state="disabled" # Para que el usuario no pueda borrar el historial
        )
        self.chat_display.pack(fill="both", expand=True)

        # Configuración de etiquetas para colores
        self.chat_display.tag_config("usuario", foreground=self.color_user, justify="right")
        self.chat_display.tag_config("bot", foreground=self.color_bot, justify="left")
        self.chat_display.tag_config("error", foreground="#ff5252", justify="left")
        self.chat_display.tag_config("separator", foreground="#333333", justify="center")

    def _crear_area_entrada(self):
        """Crea el campo de texto y el botón de enviar"""
        frame_input = tk.Frame(self.root, bg=self.color_bg)
        frame_input.pack(fill="x", padx=15, pady=(0, 20))

        self.entry_msg = tk.Entry(
            frame_input, 
            bg="#2c2c2c", 
            fg="white", 
            font=("Segoe UI", 12), 
            relief=tk.FLAT,
            insertbackground="white" # Color del cursor
        )
        self.entry_msg.pack(side=tk.LEFT, fill="both", expand=True, padx=(0, 10), ipady=10)
        self.entry_msg.bind("<Return>", self.enviar_mensaje) # Enviar con Enter

        btn_send = tk.Button(
            frame_input, 
            text="ENVIAR", 
            command=self.enviar_mensaje,
            bg=self.color_accent, 
            fg="white", 
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            activebackground="#7c43bd",
            activeforeground="white",
            padx=20,
            cursor="hand2"
        )
        btn_send.pack(side=tk.RIGHT)

    def _mostrar_mensaje(self, remitente, texto, tag):
        """Imprime el mensaje en el chat con el estilo adecuado"""
        self.chat_display.config(state="normal")
        
        if remitente == "Bot":
            self.chat_display.insert(tk.END, f"\n🤖 {texto}\n", tag)
            self.chat_display.insert(tk.END, "-"*40 + "\n", "separator")
        else:
            self.chat_display.insert(tk.END, f"\n{texto} 👤\n", tag)

        self.chat_display.see(tk.END) # Auto-scroll al final
        self.chat_display.config(state="disabled")

    def enviar_mensaje(self, event=None):
        pregunta = self.entry_msg.get().strip()
        if not pregunta:
            return

        # 1. Mostrar mensaje del usuario
        self.entry_msg.delete(0, tk.END)
        self._mostrar_mensaje("Tú", pregunta, "usuario")

        # 2. Procesar respuesta (Usamos after para dar sensación de fluidez)
        self.root.after(100, lambda: self._procesar_logica(pregunta))

    def _procesar_logica(self, pregunta):
        try:
            # Llamamos a tu archivo chatbot_logic.py
            respuesta = backend.generar_respuesta(pregunta)
            self._mostrar_mensaje("Bot", respuesta, "bot")
        except Exception as e:
            error_msg = f"Error al conectar con el cerebro del bot: {str(e)}"
            self._mostrar_mensaje("Sistema", error_msg, "error")

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = PCGamerBotApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Error crítico al iniciar la interfaz: {e}")