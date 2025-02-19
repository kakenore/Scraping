import requests
from bs4 import BeautifulSoup
import time
import random
import json
import os
from urllib.parse import urljoin

# ターゲットURL
base_url = "https://cookpad.com/jp/search/卵"

# 判別条件（表記ゆれ対応）
keyword_lists = {
    "卵": ["卵", "たまご", "玉子", "マヨネーズ", "かまぼこ", "はんぺん"],
    "小麦": ["トースト", "小麦", "小麦粉", "パン", "うどん", "パスタ", "麩", "そうめん", "薄力粉", "強力粉", "中力粉", "餃子の皮", "グルテン"],
    "乳": ["牛乳", "チーズ", "バター", "ヨーグルト", "クリーム", "発酵乳", "練乳", "れん乳", "粉ミルク", "アイスクリーム"]
}

# 保存先フォルダのベース
base_folder = "recipes_by_ingredient"
os.makedirs(base_folder, exist_ok=True)

# レシピ情報を格納するリスト
recipes = []

# 最大ページ数（約35件/ページ）
max_pages = 1  # 必要なページ数を設定

for page in range(1, max_pages + 1):
    # ページURLを生成
    url = f"{base_url}?page={page}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve page {page}")
        continue

    soup = BeautifulSoup(response.text, "html.parser")
    recipe_cards = soup.find_all("a", class_="block-link__main", itemprop="url")

    for card in recipe_cards:
        try:
            # レシピURL
            link = "https://cookpad.com" + card["href"]

            # レシピ名
            recipe_name = card.text.strip()

            # レシピページにアクセスして材料リストを取得
            recipe_response = requests.get(link)
            if recipe_response.status_code != 200:
                print(f"Failed to retrieve recipe: {link}")
                continue

            recipe_soup = BeautifulSoup(recipe_response.text, "html.parser")
            ingredients_data = recipe_soup.find_all("span")

            # 材料部分を抽出
            ingredients_list = [
                span.text.strip()
                for span in ingredients_data
                if span.text.strip() and span.text.strip() not in ["作り方", "保存済み"]
            ]

            # 表記ゆれ対応でキーワード判定
            def contains_keyword(keywords, ingredients):
                return any(any(kw in ingredient for kw in keywords) for ingredient in ingredients)

            contains_keywords = {key: contains_keyword(keyword_lists[key], ingredients_list) for key in keyword_lists}

            # 保存フォルダを決定
            save_folders = []
            for key, is_present in contains_keywords.items():
                if is_present:
                    folder_name = key.lower()  # フォルダ名を小文字に変換
                    save_folders.append(folder_name)

            # 該当なしの場合は "none" フォルダ
            if not save_folders:
                save_folders.append("none")

            # レシピ名を含む画像の取得
            img_tag = recipe_soup.find("img", alt=lambda value: value and recipe_name in value)
            if img_tag:  # レシピ名が alt の一部を含むかチェック
                img_url = img_tag["src"]

                # スキームがない場合は補完
                if img_url.startswith("//"):
                    img_url = urljoin("https://", img_url)
                elif img_url.startswith("/"):
                    img_url = urljoin(base_url, img_url)

                img_name = os.path.basename(img_url.split("?")[0])

                for folder in save_folders:
                    # 保存先フォルダを作成
                    folder_path = os.path.join(base_folder, folder)
                    os.makedirs(folder_path, exist_ok=True)

                    img_path = os.path.join(folder_path, img_name)

                    # 画像をダウンロードして保存
                    try:
                        img_data = requests.get(img_url).content
                        with open(img_path, "wb") as img_file:
                            img_file.write(img_data)
                        print(f"Downloaded image to {folder}: {img_name}")
                    except Exception as e:
                        raise RuntimeError(f"Failed to download image: {img_url}") from e

                # レシピ情報を格納
                recipes.append({
                    "Title": recipe_name,
                    "URL": link,
                    "Ingredients": ingredients_list,
                    "Contains Keywords": contains_keywords,
                    "Saved Folders": save_folders
                })

                print(f"Processed recipe: {recipe_name}")
        except Exception as e:
            print(f"Error processing recipe: {e}")

        # レシピ間でランダムに待機
        time.sleep(random.uniform(2, 5))

# JSONに保存
json_filename = "recipes_with_images.json"
with open(json_filename, "w", encoding="utf-8") as jsonfile:
    json.dump(recipes, jsonfile, ensure_ascii=False, indent=4)

print(f"Data saved to {json_filename}")
