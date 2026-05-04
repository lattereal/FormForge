import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
import time
import threading
from utils.logger import ConsoleColor, log_info, log_fail

QUESTION_TYPES = {
    0:  "Short Answer",
    1:  "Paragraph",
    2:  "Multiple Choice",
    3:  "Checkbox",
    4:  "Dropdown",
    5:  "Linear Scale",
    7:  "Grid",
    9:  "Date",
    10: "Time",
}

def _get_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def _clean_url(url):
    clean = url.split("?")[0]
    if not clean.endswith("/viewform"):
        clean = clean.rstrip("/") + "/viewform"
    return clean

def _extract_fb_data(html):
    for pattern in [
        r"var FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);\s*</script>",
        r"FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);",
    ]:
        m = re.search(pattern, html, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    return None

def _parse_from_html(html):
    data = _extract_fb_data(html)
    if data is None:
        return None

    try:
        question_blocks = data[1][1]
    except (IndexError, TypeError):
        return None

    qdict      = {}
    seen_ids   = set()
    page_count = 1

    for block in question_blocks:
        try:
            q_type_id = block[3]

            if q_type_id == 8:
                page_count += 1
                continue

            q_title  = block[1] or "Unknown Question"
            q_type   = QUESTION_TYPES.get(q_type_id, "Short Answer")
            required = bool(block[4][0][2]) if (
                block[4] and block[4][0] and len(block[4][0]) > 2
            ) else False

            entry_groups = block[4]
            if not entry_groups:
                continue

            for entry_group in entry_groups:
                try:
                    entry_id = f"entry.{entry_group[0]}"
                except (IndexError, TypeError):
                    continue

                if entry_id in seen_ids:
                    continue
                seen_ids.add(entry_id)

                options = []
                if q_type_id in (2, 3, 4):
                    raw_opts = entry_group[1] if len(entry_group) > 1 else []
                    if raw_opts:
                        for opt in raw_opts:
                            try:
                                label = opt[0]
                                if label and label != "__other_option__":
                                    options.append(label)
                            except (IndexError, TypeError):
                                pass
                elif q_type_id == 5:
                    try:
                        low  = int(entry_group[3])
                        high = int(entry_group[4])
                        options = [str(i) for i in range(low, high + 1)]
                    except Exception:
                        pass

                qdict[entry_id] = {
                    "Question": q_title,
                    "Type":     q_type,
                    "Options":  options,
                    "Required": required,
                }

        except (IndexError, TypeError):
            continue

    if not qdict:
        return None

    qdict["__pages__"] = page_count
    return qdict

def parse_form(url):
    C = ConsoleColor
    print(f"\n  {C.OKCYAN}Launching browser...{C.ENDC}")

    try:
        driver = _get_driver()
    except Exception as e:
        print(f"  {C.FAIL}Browser init failed: {e}{C.ENDC}")
        log_fail(f"Browser init failed: {e}")
        return None

    try:
        driver.get(_clean_url(url))
        print(f"  {C.OKCYAN}Waiting for page to load — solve any CAPTCHA if needed.{C.ENDC}")
        print(f"  {C.DIM}Press Enter to skip the wait early.{C.ENDC}\n")

        skip = threading.Event()

        def _listen():
            try:
                input()
            except Exception:
                pass
            skip.set()

        t = threading.Thread(target=_listen, daemon=True)
        t.start()

        for i in range(20, 0, -1):
            if skip.is_set():
                break
            print(f"  {C.DIM}  {i}s remaining... (Enter to skip){C.ENDC}", end="\r", flush=True)
            time.sleep(1)

        print(" " * 50, end="\r")
        skip.set()

        current_url = driver.current_url
        if "accounts.google.com" in current_url or "signin" in current_url.lower():
            driver.quit()
            print(f"  {C.FAIL}This form requires a Google sign-in.{C.ENDC}")
            print(f"  {C.DIM}Sign-in protected forms cannot be parsed or submitted automatically.{C.ENDC}")
            log_fail(f"Sign-in required for {url}")
            return None

        html = driver.page_source
        driver.quit()
    except Exception as e:
        try:
            driver.quit()
        except Exception:
            pass
        print(f"  {C.FAIL}Browser error: {e}{C.ENDC}")
        log_fail(f"Browser error: {e}")
        return None

    print(f"  {C.OKCYAN}Extracting form structure...{C.ENDC}")
    qdict = _parse_from_html(html)

    if qdict:
        pages = qdict.get("__pages__", 1)
        count = len(qdict) - 1
        page_note = f"  {C.DIM}({pages} page{'s' if pages > 1 else ''}){C.ENDC}" if pages > 1 else ""
        print(f"  {C.SUCCESS}Parsed {count} question(s) successfully!{C.ENDC}{page_note}")
        log_info(f"Parsed {count} questions ({pages} pages) from {url}")
        return qdict

    print(f"  {C.FAIL}No questions detected. The form may be private or require sign-in.{C.ENDC}")
    log_fail(f"Zero questions parsed from {url}")
    return None


def display_parsed_questions(qdict):
    if not qdict:
        print(f"  {ConsoleColor.FAIL}No questions to display.{ConsoleColor.ENDC}")
        return
    C = ConsoleColor
    width = 68
    print(f"\n{C.OKCYAN}{'─'*width}{C.ENDC}")
    print(f"  {C.BOLD}{C.WHITE}PARSED FORM QUESTIONS{C.ENDC}")
    print(f"{C.OKCYAN}{'─'*width}{C.ENDC}")
    for idx, (qid, q) in enumerate(qdict.items(), 1):
        if qid == "__pages__":
            continue
        req_tag    = f"{C.FAIL}[REQUIRED]{C.ENDC}" if q["Required"] else f"{C.DIM}[optional]{C.ENDC}"
        type_color = {
            "Multiple Choice": C.OKGREEN,
            "Checkbox":        C.WARNING,
            "Dropdown":        C.BLUE,
            "Short Answer":    C.OKCYAN,
            "Paragraph":       C.OKCYAN,
            "Linear Scale":    C.HEADER,
            "Date":            C.WHITE,
            "Time":            C.WHITE,
            "Grid":            C.HEADER,
        }.get(q["Type"], C.WHITE)
        print(f"\n  {C.BOLD}{C.WHITE}Q{idx}.{C.ENDC} {q['Question']}  {req_tag}")
        print(f"       {type_color}▸ {q['Type']}{C.ENDC}   {C.DIM}{qid}{C.ENDC}")
        if q["Options"]:
            for i, opt in enumerate(q["Options"], 1):
                print(f"         {C.DIM}{i}.{C.ENDC} {opt}")
    print(f"\n{C.OKCYAN}{'─'*width}{C.ENDC}\n")


def save_answers_json(answers, path):
    with open(path, "w") as f:
        json.dump(answers, f, indent=2)
    print(f"  {ConsoleColor.OKGREEN}Answers saved to {path}{ConsoleColor.ENDC}")


def load_answers_json(path):
    try:
        with open(path) as f:
            data = json.load(f)
        print(f"  {ConsoleColor.OKGREEN}Loaded {len(data)} answer(s) from {path}{ConsoleColor.ENDC}")
        return data
    except FileNotFoundError:
        print(f"  {ConsoleColor.FAIL}File not found: {path}{ConsoleColor.ENDC}")
        return None
    except json.JSONDecodeError as e:
        print(f"  {ConsoleColor.FAIL}JSON error: {e}{ConsoleColor.ENDC}")
        return None
