import requests
from bs4 import BeautifulSoup
 
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}
 
 
def get_cars(pages=3):
    cars = []
    seen_links = set()
 
    for page in range(1, pages + 1):
        url = f"https://mashina.kg/search/all/?page={page}"
 
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"[parser] Ошибка загрузки страницы {page}: {e}")
            continue
 
        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select("div.list-item, div.vip-item")
 
        if not items:
            print(f"[parser] Страница {page}: объявления не найдены")
            continue
 
        for item in items:
            try:
                # Ссылка
                link_tag = item.find("a", href=True)
                if not link_tag:
                    continue
 
                href = link_tag.get("href", "")
                link = "https://mashina.kg" + href if not href.startswith("http") else href
 
                if link in seen_links:
                    continue
                seen_links.add(link)
 
                # Заголовок
                title_tag = item.find("h2", class_="name")
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
 
                # 🔥 Цена — берём доллары и сомы отдельно
                price = "Цена не указана"
                price_tag = item.find("div", class_="block price")
                if price_tag:
                    p_tag = price_tag.find("p")
                    if p_tag:
                        strong = p_tag.find("strong")
                        dollar = strong.get_text(strip=True) if strong else ""
 
                        # Сомы — это текст после <br>
                        br = p_tag.find("br")
                        som = ""
                        if br and br.next_sibling:
                            som = str(br.next_sibling).strip()
 
                        if dollar and som:
                            price = f"{dollar}\n{som}"
                        elif dollar:
                            price = dollar
                        else:
                            price = price_tag.get_text(strip=True)
 
                # Год
                year = ""
                year_tag = item.find("p", class_="year-miles")
                if year_tag:
                    span = year_tag.find("span")
                    if span:
                        year = span.get_text(strip=True).replace("г.", "").strip()
 
                cars.append({
                    "title": title,
                    "price": price,
                    "link": link,
                    "year": year,
                    "description": f"{title} {year}",
                })
 
            except Exception as e:
                print(f"[parser] Ошибка обработки объявления: {e}")
                continue
 
        print(f"[parser] Страница {page}: найдено {len(items)} объявлений")
 
    print(f"[parser] Итого уникальных объявлений: {len(cars)}")
    return cars
 
 
if __name__ == "__main__":
    cars = get_cars(pages=1)
    for car in cars[:10]:
        print(f"TITLE: {car['title']} | YEAR: {car['year']}")
        print(f"PRICE: {car['price']}")
        print("---")
 