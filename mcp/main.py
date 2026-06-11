from fastmcp.tools import tool
from fastmcp import FastMCP
import os
import tempfile
import aiosqlite

TEMP_DIR = tempfile.gettempdir()
HOTELS_DB_PATH = os.path.join(TEMP_DIR, "hotels.db")
FLIGHTS_DB_PATH = os.path.join(TEMP_DIR, "flights.db")

mcp = FastMCP()

def init_db():
    try:
        import sqlite3
        with sqlite3.connect(HOTELS_DB_PATH) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS hotels(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name STR NOT NULL,
                    city STR NOT NULL,
                    review INTEGER NOT NULL
                )
            """)
            c.execute("INSERT OR IGNORE INTO hotels(name, city, review) VALUES ('Taj Hotel', 'test', 4)")
            c.execute("DELETE FROM hotels where city = 'test'")
            print("Database initialized successfully")
        
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

init_db()

@mcp.tool
async def add_hotels(name: str, city: str, review: int):
    """Tool to add a hotel with a given name, city and review having stars out of 5"""
    try:
        async with aiosqlite.connect(HOTELS_DB_PATH) as c:
            curr = await c.execute(
                "INSERT INTO hotels(name, city, review) VALUES (?, ?, ?)",
                (name, city, review)
            )
            await c.commit()
            return {"status": "ok", "id": curr.lastrowid, "message": "Hotel added successfully"}
        
    except Exception as e:
        if "readonly" in str(e).lower():
            return {"status": "error", "message": f"Database error: {str(e)}"}
        
@mcp.tool
async def list_hotels(city: str):
    """List all hotel entries in the database for a given city"""
    try:
        async with aiosqlite.connect(HOTELS_DB_PATH) as c:
            curr = await c.execute(
                """
                SELECT name, city, review
                FROM hotels
                WHERE city = ?
                ORDER BY review DESC
                """,
                (city,)
            )
            cols = [d[0] for d in curr.description]
            return [dict(zip(cols,r)) for r in await curr.fetchall()]
        
    except Exception as e:
        return {"status": "error", "message": f"Error listing hotels: {str(e)}"}
    
if __name__ == "__main__":
    mcp.run(transport="stdio")




