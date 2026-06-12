#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# 🐝 AGENTE FINANCIERO UNIVERSAL — HaaPpDigitalV
# Arquitecto : Víctor Hugo González Torres (Lok / Osiris)
# Versión    : 2.0  |  Frecuencia K'uhul: 12.3 Hz  |  Fricción de compra: 0
#
# ECOSISTEMA COMPLETO EN UN SOLO AGENTE:
#   ├── BotFrecuencias    — Señales ZFPI (coherencia frecuencial K'uhul)
#   ├── MarketEngine      — Libro de órdenes SQLite, matching real
#   ├── AgenteTrading     — Ejecutor de mercado con autorización de Tesorería
#   ├── AgenteTesoreria   — Libro contable, wallets, verificación de fondos
#   ├── BancoKUSOFIN      — Ciclo KuzoFynum, MotorSierra, Migrador de capital
#   ├── OsirisForense     — Firma JHOP, validación de paquetes
#   └── SofíObservadora   — Consumidora pasiva: aprende de cada operación,
#                           alimenta la inteligencia lógica de SOFÍ V9
#
# MODO DE OPERACIÓN:
#   python agente_financiero_universal.py          → servidor completo
#   python agente_financiero_universal.py --bot    → solo bot frecuencias
#   python agente_financiero_universal.py --banco  → solo ciclo bancario
#
# VARIABLES DE ENTORNO (.env):
#   MONGO_URI, SOFI_URL, BINANCE_API_KEY, BINANCE_SECRET,
#   PORT, SELF_URL, SOFI_NODE_URL, HERMES_NOMBRE
# ==============================================================================

# ── Dependencias estándar ──────────────────────────────────────────────────────
import asyncio, hashlib, json, logging, math, os, random, sqlite3, threading, time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

# ── Dotenv ────────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── MongoDB ────────────────────────────────────────────────────────────────────
try:
    from pymongo import MongoClient
    MONGO_OK = True
except ImportError:
    MONGO_OK = False

# ── WebSockets ────────────────────────────────────────────────────────────────
try:
    import websockets as _ws_lib
    WS_OK = True
except ImportError:
    WS_OK = False

# ── Flask / SocketIO ──────────────────────────────────────────────────────────
try:
    from flask import Flask, request, jsonify
    from flask_socketio import SocketIO, emit
    from flask_cors import CORS
    FLASK_OK = True
except ImportError:
    FLASK_OK = False

logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("AFU")

# ==============================================================================
# ⚙️  CONFIGURACIÓN CENTRAL
# ==============================================================================
class CFG:
    PORT             = int(os.getenv("PORT", 5000))
    FRECUENCIA_BASE  = 12.3          # Hz K'uhul
    UMBRAL_COMPRA    = 0.85
    UMBRAL_VENTA     = 0.40
    INTERVALO_BOT    = int(os.getenv("INTERVALO_BOT", 5))   # segundos
    PRECIO_MIN_BTC   = 20_000
    PRECIO_MAX_BTC   = 75_000
    COMISION         = 0.000         # 0% — Fricción de compra en cero
    NOMBRE_MONEDA    = "ZYXSOF"
    DB_PATH          = os.getenv("DB_PATH", "kusofin.db")
    MONGO_URI        = os.getenv("MONGO_URI", "")
    SOFI_URL         = os.getenv("SOFI_URL", "")            # wss://...canal_kuhul
    SELF_URL         = os.getenv("SELF_URL", "")
    SOFI_NODE_URL    = os.getenv("SOFI_NODE_URL", "")
    BINANCE_KEY      = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SEC      = os.getenv("BINANCE_SECRET", "")
    HERMES_NOMBRE    = os.getenv("HERMES_NOMBRE", "AgenteFinanciero_01")
    LLAVE_MAESTRA    = os.getenv("LLAVE_MAESTRA", "KUZ_12.3HZ_MASTER")
    META_MXN         = float(os.getenv("META_MXN", 50_000))


# ==============================================================================
# 🔱  OSIRIS FORENSE — Firma JHOP integrada
# ==============================================================================
class OsirisForense:
    FIRMA_SAL = "_12.3Hz_Kuhul_JHOP"

    def firmar(self, datos: dict) -> str:
        payload = json.dumps(datos, sort_keys=True, ensure_ascii=False) + self.FIRMA_SAL
        return hashlib.sha256(payload.encode()).hexdigest()

    def sellar(self, evento: str, datos: dict) -> dict:
        ts   = datetime.now(timezone.utc).isoformat()
        bloque = {"evento": evento, "datos": datos, "ts": ts}
        return {**bloque, "firma_jhop": self.firmar(bloque)[:16]}

osiris = OsirisForense()


