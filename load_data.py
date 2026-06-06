import asyncio
import aiohttp
import asyncpg
import re

BASE_URL = "https://swapi-node.vercel.app/api"
DATABASE_URL = "postgresql://swapi_user:swapi_pass@localhost:5432/swapi"

async def get_id_from_url(url):
    match = re.search(r'/(\d+)$', url)
    return match.group(1) if match else None

async def fetch_json(session, url):
    try:
        async with session.get(url) as response:
            return await response.json()
    except:
        return None

async def resolve_path(session, path, field):
    if not path:
        return ""
    
    url = f"{BASE_URL}{path}"
    data = await fetch_json(session, url)
    
    if not data:
        return ""
    
    if 'fields' in data:
        data = data['fields']
    
    return data.get(field, "")

async def resolve_list(session, paths, field):
    if not paths:
        return ""
    
    tasks = [resolve_path(session, path, field) for path in paths]
    results = await asyncio.gather(*tasks)
    return ", ".join([r for r in results if r])

async def save_character(conn, char):
    query = """
    INSERT INTO people (
        id, birth_year, eye_color, films, gender, hair_color,
        height, homeworld, mass, name, skin_color, starships, vehicles
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name, homeworld = EXCLUDED.homeworld
    """
    
    await conn.execute(query, 
        char.get('id'), char.get('birth_year'), char.get('eye_color'),
        char.get('films'), char.get('gender'), char.get('hair_color'),
        char.get('height'), char.get('homeworld'), char.get('mass'),
        char.get('name'), char.get('skin_color'), char.get('starships'),
        char.get('vehicles')
    )

async def main():
    conn = await asyncpg.connect(DATABASE_URL)
    
    async with aiohttp.ClientSession() as session:
        all_chars = []
        page = 1
        
        while True:
            url = f"{BASE_URL}/people?page={page}&limit=100"
            data = await fetch_json(session, url)
            
            if not data or 'results' not in data:
                break
                
            for item in data['results']:
                if 'fields' in item:
                    all_chars.append(item['fields'])
            
            if not data.get('next'):
                break
            page += 1
        
        
        for i, char in enumerate(all_chars, 1):
            
            char['id'] = await get_id_from_url(char.get('url', ''))
            
            if char.get('homeworld'):
                char['homeworld'] = await resolve_path(session, char['homeworld'], 'name')
                
            if char.get('films'):
                char['films'] = await resolve_list(session, char['films'], 'title')
            else:
                char['films'] = ""

            if char.get('starships'):
                char['starships'] = await resolve_list(session, char['starships'], 'starship_class')
            else:
                char['starships'] = ""

            if char.get('vehicles'):
                char['vehicles'] = await resolve_list(session, char['vehicles'], 'name')
            else:
                char['vehicles'] = ""

            await save_character(conn, char)
        
        
        await conn.fetchval("SELECT COUNT(*) FROM people")

    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())