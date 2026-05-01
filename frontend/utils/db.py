"""
SQLite database layer for AdoptSense.
All persistence for users, listings, photos, messages, watchlist, and KPIs.
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).parent.parent / "adoptsense.db"
UPLOAD_DIR = Path(__file__).parent.parent / "assets" / "uploads"
STUDIO_DIR = Path(__file__).parent.parent / "assets" / "studio"
SEED_DIR = Path(__file__).parent.parent / "assets" / "seed_photos"


def _ensure_dirs():
    for d in [UPLOAD_DIR, STUDIO_DIR, SEED_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    _ensure_dirs()
    conn = get_conn()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('shelter_manager', 'household')),
                shelter_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shelter_id INTEGER NOT NULL,
                pet_id TEXT,
                pet_name TEXT NOT NULL,
                type INTEGER NOT NULL DEFAULT 1,
                age INTEGER DEFAULT 0,
                breed1 INTEGER DEFAULT 0,
                breed2 INTEGER DEFAULT 0,
                gender INTEGER DEFAULT 1,
                color1 INTEGER DEFAULT 1,
                color2 INTEGER DEFAULT 0,
                color3 INTEGER DEFAULT 0,
                maturity_size INTEGER DEFAULT 0,
                fur_length INTEGER DEFAULT 0,
                vaccinated INTEGER DEFAULT 3,
                dewormed INTEGER DEFAULT 3,
                sterilized INTEGER DEFAULT 3,
                health INTEGER DEFAULT 1,
                quantity INTEGER DEFAULT 1,
                fee REAL DEFAULT 0,
                state INTEGER DEFAULT 41326,
                photo_amt INTEGER DEFAULT 0,
                video_amt INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                description_improved TEXT,
                status TEXT DEFAULT 'available',
                adoption_speed_pred INTEGER,
                adoption_speed_confidence REAL,
                adoption_speed_actual INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                adopted_at DATETIME,
                FOREIGN KEY (shelter_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS listing_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER NOT NULL,
                photo_path TEXT NOT NULL,
                is_studio_ready INTEGER DEFAULT 0,
                studio_photo_path TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS listing_kpis (
                listing_id INTEGER PRIMARY KEY,
                views INTEGER DEFAULT 0,
                contacts INTEGER DEFAULT 0,
                adoption_time_days INTEGER,
                last_view_at DATETIME,
                FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                listing_id INTEGER,
                content TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id),
                FOREIGN KEY (listing_id) REFERENCES listings(id)
            );

            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                listing_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, listing_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (listing_id) REFERENCES listings(id)
            );
        """)
    conn.close()


# ── Users ──────────────────────────────────────────────────────────────────────

