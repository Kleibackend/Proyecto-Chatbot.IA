import spacy
import sqlite3
import re
from typing import Dict, Optional, Tuple, Any

# Configuración
DB_NAME = "pc_gamer.db"

# Cargar modelo de Spacy
try:
    nlp = spacy.load("es_core_news_sm")
except OSError:
    print("Error: Modelo de Spacy no encontrado. Ejecuta: python -m spacy download es_core_news_sm")
    exit()

def obtener_conexion():
    """Retorna una conexión a la base de datos."""
    return sqlite3.connect(DB_NAME)

def analisis_pregunta(pregunta: str) -> Dict[str, Any]:
    """
    Analiza la intención del usuario. Detecta componentes, modelos específicos,
    intenciones de upgrade y casos de uso.
    """
    doc = nlp(pregunta.lower())
    
    requerimientos = {
        "tipo_componente_buscado": None, # Qué quiere el usuario
        "modelos_mencionados": [],       # Qué tiene el usuario (para compatibilidad)
        "uso": None,                     # Gaming, Edición, etc.
        "intencion_upgrade": False       # Si usa palabras como "mejorar", "upgrade"
    }

    # 1. Palabras clave de intención
    if any(token.text in ["mejorar", "upgrade", "actualizar", "potenciar"] for token in doc):
        requerimientos["intencion_upgrade"] = True

    # 2. Detección de Componentes
    for token in doc:
        txt = token.text.lower()
        if txt in ["cpu", "procesador"]:
            requerimientos["tipo_componente_buscado"] = 'Cpu'
        elif txt in ["gpu", "grafica", "gráfica", "video"]:
            requerimientos["tipo_componente_buscado"] = 'Gpu'
        elif txt in ["ram", "memoria"]:
            requerimientos["tipo_componente_buscado"] = 'Ram'
        elif txt in ["placa", "motherboard", "madre"]:
            requerimientos["tipo_componente_buscado"] = "PlacaMadre"
        elif txt in ["fuente", "psu"]:
            requerimientos["tipo_componente_buscado"] = "FuentePoder"
        
        # Detección de uso
        if txt in ["gaming", "jugar"]:
            requerimientos["uso"] = 'Gaming 1080p' # Default
        elif txt in ["edicion", "edición", "diseño", "render", "trabajo"]:
            requerimientos["uso"] = "Edición"

    if "4k" in pregunta.lower():
        requerimientos["uso"] = "Gaming 4K"

    # 3. Extracción de Modelos (Regex + Spacy Entities)
    # Detectamos cualquier modelo mencionado (puede haber más de uno, ej: CPU y GPU para calcular PSU)
    patron_modelo = r'\b(ryzen|core|i\d|rtx|geforce|radeon|gtx)\s*[\d]+[a-z0-9]*(-[a-z0-9]+)?\b'
    coincidencias = re.finditer(patron_modelo, pregunta.lower())
    
    for match in coincidencias:
        modelo_raw = match.group(0)
        # Limpieza básica
        requerimientos["modelos_mencionados"].append(modelo_raw.strip())

    return requerimientos

def obtener_datos_componente(cursor: sqlite3.Cursor, modelo_parcial: str) -> Optional[Tuple]:
    """Busca un componente y devuelve todos sus datos técnicos."""
    sql = """SELECT id, tipo, modelo, precio, socket, tipo_ram, potencia_w 
             FROM componentesPC WHERE modelo LIKE ? LIMIT 1"""
    cursor.execute(sql, (f'%{modelo_parcial}%',))
    return cursor.fetchone()

def recomendar_componente_por_contexto(cursor: sqlite3.Cursor, tipo_comp: str, uso: str) -> str:
    """
    Mejora Lógica Builds: Sugiere un componente individual basado en el uso,
    extrayéndolo de una Build probada.
    """
    columna_map = {
        'Cpu': 'cpu_id', 'Gpu': 'gpu_id', 'PlacaMadre': 'placa_madre_id',
        'Ram': 'ram_id', 'FuentePoder': 'fuente_poder_id'
    }
    
    if tipo_comp not in columna_map:
        return "Lo siento, no puedo recomendar ese tipo de componente por contexto."

    # Buscamos una build que coincida con el uso sugerido (usando LIKE para flexibilidad)
    sql_build = f"""
        SELECT c.modelo, c.precio 
        FROM construccionPC b
        JOIN componentesPC c ON b.{columna_map[tipo_comp]} = c.id
        WHERE b.uso_sugerido LIKE ? OR b.nombre LIKE ?
        LIMIT 1
    """
    param = f'%{uso}%'
    cursor.execute(sql_build, (param, param))
    res = cursor.fetchone()
    
    if res:
        return f"Para uso de {uso}, te recomiendo: {res[0]} (${res[1]:.2f}), usado en nuestros ensambles especializados."
    return f"No encontré una recomendación específica de {tipo_comp} para {uso}."

