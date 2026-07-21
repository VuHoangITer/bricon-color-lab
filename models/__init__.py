import psycopg2
import psycopg2.extras
from flask import g
import config


class PGConnection:
    """Bọc quanh 1 connection psycopg2 để hầu hết code trong models/ dùng
    được y hệt phong cách sqlite3 cũ — get_db().execute(q, params) trả
    thẳng về cursor có .fetchone()/.fetchall(), khỏi phải tự mở cursor ở
    từng nơi. Quan trọng hơn: TỰ ĐỘNG rollback ngay khi 1 câu lệnh lỗi —
    Postgres (khác SQLite) sẽ khóa cả transaction ở trạng thái 'aborted'
    sau 1 lỗi, khiến mọi câu lệnh sau đó trên CÙNG connection tiếp tục lỗi
    dây chuyền nếu không rollback. Vì 1 request Flask dùng chung 1
    connection (qua g.db) cho nhiều lệnh, hành vi tự rollback này giúp
    connection luôn dùng lại được ngay cả khi 1 thao tác (vd trùng mã màu)
    bị chặn bởi ràng buộc UNIQUE/FK ở giữa request."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, query, params=None):
        cur = self._conn.cursor()
        try:
            cur.execute(query, params or ())
        except Exception:
            self._conn.rollback()
            raise
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def connect():
    """Mở 1 connection Postgres mới, cấu hình đúng (RealDictCursor + múi
    giờ) — dùng chung cho get_db() (trong request Flask) lẫn các script
    độc lập (seed.py) để không script nào quên set cursor_factory/múi giờ."""
    conn = psycopg2.connect(
        host=config.DB_HOST, port=config.DB_PORT, dbname=config.DB_NAME,
        user=config.DB_USER, password=config.DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    # Ép múi giờ của phiên kết nối -> các cột TIMESTAMP (created_at,
    # duyet_luc...) lưu đúng giờ Việt Nam, giữ hành vi giống hệt
    # datetime('now','localtime') hồi còn SQLite, không cần sửa template.
    with conn.cursor() as cur:
        cur.execute("SET TIME ZONE %s", (config.DB_TIMEZONE,))
    conn.commit()
    return conn


def get_db():
    if "db" not in g:
        g.db = PGConnection(connect())
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)