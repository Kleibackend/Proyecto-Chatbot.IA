import sqlite3

DB_NAME = "pc_gamer.db"

def setup_database():
    """Crea las tablas y puebla la base de datos inicial con datos consistentes."""
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    
    try:
        # 1. Crear tabla de componentes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS componentesPC (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                modelo TEXT NOT NULL UNIQUE,
                precio REAL NOT NULL,
                socket TEXT,
                tipo_ram TEXT,
                potencia_w REAL
            );
        ''')

        # 2. Crear tabla de construcciones (Builds)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS construccionPC (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                estimacion_minima REAL,
                uso_sugerido TEXT, -- Nuevo campo para facilitar búsqueda por contexto
                cpu_id INTEGER NOT NULL,
                gpu_id INTEGER NOT NULL,
                placa_madre_id INTEGER NOT NULL,
                fuente_poder_id INTEGER NOT NULL,
                ram_id INTEGER NOT NULL,
                FOREIGN KEY(cpu_id) REFERENCES componentesPC(id),
                FOREIGN KEY(gpu_id) REFERENCES componentesPC(id),
                FOREIGN KEY(placa_madre_id) REFERENCES componentesPC(id),
                FOREIGN KEY(fuente_poder_id) REFERENCES componentesPC(id),
                FOREIGN KEY(ram_id) REFERENCES componentesPC(id)
            );
        ''')
        
        print("--- Tablas verificadas ---")
        
        # 3. Datos de componentes (Limpios y con datos técnicos completos)
        componentes = [
            # CPU (Socket, RAM Type, Watts)
            ('Cpu', 'Ryzen 9 9950X3D', 800.0, 'AM5', 'DDR5', 120),
            ('Cpu', 'Ryzen 7 9800X3D', 479.0, 'AM5', 'DDR5', 120),
            ('Cpu', 'Ryzen 5 7600X', 250.0, 'AM5', 'DDR5', 105),
            ('Cpu', 'Ryzen 5 5600', 130.0, 'AM4', 'DDR4', 65),
            ('Cpu', 'Core i7-14700K', 400.0, 'LGA1700', 'DDR5', 125),
            ('Cpu', 'Core i5-13400F', 195.0, 'LGA1700', 'DDR4', 65),

            # GPU (Socket=PCIe, RAM=VRAM Type, Watts)
            ('Gpu', 'GeForce RTX 5090', 2000.0, 'PCIe x16', 'GDDR7', 450),
            ('Gpu', 'GeForce RTX 5080', 1100.0, 'PCIe x16', 'GDDR7', 320),
            ('Gpu', 'GeForce RTX 4070', 600.0, 'PCIe x16', 'GDDR6X', 200),
            ('Gpu', 'GeForce RTX 3060', 320.0, 'PCIe x16', 'GDDR6', 170),

            # Placa Madre (Socket CPU, Tipo RAM soportada, Consumo propio aprox)
            ('PlacaMadre', 'Asus ROG Z790', 429.0, 'LGA1700', 'DDR5', 60),
            ('PlacaMadre', 'Asus Prime B760', 150.0, 'LGA1700', 'DDR4', 50), # Agregada para compatibilidad DDR4 Intel
            ('PlacaMadre', 'Asus X670E', 250.0, 'AM5', 'DDR5', 50),
            ('PlacaMadre', 'Gigabyte B650', 180.0, 'AM5', 'DDR5', 40),
            ('PlacaMadre', 'MSI B550', 110.0, 'AM4', 'DDR4', 35),
            
            # Fuente (Socket=Formato, Potencia W Total)
            ('FuentePoder', 'Fuente 850W Gold', 120.0, 'ATX', 'N/A', 850),
            ('FuentePoder', 'Fuente 650W Bronze', 60.0, 'ATX', 'N/A', 650),
            ('FuentePoder', 'Fuente 1000W Platinum', 200.0, 'ATX', 'N/A', 1000),

            # RAM (Socket=DIMM, Tipo RAM, Consumo)
            ('Ram', 'DDR5 32GB 6000MHz', 145.0, 'DIMM', 'DDR5', 5),
            ('Ram', 'DDR4 16GB 3200MHz', 50.0, 'DIMM', 'DDR4', 3),
        ]

        cursor.executemany('''
            INSERT OR IGNORE INTO componentesPC (tipo, modelo, precio, socket, tipo_ram, potencia_w)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', componentes)
        
        print(f"{cursor.rowcount} componentes procesados.")

        # 4. Insertar Builds
        # Helper para obtener ID
        def get_id(modelo):
            cursor.execute("SELECT id FROM componentesPC WHERE modelo = ?", (modelo,))
            res = cursor.fetchone()
            if not res:
                print(f"Advertencia: Componente {modelo} no encontrado.")
                return None
            return res[0]

        builds = [
            ("PC Master Race 4K", 3500.0, "Gaming 4K", 'Ryzen 9 9950X3D', 'GeForce RTX 5090', 'Asus X670E', 'Fuente 1000W Platinum', 'DDR5 32GB 6000MHz'),
            ("PC Gaming Calidad Precio", 900.0, "Gaming 1080p", 'Ryzen 5 5600', 'GeForce RTX 3060', 'MSI B550', 'Fuente 650W Bronze', 'DDR4 16GB 3200MHz'),
            ("Workstation Edición", 2500.0, "Edición", 'Core i7-14700K', 'GeForce RTX 5080', 'Asus ROG Z790', 'Fuente 850W Gold', 'DDR5 32GB 6000MHz')
        ]

        # Limpiamos builds anteriores para evitar duplicados si se corre varias veces
        cursor.execute("DELETE FROM construccionPC") 

        for nombre, est, uso, cpu, gpu, mobo, psu, ram in builds:
            ids = [get_id(x) for x in [cpu, gpu, mobo, psu, ram]]
            if all(ids):
                cursor.execute('''
                    INSERT INTO construccionPC (nombre, estimacion_minima, uso_sugerido, cpu_id, gpu_id, placa_madre_id, fuente_poder_id, ram_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (nombre, est, uso, *ids))
        
        conexion.commit()
        print("Builds insertadas correctamente.")

    except sqlite3.Error as e:
        print(f"Error en la base de datos: {e}")
        conexion.rollback()
    finally:
        conexion.close()

if __name__ == '__main__':
    setup_database()