def calcular_psu_requerida(cursor: sqlite3.Cursor, modelos: list) -> str:
    """
    Mejora PSU: Calcula potencia basada en CPU + GPU + Margen.
    """
    potencia_total = 0
    componentes_encontrados = []
    
    for mod in modelos:
        datos = obtener_datos_componente(cursor, mod)
        if datos:
            # datos[6] es potencia_w
            potencia_total += datos[6]
            componentes_encontrados.append(f"{datos[2]} ({datos[6]}W)")
    
    if potencia_total == 0:
        return "Necesito saber qué CPU y GPU tienes para calcular la fuente (ej: 'Fuente para Ryzen 5600 y RTX 3060')."

    # Margen de seguridad estricto (150W - 200W)
    margen = 200
    meta_w = potencia_total + margen
    
    cursor.execute("SELECT modelo, precio, potencia_w FROM componentesPC WHERE tipo='FuentePoder' AND potencia_w >= ? ORDER BY precio ASC LIMIT 1", (meta_w,))
    psu = cursor.fetchone()
    
    info_consumo = " + ".join(componentes_encontrados)
    if psu:
        return f"Consumo estimado: {potencia_total}W ({info_consumo}). Con margen de seguridad ({margen}W), necesitas ~{meta_w}W. Te recomiendo: {psu[0]} (${psu[1]:.2f})."
    else:
        return f"Consumo estimado alto ({potencia_total}W). Busca una fuente de más de {meta_w}W."

def logica_upgrade_o_compatibilidad(cursor: sqlite3.Cursor, reqs: Dict) -> str:
    """
    Maneja la lógica compleja de compatibilidad estricta y upgrades.
    """
    modelos = reqs["modelos_mencionados"]
    tipo_buscado = reqs["tipo_componente_buscado"]
    es_upgrade = reqs["intencion_upgrade"]

    if not modelos:
        return "Por favor, especifica el modelo que tienes (ej: 'Ryzen 5 5600') para verificar compatibilidad."

    # Tomamos el primer modelo mencionado como referencia principal
    datos_actual = obtener_datos_componente(cursor, modelos[0])
    if not datos_actual:
        return f"No encontré el componente '{modelos[0]}' en mi base de datos."

    tipo_actual = datos_actual[1]  # Cpu, Gpu, etc
    socket_actual = datos_actual[4]
    ram_actual = datos_actual[5]
    potencia_actual = datos_actual[6]
    precio_actual = datos_actual[3]

    # --- CASO A: UPGRADE (Mejorar el MISMO componente) ---
    if es_upgrade or (tipo_buscado and tipo_buscado == tipo_actual):
        # Filtro: Debe ser compatible (mismo socket/tipo) Y ser "significativamente mejor"
        # Definimos "mejor" como: Precio > 20% más alto O Potencia > 20% más alta (indicativo de rendimiento en este contexto simplificado)
        
        sql = """SELECT modelo, precio, potencia_w FROM componentesPC 
                 WHERE tipo = ? AND socket = ? AND (precio > ? OR potencia_w > ?)
                 ORDER BY precio DESC LIMIT 1"""
        
        # Solo aplicamos filtro de socket si es CPU o Placa. Para GPU/RAM el socket es estándar, pero verificamos tipo de RAM si aplica.
        params = [tipo_actual, socket_actual, precio_actual * 1.2, potencia_actual * 1.2]
        
        # Ajuste para RAM: debe coincidir el tipo_ram (DDR4/DDR5)
        if tipo_actual == 'Ram':
            sql = """SELECT modelo, precio FROM componentesPC 
                     WHERE tipo = 'Ram' AND tipo_ram = ? AND precio > ? 
                     ORDER BY precio DESC LIMIT 1"""
            params = [ram_actual, precio_actual * 1.2]

        cursor.execute(sql, params)
        res = cursor.fetchone()
        
        if res:
            return f"🚀 Upgrade sugerido: Tu {datos_actual[2]} puede mejorarse con el {res[0]} (${res[1]}). Es una mejora significativa."
        else:
            return f"Tu {datos_actual[2]} ya es tope de gama para su plataforma en mi base de datos o no tengo una mejora significativa registrada."

    # --- CASO B: COMPATIBILIDAD CRUZADA (Buscar pareja) ---
    # 1. Tengo CPU -> Busco Placa Madre
    if tipo_actual == 'Cpu' and (not tipo_buscado or tipo_buscado == 'PlacaMadre'):
        # Estricto: Mismo Socket Y compatible con la RAM si la especificó (o general)
        sql = "SELECT modelo, precio FROM componentesPC WHERE tipo='PlacaMadre' AND socket=? AND tipo_ram=? LIMIT 1"
        cursor.execute(sql, (socket_actual, ram_actual)) # La CPU define qué RAM usa, la placa debe coincidir
        res = cursor.fetchone()
        if res:
            return f"Para el procesador {datos_actual[2]} (Socket {socket_actual}/{ram_actual}), la placa ideal es {res[0]} (${res[1]})."

    # 2. Tengo Placa Madre -> Busco CPU o RAM
    elif tipo_actual == 'PlacaMadre':
        if tipo_buscado == 'Ram':
            sql = "SELECT modelo, precio FROM componentesPC WHERE tipo='Ram' AND tipo_ram=? LIMIT 1"
            cursor.execute(sql, (ram_actual,))
            res = cursor.fetchone()
            if res:
                return f"Tu placa usa {ram_actual}. Te recomiendo: **{res[0]}**."
        else: # Default: Buscar CPU
            sql = "SELECT modelo, precio FROM componentesPC WHERE tipo='Cpu' AND socket=? AND tipo_ram=? LIMIT 1"
            cursor.execute(sql, (socket_actual, ram_actual))
            res = cursor.fetchone()
            if res:
                return f"Para la placa {datos_actual[2]}, el procesador compatible es **{res[0]}** ({ram_actual})."

    return "No estoy seguro de qué componente compatible buscas. Prueba especificando: 'Placa para Ryzen 5600'."

