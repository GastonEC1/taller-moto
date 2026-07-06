import os
import sqlite3

DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_PRIVATE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# ─── PostgreSQL (Render) ──────────────────────────────────────────────────────
if DATABASE_URL:
    import psycopg2
    import psycopg2.extras

    def get_db():
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn

    def init_db():
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nombre TEXT NOT NULL,
                apellido TEXT NOT NULL,
                direccion TEXT,
                telefono TEXT,
                email TEXT,
                dni TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS vehiculos (
                id SERIAL PRIMARY KEY,
                marca TEXT NOT NULL,
                modelo TEXT NOT NULL,
                patente TEXT NOT NULL UNIQUE,
                anio INTEGER,
                motor TEXT,
                vin TEXT,
                color TEXT,
                combustible TEXT,
                cilindrada TEXT,
                tipo_moto TEXT,
                cliente_id INTEGER REFERENCES clientes(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Migración: agregar columnas nuevas solo si no existen
        for col, definition in [('cilindrada', 'TEXT'), ('tipo_moto', 'TEXT')]:
            c.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='vehiculos' AND column_name=%s
            """, (col,))
            if not c.fetchone():
                c.execute(f'ALTER TABLE vehiculos ADD COLUMN {col} {definition}')
        c.execute('''
            CREATE TABLE IF NOT EXISTS ordenes (
                id SERIAL PRIMARY KEY,
                vehiculo_id INTEGER NOT NULL REFERENCES vehiculos(id),
                cliente_id INTEGER NOT NULL REFERENCES clientes(id),
                fecha_ingreso DATE NOT NULL,
                fecha_estimada DATE,
                fecha_egreso DATE,
                kilometros INTEGER,
                receptor_servicio TEXT,
                descripcion_trabajo TEXT,
                diagnostico TEXT,
                repuestos TEXT,
                observaciones TEXT,
                estado TEXT DEFAULT 'abierta',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS presupuestos (
                id SERIAL PRIMARY KEY,
                cliente_id INTEGER NOT NULL REFERENCES clientes(id),
                vehiculo_id INTEGER REFERENCES vehiculos(id),
                fecha DATE NOT NULL,
                valido_hasta DATE,
                descripcion TEXT,
                observaciones TEXT,
                atendido_por TEXT,
                condicion_venta TEXT,
                estado TEXT DEFAULT 'pendiente',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS orden_repuestos (
                id SERIAL PRIMARY KEY,
                orden_id INTEGER NOT NULL REFERENCES ordenes(id),
                descripcion TEXT NOT NULL,
                cantidad REAL DEFAULT 1
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS presupuesto_items (
                id SERIAL PRIMARY KEY,
                presupuesto_id INTEGER NOT NULL REFERENCES presupuestos(id),
                tipo TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                cantidad REAL DEFAULT 1,
                precio_unitario REAL DEFAULT 0,
                en_stock INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

# ─── SQLite (local) ───────────────────────────────────────────────────────────
else:
    _dir = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(_dir, 'taller_motos.db')

    def get_db():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db():
        conn = get_db()
        c = conn.cursor()
        c.executescript('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL, apellido TEXT NOT NULL,
                direccion TEXT, telefono TEXT, email TEXT, dni TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS vehiculos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                marca TEXT NOT NULL, modelo TEXT NOT NULL,
                patente TEXT NOT NULL UNIQUE, anio INTEGER,
                motor TEXT, vin TEXT, color TEXT, combustible TEXT,
                cilindrada TEXT, tipo_moto TEXT,
                cliente_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            );
            CREATE TABLE IF NOT EXISTS ordenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehiculo_id INTEGER NOT NULL, cliente_id INTEGER NOT NULL,
                fecha_ingreso DATE NOT NULL, fecha_estimada DATE, fecha_egreso DATE,
                kilometros INTEGER, receptor_servicio TEXT,
                descripcion_trabajo TEXT, diagnostico TEXT, repuestos TEXT,
                observaciones TEXT, estado TEXT DEFAULT 'abierta',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id),
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            );
            CREATE TABLE IF NOT EXISTS presupuestos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL, vehiculo_id INTEGER,
                fecha DATE NOT NULL, valido_hasta DATE,
                descripcion TEXT, observaciones TEXT,
                atendido_por TEXT, condicion_venta TEXT,
                estado TEXT DEFAULT 'pendiente',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id)
            );
            CREATE TABLE IF NOT EXISTS orden_repuestos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orden_id INTEGER NOT NULL,
                descripcion TEXT NOT NULL,
                cantidad REAL DEFAULT 1,
                FOREIGN KEY (orden_id) REFERENCES ordenes(id)
            );
            CREATE TABLE IF NOT EXISTS presupuesto_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                presupuesto_id INTEGER NOT NULL, tipo TEXT NOT NULL,
                descripcion TEXT NOT NULL, cantidad REAL DEFAULT 1,
                precio_unitario REAL DEFAULT 0, en_stock INTEGER DEFAULT 0,
                FOREIGN KEY (presupuesto_id) REFERENCES presupuestos(id)
            );
        ''')
        # Migración: agregar columnas nuevas si no existen (para DB existentes)
        for col in ('cilindrada', 'tipo_moto'):
            try:
                c.execute(f'ALTER TABLE vehiculos ADD COLUMN {col} TEXT')
            except Exception:
                pass
        conn.commit()
        conn.close()