def create_user(username: str, email: str, password_hash: str, role: str,
                shelter_name: Optional[str] = None) -> Optional[int]:
    conn = get_conn()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO users (username, email, password_hash, role, shelter_name) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, email, password_hash, role, shelter_name),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[Dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_shelters() -> List[Dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, username, shelter_name FROM users WHERE role = 'shelter_manager'"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Listings ───────────────────────────────────────────────────────────────────

def create_listing(shelter_id: int, pet_name: str, pet_type: int,
                   **kwargs: Any) -> int:
    conn = get_conn()
    fields = ["shelter_id", "pet_name", "type"] + list(kwargs.keys())
    values = [shelter_id, pet_name, pet_type] + list(kwargs.values())
    ph = ", ".join(["?"] * len(fields))
    with conn:
        cur = conn.execute(
            f"INSERT INTO listings ({', '.join(fields)}) VALUES ({ph})", values
        )
        lid = cur.lastrowid
        conn.execute("INSERT INTO listing_kpis (listing_id) VALUES (?)", (lid,))
    conn.close()
    return lid


def get_listing(listing_id: int) -> Optional[Dict]:
    conn = get_conn()
    row = conn.execute(
        """SELECT l.*, u.shelter_name, u.username AS shelter_username, u.id AS shelter_user_id
           FROM listings l JOIN users u ON l.shelter_id = u.id
           WHERE l.id = ?""",
        (listing_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_listings(filters: Optional[Dict] = None, limit: int = 200) -> List[Dict]:
    conn = get_conn()
    q = """SELECT l.*, u.shelter_name, u.username AS shelter_username
           FROM listings l JOIN users u ON l.shelter_id = u.id
           WHERE l.status = 'available'"""
    params: List[Any] = []

    if filters:
        if filters.get("type"):
            q += " AND l.type = ?"; params.append(filters["type"])
        if filters.get("min_age") is not None:
            q += " AND l.age >= ?"; params.append(filters["min_age"])
        if filters.get("max_age") is not None:
            q += " AND l.age <= ?"; params.append(filters["max_age"])
        if filters.get("max_fee") is not None:
            q += " AND l.fee <= ?"; params.append(filters["max_fee"])
        if filters.get("vaccinated"):
            q += " AND l.vaccinated = ?"; params.append(filters["vaccinated"])
        if filters.get("dewormed"):
            q += " AND l.dewormed = ?"; params.append(filters["dewormed"])
        if filters.get("sterilized"):
            q += " AND l.sterilized = ?"; params.append(filters["sterilized"])
        if filters.get("health"):
            q += " AND l.health = ?"; params.append(filters["health"])
        if filters.get("gender"):
            q += " AND l.gender = ?"; params.append(filters["gender"])
        if filters.get("maturity_size"):
            q += " AND l.maturity_size = ?"; params.append(filters["maturity_size"])
        if filters.get("color1"):
            q += " AND l.color1 = ?"; params.append(filters["color1"])
        if filters.get("shelter_id"):
            q += " AND l.shelter_id = ?"; params.append(filters["shelter_id"])
        if filters.get("max_speed") is not None:
            q += " AND l.adoption_speed_pred <= ?"; params.append(filters["max_speed"])

    q += " ORDER BY l.created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_shelter_listings(shelter_id: int) -> List[Dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT l.*, k.views, k.contacts, k.adoption_time_days
           FROM listings l LEFT JOIN listing_kpis k ON l.id = k.listing_id
           WHERE l.shelter_id = ? ORDER BY l.created_at DESC""",
        (shelter_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_listing(listing_id: int, **kwargs: Any) -> bool:
    if not kwargs:
        return False
    conn = get_conn()
    set_clause = ", ".join([f"{k} = ?" for k in kwargs])
    values = list(kwargs.values()) + [listing_id]
    with conn:
        conn.execute(f"UPDATE listings SET {set_clause} WHERE id = ?", values)
    conn.close()
    return True


def delete_listing(listing_id: int) -> bool:
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM listing_photos WHERE listing_id = ?", (listing_id,))
        conn.execute("DELETE FROM listing_kpis WHERE listing_id = ?", (listing_id,))
        conn.execute("DELETE FROM watchlist WHERE listing_id = ?", (listing_id,))
        conn.execute("DELETE FROM messages WHERE listing_id = ?", (listing_id,))
        conn.execute("DELETE FROM listings WHERE id = ?", (listing_id,))
    conn.close()
    return True


def mark_adopted(listing_id: int, actual_speed: int) -> bool:
    listing = get_listing(listing_id)
    if not listing:
        return False
    now = datetime.now().isoformat()
    days = (datetime.fromisoformat(now) - datetime.fromisoformat(listing["created_at"])).days
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE listings SET status='adopted', adopted_at=?, adoption_speed_actual=? WHERE id=?",
            (now, actual_speed, listing_id),
        )
        conn.execute(
            "UPDATE listing_kpis SET adoption_time_days=? WHERE listing_id=?",
            (days, listing_id),
        )
    conn.close()
    return True


# ── Photos ─────────────────────────────────────────────────────────────────────

def add_photo(listing_id: int, photo_path: str) -> int:
    conn = get_conn()
    with conn:
        cur = conn.execute(
            "INSERT INTO listing_photos (listing_id, photo_path) VALUES (?, ?)",
            (listing_id, photo_path),
        )
        pid = cur.lastrowid
        conn.execute(
            "UPDATE listings SET photo_amt = photo_amt + 1 WHERE id = ?", (listing_id,)
        )
    conn.close()
    return pid


def get_photos(listing_id: int) -> List[Dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM listing_photos WHERE listing_id = ? ORDER BY id", (listing_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_photo_studio(photo_id: int, studio_path: str) -> bool:
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE listing_photos SET is_studio_ready=1, studio_photo_path=? WHERE id=?",
            (studio_path, photo_id),
        )
    conn.close()
    return True


# ── KPIs ───────────────────────────────────────────────────────────────────────

def increment_views(listing_id: int):
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE listing_kpis SET views=views+1, last_view_at=? WHERE listing_id=?",
            (datetime.now().isoformat(), listing_id),
        )
    conn.close()


def increment_contacts(listing_id: int):
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE listing_kpis SET contacts=contacts+1 WHERE listing_id=?", (listing_id,)
        )
    conn.close()


def get_listing_kpi(listing_id: int) -> Optional[Dict]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM listing_kpis WHERE listing_id=?", (listing_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_shelter_kpis(shelter_id: int) -> Dict:
    conn = get_conn()
    rows = conn.execute(
        """SELECT l.*, k.views, k.contacts, k.adoption_time_days
           FROM listings l LEFT JOIN listing_kpis k ON l.id = k.listing_id
           WHERE l.shelter_id = ?""",
        (shelter_id,),
    ).fetchall()
    conn.close()
    ls = [dict(r) for r in rows]
    total = len(ls)
    active = sum(1 for r in ls if r["status"] == "available")
    adopted = sum(1 for r in ls if r["status"] == "adopted")
    speeds = [r["adoption_speed_actual"] for r in ls if r.get("adoption_speed_actual") is not None]
    los_vals = [r["adoption_time_days"] for r in ls if r.get("adoption_time_days") is not None]
    total_views = sum(r.get("views") or 0 for r in ls)
    total_contacts = sum(r.get("contacts") or 0 for r in ls)
    return {
        "total": total,
        "active": active,
        "adopted": adopted,
        "adoption_rate": (adopted / total * 100) if total else 0,
        "avg_adoption_speed": (sum(speeds) / len(speeds)) if speeds else None,
        "avg_los_days": (sum(los_vals) / len(los_vals)) if los_vals else None,
        "total_views": total_views,
        "total_contacts": total_contacts,
        "contact_rate": (total_contacts / total_views * 100) if total_views else 0,
        "listings": ls,
    }


# ── Messages ───────────────────────────────────────────────────────────────────

def send_message(sender_id: int, receiver_id: int, content: str,
                 listing_id: Optional[int] = None) -> int:
    conn = get_conn()
    with conn:
        cur = conn.execute(
            "INSERT INTO messages (sender_id, receiver_id, listing_id, content) VALUES (?,?,?,?)",
            (sender_id, receiver_id, listing_id, content),
        )
        mid = cur.lastrowid
    conn.close()
    if listing_id:
        increment_contacts(listing_id)
    return mid


def get_conversation(user1_id: int, user2_id: int,
                     listing_id: Optional[int] = None) -> List[Dict]:
    conn = get_conn()
    if listing_id:
        rows = conn.execute(
            """SELECT m.*, u.username AS sender_name FROM messages m
               JOIN users u ON m.sender_id = u.id
               WHERE m.listing_id = ?
               AND ((m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?))
               ORDER BY m.created_at ASC""",
            (listing_id, user1_id, user2_id, user2_id, user1_id),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT m.*, u.username AS sender_name FROM messages m
               JOIN users u ON m.sender_id = u.id
               WHERE (m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?)
               ORDER BY m.created_at ASC""",
            (user1_id, user2_id, user2_id, user1_id),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_conversations(user_id: int) -> List[Dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT
               CASE WHEN m.sender_id=? THEN m.receiver_id ELSE m.sender_id END AS other_id,
               u.username AS other_username,
               u.shelter_name,
               m.listing_id,
               l.pet_name,
               m.content AS last_message,
               m.created_at AS last_at,
               SUM(CASE WHEN m.receiver_id=? AND m.is_read=0 THEN 1 ELSE 0 END) AS unread_count
           FROM messages m
           JOIN users u ON u.id = CASE WHEN m.sender_id=? THEN m.receiver_id ELSE m.sender_id END
           LEFT JOIN listings l ON l.id = m.listing_id
           WHERE m.sender_id=? OR m.receiver_id=?
           GROUP BY other_id, m.listing_id
           ORDER BY last_at DESC""",
        (user_id, user_id, user_id, user_id, user_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_messages_read(reader_id: int, sender_id: int,
                        listing_id: Optional[int] = None):
    conn = get_conn()
    if listing_id:
        with conn:
            conn.execute(
                "UPDATE messages SET is_read=1 WHERE receiver_id=? AND sender_id=? AND listing_id=?",
                (reader_id, sender_id, listing_id),
            )
    else:
        with conn:
            conn.execute(
                "UPDATE messages SET is_read=1 WHERE receiver_id=? AND sender_id=?",
                (reader_id, sender_id),
            )
    conn.close()


def get_unread_count(user_id: int) -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM messages WHERE receiver_id=? AND is_read=0", (user_id,)
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


# ── Watchlist ──────────────────────────────────────────────────────────────────

def add_to_watchlist(user_id: int, listing_id: int) -> bool:
    conn = get_conn()
    try:
        with conn:
            conn.execute(
                "INSERT INTO watchlist (user_id, listing_id) VALUES (?,?)",
                (user_id, listing_id),
            )
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def remove_from_watchlist(user_id: int, listing_id: int) -> bool:
    conn = get_conn()
    with conn:
        conn.execute(
            "DELETE FROM watchlist WHERE user_id=? AND listing_id=?", (user_id, listing_id)
        )
    conn.close()
    return True


def is_in_watchlist(user_id: int, listing_id: int) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM watchlist WHERE user_id=? AND listing_id=?", (user_id, listing_id)
    ).fetchone()
    conn.close()
    return row is not None


def get_watchlist(user_id: int) -> List[Dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT l.*, u.shelter_name, u.username AS shelter_username, w.created_at AS saved_at
           FROM watchlist w JOIN listings l ON w.listing_id = l.id
           JOIN users u ON l.shelter_id = u.id
           WHERE w.user_id=? ORDER BY w.created_at DESC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_seeded() -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM listings WHERE pet_id IS NOT NULL"
    ).fetchone()
    conn.close()
    return (row["cnt"] > 0) if row else False