def generar_respuesta(pregunta: str) -> str:
    """Orquestador principal de la lógica."""
    try:
        with obtener_conexion() as conexion:
            cursor = conexion.cursor()
            reqs = analisis_pregunta(pregunta)
            
            tipo = reqs["tipo_componente_buscado"]
            uso = reqs["uso"]
            modelos = reqs["modelos_mencionados"]
            
            # Prioridad 1: Pregunta sobre Fuente de Poder con componentes específicos
            if tipo == 'FuentePoder' and len(modelos) >= 1:
                return calcular_psu_requerida(cursor, modelos)

            # Prioridad 2: Pregunta por Upgrade o Compatibilidad (menciona modelo)
            if modelos:
                return logica_upgrade_o_compatibilidad(cursor, reqs)

            # Prioridad 3: Pregunta Contextual (Componente + Uso)
            # Ej: "Qué GPU me sirve para Edición"
            if tipo and uso:
                return recomendar_componente_por_contexto(cursor, tipo, uso)

            # Prioridad 4: Recomendación de Build Completa (Solo uso)
            if uso:
                sql = "SELECT nombre, estimacion_minima FROM construccionPC WHERE uso_sugerido = ? OR nombre LIKE ? LIMIT 1"
                cursor.execute(sql, (uso, f'%{uso}%'))
                res = cursor.fetchone()
                if res:
                    return f"Para '{uso}', te recomiendo el ensamble completo: {res[0]} (~${res[1]:.2f})."
                return "No tengo un ensamble específico para ese uso, pero el 'PC Gaming Calidad Precio' suele funcionar bien."

            return "Hola. ¿En qué te ayudo? Puedes preguntar: 'Mejora para Ryzen 5600', 'GPU para Edición' o 'Fuente para RTX 3060 y Ryzen 5600'."

    except sqlite3.Error as e:
        return f"Error interno de base de datos: {e}"

if __name__ == '__main__':
    print("🔧 BOT HARDWARE v2.0 INICIADO")
    while True:
        try:
            user_input = input("\nTu: ")
            if user_input.lower() in ['salir', 'exit']:
                break
            print(f"Bot: {generar_respuesta(user_input)}")
        except KeyboardInterrupt:
            break