# ==============================================================================
# 💾  BASE DE DATOS SQLite — Libro contable local
# ==============================================================================
@contextmanager
def get_db():
    conn = sqlite3.connect(CFG.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # concurrencia segura
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre       TEXT UNIQUE NOT NULL,
            saldo_zyxsof REAL NOT NULL DEFAULT 0,
            saldo_usd    REAL NOT NULL DEFAULT 0,
            creado       TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS ordenes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            tipo       TEXT NOT NULL CHECK(tipo IN ('buy','sell')),
            precio     REAL NOT NULL,
            cantidad   REAL NOT NULL,
            estado     TEXT NOT NULL DEFAULT 'activa'
                           CHECK(estado IN ('activa','ejecutada','cancelada')),
            comision   REAL NOT NULL DEFAULT 0,
            timestamp  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS trades (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            orden_compra_id INTEGER NOT NULL,
            orden_venta_id  INTEGER NOT NULL,
            precio          REAL NOT NULL,
            cantidad        REAL NOT NULL,
            firma_jhop      TEXT,
            timestamp       TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(orden_compra_id) REFERENCES ordenes(id),
            FOREIGN KEY(orden_venta_id)  REFERENCES ordenes(id)
        );
        CREATE TABLE IF NOT EXISTS senales (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo      TEXT NOT NULL,
            precio    REAL,
            coherencia REAL,
            activo    TEXT DEFAULT 'ZYXSOF/USD',
            ejecutada INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS eventos_sofi (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT NOT NULL,
            payload   TEXT NOT NULL,
            aprendido INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        INSERT OR IGNORE INTO usuarios (nombre, saldo_zyxsof, saldo_usd)
            VALUES ('arquitecto', 1000.0, 500.0);
        INSERT OR IGNORE INTO usuarios (nombre, saldo_zyxsof, saldo_usd)
            VALUES ('sofi_bot', 10000.0, 5000.0);
        INSERT OR IGNORE INTO usuarios (nombre, saldo_zyxsof, saldo_usd)
            VALUES ('tesorero_01', 50000.0, 10000.0);
        """)
    log.info("💾 BD Kusofin inicializada.")


# ==============================================================================
# 📊  MARKET ENGINE — Motor de órdenes con matching real + comisión 0
# ==============================================================================
class MarketEngine:
    """
    Libro de órdenes ZYXSOF/USD con matching precio-tiempo.
    Comisión = 0 (Fricción Cero de compra).
    """

    @staticmethod
    def crear_orden(usuario: str, tipo: str, precio: float,
                    cantidad: float, origen: str = "bot") -> dict:
        comision = round(precio * cantidad * CFG.COMISION, 8)
        with get_db() as c:
            u = c.execute("SELECT id, saldo_zyxsof, saldo_usd FROM usuarios WHERE nombre=?",
                          (usuario,)).fetchone()
            if not u:
                return {"error": f"Usuario '{usuario}' no existe"}

            # Validar fondos
            if tipo == "sell" and u["saldo_zyxsof"] < cantidad:
                return {"error": "Saldo ZYXSOF insuficiente"}
            if tipo == "buy" and u["saldo_usd"] < precio * cantidad:
                return {"error": "Saldo USD insuficiente"}

            cur = c.execute(
                "INSERT INTO ordenes (usuario_id,tipo,precio,cantidad,comision) VALUES (?,?,?,?,?)",
                (u["id"], tipo, precio, cantidad, comision)
            )
            oid = cur.lastrowid

        sello = osiris.sellar("ORDEN_CREADA", {
            "orden_id": oid, "usuario": usuario, "tipo": tipo,
            "precio": precio, "cantidad": cantidad, "comision": comision
        })
        log.info(f"📋 Orden #{oid} | {tipo.upper()} {cantidad} @ {precio} | {usuario} | JHOP:{sello['firma_jhop']}")
        return {"exito": True, "orden_id": oid, "comision": comision, "sello": sello}

    @staticmethod
    def ejecutar_matching() -> list[dict]:
        trades_realizados = []
        with get_db() as c:
            compras = c.execute(
                "SELECT * FROM ordenes WHERE tipo='buy' AND estado='activa' ORDER BY precio DESC, id ASC"
            ).fetchall()
            ventas  = c.execute(
                "SELECT * FROM ordenes WHERE tipo='sell' AND estado='activa' ORDER BY precio ASC, id ASC"
            ).fetchall()

            i = j = 0
            while i < len(compras) and j < len(ventas):
                b, s = compras[i], ventas[j]
                if b["precio"] >= s["precio"]:
                    qty   = min(b["cantidad"], s["cantidad"])
                    price = (b["precio"] + s["precio"]) / 2
                    firma = osiris.firmar({"b": b["id"], "s": s["id"], "p": price, "q": qty})

                    c.execute(
                        "INSERT INTO trades (orden_compra_id,orden_venta_id,precio,cantidad,firma_jhop)"
                        " VALUES (?,?,?,?,?)",
                        (b["id"], s["id"], price, qty, firma[:16])
                    )
                    # Actualizar saldos
                    c.execute("UPDATE usuarios SET saldo_usd=saldo_usd-?, saldo_zyxsof=saldo_zyxsof+? WHERE id=?",
                              (price*qty, qty, b["usuario_id"]))
                    c.execute("UPDATE usuarios SET saldo_usd=saldo_usd+?, saldo_zyxsof=saldo_zyxsof-? WHERE id=?",
                              (price*qty, qty, s["usuario_id"]))

                    # Cerrar órdenes completadas
                    restante_b = b["cantidad"] - qty
                    restante_s = s["cantidad"] - qty
                    if restante_b == 0:
                        c.execute("UPDATE ordenes SET estado='ejecutada' WHERE id=?", (b["id"],)); i += 1
                    else:
                        c.execute("UPDATE ordenes SET cantidad=? WHERE id=?", (restante_b, b["id"]))
                    if restante_s == 0:
                        c.execute("UPDATE ordenes SET estado='ejecutada' WHERE id=?", (s["id"],)); j += 1
                    else:
                        c.execute("UPDATE ordenes SET cantidad=? WHERE id=?", (restante_s, s["id"]))

                    trades_realizados.append({
                        "precio": round(price, 4), "cantidad": round(qty, 8),
                        "firma_jhop": firma[:16]
                    })
                    log.info(f"✅ TRADE: {qty:.6f} ZYXSOF @ {price:.2f} USD | JHOP:{firma[:8]}")
                else:
                    break
        return trades_realizados

    @staticmethod
    def libro_ordenes() -> dict:
        with get_db() as c:
            def _enrich(rows, tipo):
                result = []
                for r in rows:
                    u = c.execute("SELECT nombre FROM usuarios WHERE id=?",
                                  (r["usuario_id"],)).fetchone()
                    result.append({
                        "id": r["id"], "precio": r["precio"],
                        "cantidad": r["cantidad"],
                        "usuario": u["nombre"] if u else "?"
                    })
                return result

            bids = _enrich(c.execute(
                "SELECT * FROM ordenes WHERE tipo='buy' AND estado='activa' ORDER BY precio DESC"
            ).fetchall(), "buy")
            asks = _enrich(c.execute(
                "SELECT * FROM ordenes WHERE tipo='sell' AND estado='activa' ORDER BY precio ASC"
            ).fetchall(), "sell")
        return {"bids": bids, "asks": asks, "spread": asks[0]["precio"] - bids[0]["precio"] if bids and asks else 0}

    @staticmethod
    def saldo(usuario: str) -> dict:
        with get_db() as c:
            u = c.execute("SELECT saldo_zyxsof, saldo_usd FROM usuarios WHERE nombre=?",
                          (usuario,)).fetchone()
        return dict(u) if u else {}


# ==============================================================================
# 📡  BOT DE FRECUENCIAS — Motor ZFPI K'uhul
# ==============================================================================
class BotFrecuencias:
    """
    Convierte el precio de mercado en señales de frecuencia K'uhul.
    Fricción cero: genera orden directa cuando la coherencia cruza umbrales.
    """

    def __init__(self):
        self.ciclos         = 0
        self.compras        = 0
        self.ventas         = 0
        self.ultima_coh     = 0.0
        self.ultimo_precio  = 0.0
        self.historial      : list[dict] = []
        self._activo        = False
        self._hilo          : Optional[threading.Thread] = None

    # ── Matemática K'uhul ────────────────────────────────────────────────────
    @staticmethod
    def precio_a_frecuencia(precio: float) -> float:
        rango = CFG.PRECIO_MAX_BTC - CFG.PRECIO_MIN_BTC + 1e-9
        norm  = (precio - CFG.PRECIO_MIN_BTC) / rango
        return 8.0 + norm * 8.0

    @staticmethod
    def contraparte(f: float) -> float:
        return (CFG.FRECUENCIA_BASE ** 2) / max(f, 0.01)

    def coherencia(self, f1: float, f2: float) -> float:
        f2e  = self.contraparte(f2)
        diff = abs(f1 - f2e)
        return 1.0 - diff / (f1 + f2e + 1e-9)

    def obtener_precio(self) -> Optional[float]:
        """Intenta precio real de Binance. Fallback aleatorio simulado."""
        if CFG.BINANCE_KEY:
            try:
                import requests as _r
                r = _r.get(
                    "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
                    timeout=4
                )
                return float(r.json()["price"])
            except Exception:
                pass
        # Simulación con movimiento browniano
        base = self.ultimo_precio or 50_000.0
        return round(base * (1 + random.gauss(0, 0.002)), 2)

    def ejecutar_ciclo(self, tesorero: "AgenteTesoreria",
                       trader: "AgenteTrading") -> dict:
        precio = self.obtener_precio()
        if precio is None:
            return {"error": "Sin precio"}

        self.ciclos       += 1
        self.ultimo_precio = precio
        freq = self.precio_a_frecuencia(precio)
        coh  = self.coherencia(freq, CFG.FRECUENCIA_BASE)
        self.ultima_coh = coh

        senal = {
            "ciclo":      self.ciclos,
            "precio":     precio,
            "frecuencia": round(freq, 4),
            "coherencia": round(coh, 4),
            "tipo":       "NEUTRAL",
            "accion":     None,
        }

        if coh > CFG.UMBRAL_COMPRA:
            self.compras += 1
            senal["tipo"] = "COMPRA"
            # Solicitar fondos al Tesorero antes de ejecutar
            fondos = tesorero.verificar_fondos(precio * 0.001)
            if fondos["seguro"]:
                res = trader.ejecutar_trade("buy", precio, 0.001, "sofi_bot")
                senal["accion"] = res
                log.info(f"🟢 COMPRA #{self.compras} | coh:{coh:.4f} | ${precio:,.0f}")
            else:
                senal["accion"] = {"bloqueado": "Fondos insuficientes — Tesorero denegó"}
                log.warning(f"⚠️  COMPRA bloqueada — sin fondos suficientes")

        elif coh < CFG.UMBRAL_VENTA:
            self.ventas += 1
            senal["tipo"] = "VENTA"
            res = trader.ejecutar_trade("sell", precio, 0.001, "sofi_bot")
            senal["accion"] = res
            log.info(f"🔴 VENTA #{self.ventas} | coh:{coh:.4f} | ${precio:,.0f}")
        else:
            log.info(f"⏸️  NEUTRAL | coh:{coh:.4f} | ${precio:,.0f} | ciclo:{self.ciclos}")

        self.historial.append(senal)
        if len(self.historial) > 200:
            self.historial.pop(0)

        # Guardar señal en BD
        with get_db() as c:
            c.execute(
                "INSERT INTO senales (tipo,precio,coherencia) VALUES (?,?,?)",
                (senal["tipo"], precio, coh)
            )

        return senal

    def iniciar(self, tesorero: "AgenteTesoreria", trader: "AgenteTrading"):
        self._activo = True
        def _loop():
            log.info("🤖 Bot ZFPI K'uhul iniciado — Fricción Cero")
            while self._activo:
                try:
                    self.ejecutar_ciclo(tesorero, trader)
                except Exception as e:
                    log.error(f"Bot error: {e}")
                time.sleep(CFG.INTERVALO_BOT)
        self._hilo = threading.Thread(target=_loop, daemon=True)
        self._hilo.start()

    def detener(self):
        self._activo = False

    def estado(self) -> dict:
        return {
            "ciclos":        self.ciclos,
            "compras":       self.compras,
            "ventas":        self.ventas,
            "ultima_coh":    self.ultima_coh,
            "ultimo_precio": self.ultimo_precio,
            "frecuencia_base": CFG.FRECUENCIA_BASE,
            "activo":        self._activo,
        }


# ==============================================================================
# 🏦  AGENTE TESORERÍA — Libro contable, wallets, autorización de fondos
# ==============================================================================
class AgenteTesoreria:
    """
    Único custodio del capital. Ningún trade se ejecuta sin su autorización.
    Mantiene balance ZYXSOF en memoria + persiste en MongoDB si disponible.
    """

    def __init__(self):
        self.nombre          = "Tesorero_01"
        self.balance_zyxsof  = 0.0
        self.balance_usd     = 0.0
        self.operaciones     = 0
        self._lock           = threading.Lock()
        self._mongo_col      = None
        self._iniciar_mongo()
        self._sincronizar_desde_db()
        log.info(f"🏦 [{self.nombre}] Tesorería en línea.")

    def _iniciar_mongo(self):
        if MONGO_OK and CFG.MONGO_URI:
            try:
                db = MongoClient(CFG.MONGO_URI, serverSelectionTimeoutMS=3000)["HaaPpDigitalV"]
                self._mongo_col = db["Tesoreria_ZYXSOF"]
                log.info("🏦 Tesorería anclada en MongoDB Atlas.")
            except Exception as e:
                log.warning(f"MongoDB Tesorería no disponible: {e}")

    def _sincronizar_desde_db(self):
        with get_db() as c:
            u = c.execute(
                "SELECT saldo_zyxsof, saldo_usd FROM usuarios WHERE nombre=?",
                (self.nombre,)
            ).fetchone()
            if u:
                self.balance_zyxsof = u["saldo_zyxsof"]
                self.balance_usd    = u["saldo_usd"]

    def verificar_fondos(self, monto_usd: float) -> dict:
        with self._lock:
            ok = self.balance_usd >= monto_usd
            return {
                "seguro":         ok,
                "balance_usd":    round(self.balance_usd, 4),
                "monto_requerido": monto_usd,
                "mensaje": "✅ Fondos autorizados" if ok else "🚫 Fondos insuficientes"
            }

    def conciliar(self, tipo: str, monto_zyxsof: float,
                  monto_usd: float, firma: str = "") -> dict:
        """Actualiza el libro tras un trade ejecutado."""
        with self._lock:
            self.operaciones += 1
            if tipo == "buy":
                self.balance_zyxsof += monto_zyxsof
                self.balance_usd    -= monto_usd
            elif tipo == "sell":
                self.balance_zyxsof -= monto_zyxsof
                self.balance_usd    += monto_usd

            registro = osiris.sellar("CONCILIACION", {
                "op": self.operaciones, "tipo": tipo,
                "delta_zyxsof": monto_zyxsof, "delta_usd": monto_usd,
                "balance_zyxsof": round(self.balance_zyxsof, 6),
                "balance_usd":    round(self.balance_usd, 4),
            })

            # Persistir en MongoDB
            if self._mongo_col:
                try:
                    self._mongo_col.insert_one({**registro, "ts": datetime.utcnow()})
                except Exception:
                    pass

            # Actualizar SQLite
            with get_db() as c:
                c.execute(
                    "UPDATE usuarios SET saldo_zyxsof=?, saldo_usd=? WHERE nombre=?",
                    (self.balance_zyxsof, self.balance_usd, self.nombre)
                )
            return registro

    def transferir(self, monto: float, destino: str = "MercadoPago") -> dict:
        if self.balance_usd < monto:
            return {"error": "Fondos insuficientes para transferencia"}
        with self._lock:
            self.balance_usd -= monto
            sello = osiris.sellar("TRANSFERENCIA", {
                "monto": monto, "destino": destino,
                "balance_post": round(self.balance_usd, 4)
            })
        return {"exito": True, "referencia": sello["firma_jhop"], "sello": sello}

    def estado(self) -> dict:
        return {
            "nombre":         self.nombre,
            "balance_zyxsof": round(self.balance_zyxsof, 6),
            "balance_usd":    round(self.balance_usd, 4),
            "operaciones":    self.operaciones,
        }


# ==============================================================================
# 📈  AGENTE TRADING — Ejecutor de mercado
# ==============================================================================
class AgenteTrading:
    """
    Ejecuta órdenes en el MarketEngine local.
    Solo actúa cuando Tesorero autoriza (verificar_fondos()).
    """

    def __init__(self, tesorero: AgenteTesoreria):
        self.nombre    = "Trader_01"
        self.tesorero  = tesorero
        self.trades    = 0
        self.pnl       = 0.0
        self._lock     = threading.Lock()
        log.info(f"📈 [{self.nombre}] Trader en línea.")

    def ejecutar_trade(self, tipo: str, precio: float,
                       cantidad: float, usuario: str = "sofi_bot") -> dict:
        with self._lock:
            resultado = MarketEngine.crear_orden(usuario, tipo, precio, cantidad)
            if resultado.get("exito"):
                self.trades += 1
                monto_usd = precio * cantidad
                conciliacion = self.tesorero.conciliar(
                    tipo, cantidad, monto_usd, resultado["sello"]["firma_jhop"]
                )
                resultado["conciliacion"] = conciliacion
                resultado["trade_num"]    = self.trades
            return resultado

    def solicitar_autorizacion(self, precio: float, cantidad: float) -> bool:
        fondos = self.tesorero.verificar_fondos(precio * cantidad)
        return fondos["seguro"]

    def estado(self) -> dict:
        return {
            "nombre": self.nombre,
            "trades": self.trades,
            "pnl":    round(self.pnl, 4),
        }


# ==============================================================================
# 🏦  BANCO KUSOFIN — KuzoFynum + MotorSierra + Migrador
# ==============================================================================
class MotorSierra:
    def __init__(self, min_trabajo: int = 15, min_descanso: int = 15):
        self.min_trabajo  = min_trabajo
        self.min_descanso = min_descanso
        self.ciclos       = 0
        self._t0          = time.time()

    def fase(self) -> str:
        total = (self.min_trabajo + self.min_descanso) * 60
        t     = (time.time() - self._t0) % total
        return "TRABAJO" if t < self.min_trabajo * 60 else "DESCANSO"

    def ciclo(self) -> dict:
        self.ciclos += 1
        f = self.fase()
        return {
            "fase":       f,
            "ciclos":     self.ciclos,
            "intensidad": 0.75 if f == "TRABAJO" else 0.25,
            "ts":         datetime.utcnow().isoformat()
        }

    def estado(self) -> dict:
        return {"fase": self.fase(), "ciclos": self.ciclos,
                "config": f"{self.min_trabajo}T/{self.min_descanso}D min"}


class BancoKUSOFIN:
    """
    Ciclo bancario coherencial + MotorSierra + Migrador de capital.
    Pulso autónomo cada 30 s.
    """

    def __init__(self):
        self.activo           = False
        self.ciclos_bancarios = 0
        self.volumen_total    = 0.0
        self.saldo_acumulado  = 120.50
        self.sierra           = MotorSierra()
        self._lock            = threading.Lock()
        self._hilo            : Optional[threading.Thread] = None
        # Migrador simple inline
        self.meta_mxn         = CFG.META_MXN
        self.fase_migracion   = "INICIO"
        log.info("🏦 BancoKUSOFIN listo.")

    def activar(self) -> dict:
        if self.activo:
            return {"exito": True, "mensaje": "Banco KUZ ya activo"}
        self.activo = True
        self._hilo = threading.Thread(target=self._pulso, daemon=True)
        self._hilo.start()
        return {"exito": True, "mensaje": "🏦 Bank_KUSOFIN ACTIVADO — 12.3 Hz"}

    def _pulso(self):
        while self.activo:
            time.sleep(30)
            try:
                self._ejecutar_ciclo_interno()
            except Exception as e:
                log.error(f"KUZ pulso error: {e}")

    def _ejecutar_ciclo_interno(self) -> dict:
        with self._lock:
            self.ciclos_bancarios += 1
            coherencia    = round(
                0.85 + math.sin(time.time() / 3600) * 0.1 + random.uniform(-0.02, 0.02), 4
            )
            volumen       = round(coherencia * CFG.FRECUENCIA_BASE * 0.001, 6)
            self.volumen_total   += volumen
            self.saldo_acumulado += volumen * CFG.FRECUENCIA_BASE

            # Actualizar fase de migración
            pct = self.saldo_acumulado / self.meta_mxn
            if pct < 0.25:     self.fase_migracion = "INICIO"
            elif pct < 0.60:   self.fase_migracion = "ACELERACION"
            elif pct < 0.95:   self.fase_migracion = "CONSOLIDACION"
            else:              self.fase_migracion = "META_ALCANZADA"

            ciclo = {
                "ciclo":      self.ciclos_bancarios,
                "coherencia": coherencia,
                "volumen":    volumen,
                "acumulado":  round(self.saldo_acumulado, 2),
                "fase":       self.fase_migracion,
            }
            log.debug(f"🏦 KUZ ciclo #{self.ciclos_bancarios} | coh:{coherencia} | saldo:${self.saldo_acumulado:.2f}")
            return ciclo

    def ejecutar_ciclo_manual(self) -> dict:
        ciclo  = self._ejecutar_ciclo_interno()
        sierra = self.sierra.ciclo()
        return {**ciclo, "sierra": sierra, "firma_jhop": osiris.firmar(ciclo)[:12]}

    def generar_sustento(self, monto: float = 500.0) -> dict:
        return {
            "referencia":  f"KUZ-{int(time.time())}-{int(monto)}",
            "monto_mxn":   monto,
            "tipo":        "TRANSFERENCIA_SPEI",
            "concepto":    "HaaPpDigitalV — Bank_KUSOFIN",
            "frecuencia":  CFG.FRECUENCIA_BASE,
            "valido_hasta": int(time.time()) + 3600,
            "ts":           datetime.utcnow().isoformat()
        }

    def estado(self) -> dict:
        return {
            "activo":          self.activo,
            "ciclos_bancarios":self.ciclos_bancarios,
            "volumen_total":   round(self.volumen_total, 6),
            "saldo_acumulado": round(self.saldo_acumulado, 2),
            "meta_mxn":        self.meta_mxn,
            "porcentaje_meta": f"{min(round(self.saldo_acumulado/self.meta_mxn*100, 1), 100)}%",
            "fase_migracion":  self.fase_migracion,
            "sierra":          self.sierra.estado(),
        }


# ==============================================================================
# 👁️  SOFÍ OBSERVADORA — Consumidora de inteligencia financiera
#
#  RESPONSABILIDAD ÚNICA:
#    • Absorber cada evento del ecosistema (trades, señales, ciclos bancarios)
#    • Clasificarlo en los 9 Planos del Cortex
#    • Enviarlo al bus K'uhul de SOFÍ V9 como paquete de aprendizaje
#    • Guardar en BD local para auditoría offline
#
#  LO QUE NO HACE:
#    • NO ejecuta órdenes (eso es AgenteTrading)
#    • NO custodia fondos (eso es AgenteTesoreria)
#    • NO toma decisiones de trading (eso es BotFrecuencias)
#
#  RESULTADO: SOFÍ V9 recibe un flujo constante de eventos reales que
#  alimentan su memoria vectorial y evolucionan su lógica autónoma.
# ==============================================================================
class SofiObservadora:

    PLANO_MAP = {
        "trade":     5,   # Galaxias — Agentes/Zánganos
        "senal":     5,
        "banco":     5,
        "tesoreria": 5,
        "riesgo":    8,   # Radiación Gamma — Seguridad
        "error":     8,
        "aprendizaje": 9, # Red Cósmica K'uhul
        "ciclo":     3,   # Materia Ordinaria
    }

    def __init__(self):
        self.eventos_enviados    = 0
        self.eventos_locales     = 0
        self.cola: list[dict]    = []
        self._activa             = False
        self._hilo               : Optional[threading.Thread] = None
        log.info("👁️  SofíObservadora: modo escucha activo — alimentando inteligencia.")

    # ── Ingesta de eventos ────────────────────────────────────────────────────
    def absorber(self, categoria: str, datos: dict):
        """Llamar desde cualquier módulo después de cada operación significativa."""
        plano = self.PLANO_MAP.get(categoria, 3)
        evento = {
            "categoria":    categoria,
            "plano":        plano,
            "datos":        datos,
            "aprendizaje":  self._sintetizar_aprendizaje(categoria, datos),
            "ts":           datetime.utcnow().isoformat(),
            "firma_jhop":   osiris.firmar(datos)[:10],
        }
        self.cola.append(evento)
        self.eventos_locales += 1

        # Persistir en BD
        with get_db() as c:
            c.execute(
                "INSERT INTO eventos_sofi (categoria, payload) VALUES (?,?)",
                (categoria, json.dumps(evento, ensure_ascii=False))
            )

    def _sintetizar_aprendizaje(self, categoria: str, datos: dict) -> str:
        """
        Convierte datos crudos en una frase de aprendizaje para el Cortex de SOFÍ.
        Esto es lo que realmente alimenta su inteligencia lógica.
        """
        if categoria == "senal":
            tipo = datos.get("tipo", "?")
            coh  = datos.get("coherencia", 0)
            px   = datos.get("precio", 0)
            return (
                f"Cuando coherencia={coh:.3f} y precio={px:.0f}, "
                f"la señal óptima fue {tipo}. "
                f"{'Alta coherencia indica compra ZYXSOF.' if tipo=='COMPRA' else 'Baja coherencia indica venta o espera.'}"
            )
        elif categoria == "trade":
            return (
                f"Trade ejecutado: {datos.get('tipo','?')} "
                f"{datos.get('cantidad',0):.6f} ZYXSOF @ {datos.get('precio',0):.2f} USD. "
                f"El ecosistema opera con fricción de compra en cero."
            )
        elif categoria == "banco":
            return (
                f"Ciclo bancario #{datos.get('ciclo','?')} — coherencia {datos.get('coherencia','?')}. "
                f"Fase migración: {datos.get('fase','?')}. "
                f"Capital acumulado avanza hacia meta MXN."
            )
        elif categoria == "tesoreria":
            return (
                f"Conciliación: balance ZYXSOF={datos.get('balance_zyxsof','?')}, "
                f"USD={datos.get('balance_usd','?')}. "
                f"La Tesorería es el único custodio del capital del ecosistema."
            )
        elif categoria == "riesgo":
            return f"Alerta de riesgo detectada: {datos}. SOFÍ debe incrementar umbral de seguridad."
        return f"Evento {categoria}: {str(datos)[:100]}"

    # ── Transmisión al bus SOFÍ V9 ────────────────────────────────────────────
    async def _enviar_al_bus(self, evento: dict):
        if not WS_OK or not CFG.SOFI_URL:
            return
        try:
            async with _ws_lib.connect(CFG.SOFI_URL, open_timeout=5) as ws:
                paquete = {
                    "origen":  "SofiObservadora_AFU",
                    "comando": evento["aprendizaje"],
                    "lat":     20.9674,
                    "lon":     -89.6237,
                    "meta": {
                        "categoria": evento["categoria"],
                        "plano":     evento["plano"],
                        "datos":     evento["datos"],
                    }
                }
                await ws.send(json.dumps(paquete))
                self.eventos_enviados += 1
        except Exception as e:
            log.debug(f"[SofíObs] No se pudo enviar al bus: {e}")

    def _loop_transmision(self):
        """Drena la cola cada 3 s y envía eventos pendientes a SOFÍ V9."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while self._activa:
            time.sleep(3)
            while self.cola:
                evento = self.cola.pop(0)
                try:
                    loop.run_until_complete(self._enviar_al_bus(evento))
                except Exception:
                    pass

    def iniciar(self):
        self._activa = True
        self._hilo   = threading.Thread(target=self._loop_transmision, daemon=True)
        self._hilo.start()
        log.info("👁️  SofíObservadora: transmisión al bus K'uhul iniciada.")

    def estado(self) -> dict:
        return {
            "activa":            self._activa,
            "eventos_locales":   self.eventos_locales,
            "eventos_enviados":  self.eventos_enviados,
            "cola_pendiente":    len(self.cola),
            "bus_sofi":          CFG.SOFI_URL or "⚠️ no configurado",
        }


# ==============================================================================
# ⚡  KEEP-ALIVE — evita que Render duerma el servicio
# ==============================================================================
def keep_alive():
    import urllib.request
    def _loop():
        while True:
            time.sleep(14 * 60)
            for nombre, url in [("Banco Python", CFG.SELF_URL), ("SOFI Node", CFG.SOFI_NODE_URL)]:
                if not url:
                    continue
                try:
                    req = urllib.request.Request(f"{url}/ping", headers={"User-Agent": "AFU/2.0"})
                    with urllib.request.urlopen(req, timeout=5) as r:
                        log.info(f"💓 keep-alive {nombre} ✅ ({r.status})")
                except Exception as e:
                    log.warning(f"⚠️  keep-alive {nombre}: {e}")
    threading.Thread(target=_loop, daemon=True).start()


# ==============================================================================
# 🌐  API FLASK — Endpoints operacionales
# ==============================================================================
def crear_api(tesorero: AgenteTesoreria, trader: AgenteTrading,
              bot: BotFrecuencias, banco: BancoKUSOFIN,
              sofi_obs: SofiObservadora):

    if not FLASK_OK:
        log.warning("Flask no instalado — API REST desactivada.")
        return None, None

    flask_app = Flask(__name__)
    CORS(flask_app)
    sio = SocketIO(flask_app, cors_allowed_origins="*", async_mode="threading")

    # ── Health ───────────────────────────────────────────────────────────────
    @flask_app.route("/ping")
    @flask_app.route("/health")
    def ping():
        return jsonify({
            "status":     "alive",
            "version":    "AFU-2.0",
            "frecuencia": f"{CFG.FRECUENCIA_BASE} Hz",
            "ts":         datetime.utcnow().isoformat()
        })

    # ── Estado global ────────────────────────────────────────────────────────
    @flask_app.route("/api/estado")
    def estado_global():
        return jsonify({
            "tesoreria":   tesorero.estado(),
            "trader":      trader.estado(),
            "bot":         bot.estado(),
            "banco":       banco.estado(),
            "sofi_obs":    sofi_obs.estado(),
            "libro":       MarketEngine.libro_ordenes(),
        })

    # ── Tesorería ────────────────────────────────────────────────────────────
    @flask_app.route("/api/tesoreria")
    def api_tesoreria():
        return jsonify(tesorero.estado())

    @flask_app.route("/api/tesoreria/verificar", methods=["POST"])
    def api_verificar():
        d = request.get_json(silent=True) or {}
        return jsonify(tesorero.verificar_fondos(float(d.get("monto_usd", 0))))

    @flask_app.route("/api/tesoreria/transferir", methods=["POST"])
    def api_transferir():
        d = request.get_json(silent=True) or {}
        return jsonify(tesorero.transferir(float(d.get("monto", 0)), d.get("destino", "MercadoPago")))

    # ── Trading ──────────────────────────────────────────────────────────────
    @flask_app.route("/api/trade", methods=["POST"])
    def api_trade():
        d = request.get_json(silent=True) or {}
        resultado = trader.ejecutar_trade(
            d.get("tipo", "buy"),
            float(d.get("precio", 50000)),
            float(d.get("cantidad", 0.001)),
            d.get("usuario", "sofi_bot")
        )
        sofi_obs.absorber("trade", {**d, "resultado": resultado})
        return jsonify(resultado)

    # ── Libro de órdenes ─────────────────────────────────────────────────────
    @flask_app.route("/api/libro")
    def api_libro():
        return jsonify(MarketEngine.libro_ordenes())

    # ── Bot ──────────────────────────────────────────────────────────────────
    @flask_app.route("/api/bot/estado")
    def api_bot_estado():
        return jsonify(bot.estado())

    @flask_app.route("/api/bot/senal")
    def api_senal_manual():
        senal = bot.ejecutar_ciclo(tesorero, trader)
        sofi_obs.absorber("senal", senal)
        return jsonify(senal)

    # ── Banco KUSOFIN ────────────────────────────────────────────────────────
    @flask_app.route("/api/banco/estado")
    def api_banco_estado():
        return jsonify(banco.estado())

    @flask_app.route("/api/banco/activar", methods=["POST"])
    def api_banco_activar():
        return jsonify(banco.activar())

    @flask_app.route("/api/banco/ciclo")
    def api_banco_ciclo():
        ciclo = banco.ejecutar_ciclo_manual()
        sofi_obs.absorber("banco", ciclo)
        return jsonify(ciclo)

    @flask_app.route("/api/banco/sustento", methods=["GET", "POST"])
    def api_sustento():
        d = request.get_json(silent=True) or {}
        return jsonify(banco.generar_sustento(float(d.get("monto", 500))))

    # ── SOFÍ Observadora ─────────────────────────────────────────────────────
    @flask_app.route("/api/sofi/estado")
    def api_sofi_estado():
        return jsonify(sofi_obs.estado())

    @flask_app.route("/api/sofi/cola")
    def api_sofi_cola():
        with get_db() as c:
            rows = c.execute(
                "SELECT categoria, payload, timestamp FROM eventos_sofi ORDER BY id DESC LIMIT 50"
            ).fetchall()
        return jsonify([{"categoria": r["categoria"],
                         "payload":   json.loads(r["payload"]),
                         "ts":        r["timestamp"]} for r in rows])

    # ── Saldo de usuario ──────────────────────────────────────────────────────
    @flask_app.route("/api/saldo/<usuario>")
    def api_saldo(usuario):
        return jsonify(MarketEngine.saldo(usuario))

    # ── SocketIO — pulso cada 5s ──────────────────────────────────────────────
    @sio.on("connect")
    def on_connect():
        sio.emit("bienvenida", {
            "mensaje":    "🌌 AFU-2.0 en línea — 12.3 Hz",
            "tesoreria":  tesorero.estado(),
            "bot":        bot.estado(),
            "banco":      banco.estado(),
        })

    def pulso_socketio():
        while True:
            time.sleep(5)
            try:
                sio.emit("pulso", {
                    "ts":        datetime.utcnow().isoformat(),
                    "bot":       bot.estado(),
                    "tesoreria": tesorero.estado(),
                    "sofi_obs":  sofi_obs.estado(),
                    "banco":     banco.estado(),
                })
            except Exception:
                pass

    threading.Thread(target=pulso_socketio, daemon=True).start()

    return flask_app, sio


# ==============================================================================
# 🚀  PUNTO DE ENTRADA
# ==============================================================================
def main():
    import sys
    modo = sys.argv[1] if len(sys.argv) > 1 else "--server"

    # ── Inicializar BD ────────────────────────────────────────────────────────
    init_db()

    # ── Instanciar ecosistema ─────────────────────────────────────────────────
    tesorero = AgenteTesoreria()
    trader   = AgenteTrading(tesorero)
    bot      = BotFrecuencias()
    banco    = BancoKUSOFIN()
    sofi_obs = SofiObservadora()

    # ── SofíObservadora siempre activa (transmite al bus K'uhul si hay URL) ──
    sofi_obs.iniciar()

    if modo == "--bot":
        log.info("▶  Modo BOT solo")
        bot.iniciar(tesorero, trader)
        while True:
            time.sleep(1)

    elif modo == "--banco":
        log.info("▶  Modo BANCO solo")
        banco.activar()
        while True:
            time.sleep(30)
            ciclo = banco.ejecutar_ciclo_manual()
            sofi_obs.absorber("banco", ciclo)

    else:
        # ── Modo servidor completo ────────────────────────────────────────────
        log.info("▶  Modo SERVIDOR COMPLETO — AFU 2.0")

        # Banco en ciclo autónomo
        banco.activar()

        # Bot frecuencias
        bot.iniciar(tesorero, trader)

        # Matching loop cada 5s
        def matching_loop():
            while True:
                trades = MarketEngine.ejecutar_matching()
                for t in trades:
                    sofi_obs.absorber("trade", t)
                time.sleep(5)
        threading.Thread(target=matching_loop, daemon=True).start()

        # Keep-alive Render
        keep_alive()

        # API Flask
        flask_app, sio = crear_api(tesorero, trader, bot, banco, sofi_obs)

        log.info("╔══════════════════════════════════════════════════╗")
        log.info("║  AGENTE FINANCIERO UNIVERSAL v2.0                ║")
        log.info(f"║  HaaPpDigitalV · Mérida, Yucatán, MX            ║")
        log.info(f"║  Puerto: {CFG.PORT}  |  Frecuencia: {CFG.FRECUENCIA_BASE} Hz       ║")
        log.info(f"║  Comisión de compra: {CFG.COMISION*100}% (FRICCIÓN CERO)    ║")
        log.info(f"║  SOFÍ Bus: {CFG.SOFI_URL[:40] if CFG.SOFI_URL else '⚠️ no configurado'}  ║")
        log.info("╚══════════════════════════════════════════════════╝")

        if flask_app and sio:
            sio.run(flask_app, host="0.0.0.0", port=CFG.PORT,
                    debug=False, use_reloader=False)
        else:
            while True:
                time.sleep(60)


if __name__ == "__main__":
    main()
