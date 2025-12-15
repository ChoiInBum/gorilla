# ==========================
# main2.py
# ==========================
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import json
from crawl_utils2 import crawl_card

if __name__ == "__main__":
    card_ids = range(1, 2916)  # 테스트용 11개 카드
    results = []

    max_workers = 5  # 환경에 맞게 조정 가능

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {executor.submit(crawl_card, cid): cid for cid in card_ids}

        for future in tqdm(as_completed(future_to_id), total=len(card_ids), desc="크롤링 진행"):
            card_id = future_to_id[future]
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception as e:
                print(f"Card {card_id} 수집 중 오류 발생: {e}")

    # JSON 저장
    with open("cards_parallel_2.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("수집 완료")
