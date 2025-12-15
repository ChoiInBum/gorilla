# ==========================
# crawl_utils2.py
# ==========================
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def crawl_card(card_id):
    """
    카드 상세 페이지에서 정보(이름, 연회비, 전월실적, 브랜드, 혜택: category, detail, detail_text)를 수집.
    - 혜택 항목 중 category(p)가 '유의사항'이면 해당 항목을 건너뜀.
    - 각 혜택의 dt(버튼)를 클릭해서 dd > div 안의 상세 텍스트를 얻음.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    # 안정화 옵션 추가
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-browser-side-navigation")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(f"https://www.card-gorilla.com/card/detail/{card_id}")
    except Exception as e:
        print(f"Card {card_id} 페이지 열기 실패: {e}")
        try:
            driver.quit()
        except:
            pass
        return None

    try:
        # 발급 중단 체크
        try:
            btn = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR,
                     "#q-app > section > div.card_detail.fr-view > section > div > article.card_top > div > div > div.data_area > div.btn_wrap > div > a > span > b")
                )
            )
            if btn.text.strip() == "신규발급이 중단된 카드입니다.":
                driver.quit()
                return None
        except:
            pass

        # 카드 이름
        try:
            name = driver.find_element(By.CSS_SELECTOR,
                "#q-app > section > div.card_detail.fr-view > section > div > article.card_top > div > div > div.data_area > div.tit > strong").text
        except:
            name = None

        # 연회비
        try:
            fee_elements = driver.find_elements(By.CSS_SELECTOR,
                "#q-app > section > div.card_detail.fr-view > section > div > article.card_top > div > div > div.bnf2 > dl:nth-child(1) > dd.in_out")
            fees = [el.text for el in fee_elements]
        except:
            fees = []

        # 전월 실적
        try:
            monthly = driver.find_element(By.CSS_SELECTOR,
                "#q-app > section > div.card_detail.fr-view > section > div > article.card_top > div > div > div.bnf2 > dl:nth-child(2) > dd").text
        except:
            monthly = None

        # 브랜드 리스트
        try:
            brand_elements = driver.find_elements(By.CSS_SELECTOR,
                "#q-app > section > div.card_detail.fr-view > section > div > article.card_top > div > div > div.bnf2 > dl:nth-child(3) > dd > span")
            brand = [el.text for el in brand_elements if el.text.strip() != ""]
        except:
            brand = []

        # 혜택 수집: dt 클릭해서 dd > div 텍스트 얻기, '유의사항' 제외
        benefits = []
        i = 1
        base_dl = "#q-app > section > div.card_detail.fr-view > section > div > article.cmd_con.benefit > div.lst.bene_area > dl:nth-child({idx})"
        while True:
            dl_selector = base_dl.format(idx=i)
            dt_selector = dl_selector + " > dt"
            p_selector = dt_selector + " > p"
            i_tag_selector = dt_selector + " > i"
            dd_box_selector = dl_selector + " > dd > div"

            try:
                # dt element (버튼) 확인
                dt_elem = driver.find_element(By.CSS_SELECTOR, dt_selector)
            except:
                # 더 이상 dl이 없으면 종료
                break

            # category (분류 p)
            try:
                category = driver.find_element(By.CSS_SELECTOR, p_selector).text
            except:
                category = ""

            # detail (작은 i 태그)
            try:
                detail = driver.find_element(By.CSS_SELECTOR, i_tag_selector).text
            except:
                detail = ""

            # '유의사항'이면 스킵
            if category.strip() == "유의사항":
                i += 1
                continue

            # 클릭해서 상세 박스 노출 시도
            box_text = ""
            try:
                # 시도 1: 이미 열려 있을 수 있으니 먼저 확인
                try:
                    box_elem = driver.find_element(By.CSS_SELECTOR, dd_box_selector)
                    # 텍스트가 비어있거나 숨겨져 있으면 클릭 시도
                    if not box_elem.text.strip():
                        raise Exception("box empty, try click")
                    box_text = box_elem.text.strip()
                except:
                    # 안전한 클릭 (JS 클릭)
                    try:
                        driver.execute_script("arguments[0].scrollIntoView(true);", dt_elem)
                        driver.execute_script("arguments[0].click();", dt_elem)
                    except Exception:
                        try:
                            dt_elem.click()
                        except Exception:
                            pass

                    # 클릭 후 잠깐 대기 및 박스 출현 대기
                    time.sleep(0.2)
                    try:
                        box_text = WebDriverWait(driver, 1.5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, dd_box_selector))
                        ).text
                    except:
                        # 짧게 추가 대기 시도
                        time.sleep(0.3)
                        try:
                            box_text = driver.find_element(By.CSS_SELECTOR, dd_box_selector).text
                        except:
                            box_text = ""
            except Exception:
                box_text = ""

            benefits.append({
                "category": category,
                "detail": detail,
                "detail_text": box_text
            })

            i += 1

        return {
            "id": card_id,
            "name": name,
            "fees": fees,
            "monthly_usage": monthly,
            "brand": brand,
            "benefits": benefits
        }

    except Exception as e:
        # 예기치 못한 에러 발생 시 로깅
        print(f"Card {card_id} 예외 발생: {e}")
        return None
    finally:
        try:
            driver.quit()
        except:
            pass
