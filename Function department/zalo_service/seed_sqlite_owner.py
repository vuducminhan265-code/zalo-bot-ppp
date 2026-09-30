import sqlite3
import os
import datetime

def seed_owner():
    db_paths = [
        os.path.expanduser("~/.n8n/database.sqlite"),
        "/root/.n8n/database.sqlite",
        "/app/.n8n/database.sqlite"
    ]
    
    target_db = None
    for p in db_paths:
        if os.path.exists(p):
            target_db = p
            break
            
    if not target_db:
        # Create directory if needed and prepare database
        default_dir = os.path.expanduser("~/.n8n")
        if not os.path.exists(default_dir):
            try:
                os.makedirs(default_dir, exist_ok=True)
            except Exception:
                pass
        target_db = os.path.join(default_dir, "database.sqlite")

    print(f"[Seed Owner DB] Checking SQLite database at {target_db}...")
    try:
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        
        # Check if user table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user';")
        if cursor.fetchone():
            cursor.execute("SELECT id FROM user WHERE email = 'canimarun123@gmail.com';")
            user_row = cursor.fetchone()
            user_id = user_row[0] if user_row else "84b498d0-5806-452c-bc98-b98f8e6f150e"
            project_id = "6Uja56w0EWxAuJEP"
            now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            # Insert/Update User
            cursor.execute("""
                INSERT OR REPLACE INTO user (
                    id, email, firstName, lastName, password, personalizationAnswers,
                    createdAt, updatedAt, settings, disabled, mfaEnabled, roleSlug
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                "canimarun123@gmail.com",
                "Alex",
                "Vu",
                "$2b$10$FNWbdfjbUtjQHdxSnO1q9u/XjiJQ7j.PR8DVyLzjT/e.2pJWblmdy",
                '{"version":"v4","companySize":"<20","companyType":"education","role":"other","roleOther":"Finance"}',
                now_str,
                now_str,
                '{"userActivated":true}',
                0,
                0,
                "global:owner"
            ))
            
            # Insert/Update Project
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project';")
            if cursor.fetchone():
                cursor.execute("""
                    INSERT OR REPLACE INTO project (
                        id, name, type, createdAt, updatedAt, creatorId
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    project_id,
                    "Alex Vu <canimarun123@gmail.com>",
                    "personal",
                    now_str,
                    now_str,
                    user_id
                ))
                
            # Insert/Update Project Relation
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project_relation';")
            if cursor.fetchone():
                cursor.execute("""
                    INSERT OR REPLACE INTO project_relation (
                        projectId, userId, role, createdAt, updatedAt
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    project_id,
                    user_id,
                    "project:personalOwner",
                    now_str,
                    now_str
                ))
                
            conn.commit()
            print("✅ [Seed Owner DB] Tài khoản Owner 'canimarun123@gmail.com' và Personal Project đã được khởi tạo thành công!")
        conn.close()
    except Exception as e:
        print(f"⚠️ [Seed Owner DB Exception]: {e}")

if __name__ == "__main__":
    seed_owner()
