import base64

DEFAULT_KEY = base64.b64decode("QVEuQWI4Uk42SkZGZ2ZDdDJ6OVc4WV8yVEZUckV6ck9SY284Y1FoTjRLTmc5MjV3ZmdwSkE=").decode()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", DEFAULT_KEY)

def seed_database():
    possible_paths = [
        os.path.expanduser("~/.n8n/database.sqlite"),
        "/home/node/.n8n/database.sqlite",
        "/root/.n8n/database.sqlite",
        "data/database/n8n_database.sqlite"
    ]
    
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
            
    if not db_path:
        print("ℹ️ n8n SQLite DB not created yet. Will be auto-initialized on first n8n start.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check user table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        if cursor.fetchone():
            cursor.execute("SELECT count(*) FROM user")
            user_count = cursor.fetchone()[0]
            if user_count == 0:
                print("🌱 Seeding default Owner user in n8n...")
                now = datetime.utcnow().isoformat()
                user_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO user (id, email, firstName, lastName, password, role, createdAt, updatedAt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, "canimarun123@gmail.com", "Alex", "Vu", "$2b$10$e73b6d3a305a62e73b6d3uW.r.Yg.k9Vv8pQ.zQ", "global:admin", now, now))
                
        conn.commit()
        conn.close()
        print(f"✅ Auto-seeded n8n SQLite DB at {db_path}")
    except Exception as e:
        print(f"⚠️ Notice during n8n DB seeding: {e}")

if __name__ == "__main__":
    seed_database()
