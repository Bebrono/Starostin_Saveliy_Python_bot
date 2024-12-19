import requests
from bs4 import BeautifulSoup
import psycopg2
import os

URL_PROTRACKER = "https://dota2protracker.com"
DOTABUFF_URL = "https://ru.dotabuff.com/heroes"

DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB", "dota_db"),
    "user": os.getenv("POSTGRES_USER", "dota_user2"),
    "password": os.getenv("POSTGRES_PASSWORD", "1234"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", 5432)
}

def connect_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"ошибка подключения к БД: {e}")
        return None

def get_best_aspect(hero_name):
    url = f"{URL_PROTRACKER}/hero/{hero_name.replace(' ', '%20')}"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"ошибка подключения героя {hero_name}. Status code: {response.status_code}")
        return {"aspect": None, "win_rate": 0.0, "pick_rate": 0.0}

    soup = BeautifulSoup(response.content, 'html.parser')

    aspects = []

    # Находим все контейнеры аспектов героя
    aspect_containers = soup.select('div.flex.gap-2 > div.cursor-pointer')

    for aspect in aspect_containers:
        try:
            #берем аспекты
            name = aspect.select_one('.uppercase, .pr-2.text-md.uppercase').text.strip()

            pick_rate_element = aspect.select_one('div:-soup-contains("pick rate") b')
            pick_rate_text = pick_rate_element.text.strip().rstrip('%')
            pick_rate = float(pick_rate_text)

            win_rate_element = aspect.select_one('b[style*="color:rgba"]')
            win_rate_text = win_rate_element.text.strip().rstrip('%')
            win_rate = float(win_rate_text)

            aspects.append({
                'name': name,
                'pick_rate': pick_rate,
                'win_rate': win_rate
            })
        except (AttributeError, ValueError) as e:
            print(f"ошибка аспекта: {e}")
            continue

    if not aspects:
        return {"aspect": None, "win_rate": 0.0, "pick_rate": 0.0}

    best_aspect = max(aspects, key=lambda x: (x['pick_rate'], x['win_rate']))

    return {
        "aspect": best_aspect['name'],
        "win_rate": best_aspect['win_rate'],
        "pick_rate": best_aspect['pick_rate']
    }

def get_counters(hero_name):

    special_cases = {
        "Nature's Prophet": "natures-prophet"
    }

    hero_slug = special_cases.get(hero_name, hero_name.lower().replace(" ", "-"))

    url = f"{DOTABUFF_URL}/{hero_slug}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"ошибка подключения героя {hero_name}. Status code: {response.status_code}")
        return {"strong_against": [], "weak_against": []}

    soup = BeautifulSoup(response.text, "html.parser")

    def extract_heroes(section_index):
        section = soup.find_all("section")[section_index]
        rows = section.select("article table tbody tr")
        heroes = []

        for row in rows[:3]:
            hero = row.select_one("a.link-type-hero").text.strip()
            heroes.append(hero)
        return heroes

    try:
        strong_against = extract_heroes(4)
        weak_against = extract_heroes(5)
    except Exception as e:
        print(f"нет инфы в 4-5 секции {hero_name}, {e} берем 5-6")
        try:
            strong_against = extract_heroes(5)
            weak_against = extract_heroes(6)
        except Exception as e:
            print(f"нет инфы в 5-6 секции {hero_name}, {e} берем 6-7")
            try:
                strong_against = extract_heroes(6)
                weak_against = extract_heroes(7)
            except Exception as e:
                print(f"нет инфы в 5-6 секции {hero_name}. габелла: {e}")
                strong_against = []
                weak_against = []

    return {"strong_against": strong_against, "weak_against": weak_against}


def scrape_heroes():
    response = requests.get(URL_PROTRACKER)

    if response.status_code != 200:
        print(f"ошибка подключения Status code: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    table_container = soup.find("div", class_="flex flex-col")

    if not table_container:
        return []

    hero_rows = table_container.find_all(
        "div",
        class_="grid grid-cols-5 gap-2 py-1 px-2 bg-d2pt-gray-3 justify-start border-solid border-b border-d2pt-gray-5 text-xs font-medium svelte-16lgea8",
    )

    heroes = []

    for row in hero_rows:
        try:
            hero_name_tag = row.find("span", class_="hidden sm:block max-w-[90px]")
            hero_name = hero_name_tag.text.strip() if hero_name_tag else "Unknown Hero"

            winrate_tag_green = row.find(
                "div",
                class_="ch2 flex gap-1 items-center justify-center text-sm font-medium green svelte-16lgea8",
            )
            winrate_tag_red = row.find(
                "div",
                class_="ch2 flex gap-1 items-center justify-center text-sm font-medium red svelte-16lgea8",
            )

            if winrate_tag_green:
                win_rate_text = winrate_tag_green.get_text(strip=True).replace("%", "")
            elif winrate_tag_red:
                win_rate_text = winrate_tag_red.get_text(strip=True).replace("%", "")
            else:
                win_rate_text = "0.0"

            win_rate = float(win_rate_text)

            print(f"Берем аспект для {hero_name}...")
            best_aspect = get_best_aspect(hero_name)

            print(f"Берем героев для  {hero_name}...")
            counters = get_counters(hero_name)

            print(f"Герой: {hero_name}, Аспект: {best_aspect}, герои: {counters}")

            heroes.append({
                "name": hero_name,
                "win_rate": win_rate,
                "best_aspect": best_aspect["aspect"],
                "best_aspect_win_rate": best_aspect["win_rate"],
                "best_aspect_pick_rate": best_aspect["pick_rate"],
                "strong_against": counters["strong_against"],
                "weak_against": counters["weak_against"],
            })
        except Exception as e:
            print(f"Error processing row for hero: {e}")
            continue

    return heroes

def save_heroes_to_db(heroes):
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            for hero in heroes:
                cur.execute(
                    """
                    INSERT INTO heroes (name, win_rate, best_aspect, best_aspect_win_rate, best_aspect_pick_rate, strong_against, weak_against)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO UPDATE SET
                        win_rate = EXCLUDED.win_rate,
                        best_aspect = EXCLUDED.best_aspect,
                        best_aspect_win_rate = EXCLUDED.best_aspect_win_rate,
                        best_aspect_pick_rate = EXCLUDED.best_aspect_pick_rate,
                        strong_against = EXCLUDED.strong_against,
                        weak_against = EXCLUDED.weak_against;
                    """,
                    (
                        hero["name"],
                        hero["win_rate"],
                        hero["best_aspect"],
                        hero["best_aspect_win_rate"],
                        hero["best_aspect_pick_rate"],
                        hero["strong_against"],
                        hero["weak_against"]
                    ),
                )
        conn.commit()
        print("Heroes data has been saved successfully!")
    except Exception as e:
        print(f"Failed to save heroes to the database: {e}")
    finally:
        conn.close()

# if __name__ == "__main__":
#     heroes = scrape_heroes()
#     if heroes:
#         save_heroes_to_db(heroes)
