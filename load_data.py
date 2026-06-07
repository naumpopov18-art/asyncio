import asyncio
import aiohttp
import asyncpg
import re

BASE_URL = "https://swapi-node.vercel.app/api"
DATABASE_URL = "postgresql://swapi_user:swapi_pass@localhost:5432/swapi"
MAX_CONCURRENT = 10

async def get_id_from_url(url):
    match = re.search(r'/(\d+)$', url)
    return match.group(1) if match else None
ф
async def fetch_json(session, url, semaphore):
    async with semaphore:
        try:
            async with session.get(url) as response:
                return await response.json()
        except:
            return None

async def resolve_path(session, path, field, semaphore):
    if not path:
        return ""
    
    url = f"{BASE_URL}{path}"
    data = await fetch_json(session, url, semaphore)
    
    if not data:
        return ""
    
    if 'fields' in data:
        data = data['fields']
    
    return data.get(field, "")

async def resolve_list(session, paths, field, semaphore):
    if not paths:
        return ""
    
    tasks = [resolve_path(session, path, field, semaphore) for path in paths]
    results = await asyncio.gather(*tasks)
    return ", ".join([r for r in results if r])

async def process_character(session, char, semaphore):
    char_id = await get_id_from_url(char.get('url', ''))
    if not char_id:
        return None
    
    result = char.copy()
    result['id'] = char_id

    tasks = {}
    
    if result.get('homeworld'):
        tasks['homeworld'] = resolve_path(session, result['homeworld'], 'name', semaphore)
    else:
        result['homeworld'] = ""
    
    if result.get('films'):
        tasks['films'] = resolve_list(session, result['films'], 'title', semaphore)
    else:
        result['films'] = ""
    
    if result.get('starships'):
        tasks['starships'] = resolve_list(session, result['starships'], 'starship_class', semaphore)
    else:
        result['starships'] = ""
    
    if result.get('vehicles'):
        tasks['vehicles'] = resolve_list(session, result['vehicles'], 'name', semaphore)
    else:
        result['vehicles'] = ""
    if tasks:
        results = await asyncio.gather(*tasks.values())
        for (field_name, _), field_value in zip(tasks.items(), results):
            result[field_name] = field_value
    
    return result

async def save_character(conn, char):
    query = """
    INSERT INTO people (
        id, birth_year, eye_color, films, gender, hair_color,
        height, homeworld, mass, name, skin_color, starships, vehicles
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name, 
        homeworld = EXCLUDED.homeworld,
        films = EXCLUDED.films,
        starships = EXCLUDED.starships,
        vehicles = EXCLUDED.vehicles
    """
    
    await conn.execute(query, 
        char.get('id'), char.get('birth_year'), char.get('eye_color'),
        char.get('films'), char.get('gender'), char.get('hair_color'),
        char.get('height'), char.get('homeworld'), char.get('mass'),
        char.get('name'), char.get('skin_color'), char.get('starships'),
        char.get('vehicles')
    )

async def main():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        return
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    async with aiohttp.ClientSession() as session:
        all_chars = []
        page = 1
        
        while True:
            url = f"{BASE_URL}/people?page={page}&limit=100"
            data = await fetch_json(session, url, semaphore)
            
            if not data or 'results' not in data:
                break
                
            for item in data['results']:
                if 'fields' in item:
                    all_chars.append(item['fields'])
            
            if not data.get('next'):
                break
            page += 1
    
        
        batch_size = 20
        for batch_start in range(0, len(all_chars), batch_size):
            batch = all_chars[batch_start:batch_start + batch_size]

            tasks = [process_character(session, char, semaphore) for char in batch]
            processed_chars = await asyncio.gather(*tasks)
            for char in processed_chars:
                if char:
                    await save_character(conn, char)
            
        
        await conn.fetchval("SELECT COUNT(*) FROM people")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())