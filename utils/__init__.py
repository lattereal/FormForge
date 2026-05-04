import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading
import itertools
import string
import random
import time
import requests
from utils.logger import ConsoleColor, log_info, log_success, log_fail

CONFIG = {
    "delay":       0.35,
    "threads":     25,
    "use_proxies": False,
    "timeout":     20,
    "user_agent":  "random"
}

proxies      = []
proxy_cycle  = None
lock         = threading.Lock()
_successful  = [0]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

def get_successful_requests():
    return _successful[0]

def reset_successful_requests():
    _successful[0] = 0

def generate_cool_id():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(8))

def get_submit_headers(referer_url=""):
    ua = random.choice(USER_AGENTS) if CONFIG["user_agent"] == "random" else USER_AGENTS[0]
    return {
        "User-Agent":      ua,
        "Accept":          "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type":    "application/x-www-form-urlencoded",
        "Origin":          "https://docs.google.com",
        "Referer":         referer_url or "https://docs.google.com/forms/",
        "Connection":      "keep-alive",
        "Sec-Fetch-Dest":  "document",
        "Sec-Fetch-Mode":  "navigate",
        "Sec-Fetch-Site":  "same-origin",
    }

def get_random_headers():
    return get_submit_headers()

def get_proxy():
    global proxy_cycle
    if proxy_cycle and CONFIG["use_proxies"]:
        return next(proxy_cycle)
    return None

def load_proxies(filename=None):
    global proxies, proxy_cycle
    if filename is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filename = os.path.join(base, "data", "proxies.txt")
    try:
        with open(filename) as f:
            loaded = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        if loaded:
            proxies = loaded
            proxy_cycle = itertools.cycle(proxies)
            print(f"{ConsoleColor.OKGREEN}  {len(proxies)} proxies loaded from {filename}{ConsoleColor.ENDC}")
            log_info(f"Loaded {len(proxies)} proxies")
        else:
            print(f"{ConsoleColor.WARNING}  proxies.txt is empty.{ConsoleColor.ENDC}")
    except FileNotFoundError:
        print(f"{ConsoleColor.WARNING}  proxies.txt not found at {filename}{ConsoleColor.ENDC}")

def test_proxies():
    if not proxies:
        print(f"{ConsoleColor.FAIL}  No proxies loaded.{ConsoleColor.ENDC}")
        return
    print(f"\n{ConsoleColor.OKCYAN}  Testing {len(proxies)} proxies...{ConsoleColor.ENDC}")
    alive, dead = 0, 0
    for p in proxies:
        try:
            r = requests.get("https://api.ipify.org?format=json",
                             proxies={"http": p, "https": p}, timeout=8)
            if r.status_code == 200:
                print(f"  {ConsoleColor.OKGREEN}ALIVE{ConsoleColor.ENDC}  {p}  → {r.json().get('ip','?')}")
                alive += 1
            else:
                print(f"  {ConsoleColor.FAIL}DEAD {ConsoleColor.ENDC}  {p}")
                dead += 1
        except:
            print(f"  {ConsoleColor.FAIL}DEAD {ConsoleColor.ENDC}  {p}")
            dead += 1
    print(f"\n  Results: {ConsoleColor.OKGREEN}{alive} alive{ConsoleColor.ENDC}  /  {ConsoleColor.FAIL}{dead} dead{ConsoleColor.ENDC}")

def _build_payload(data, fbzx=None):
    payload = {
        "fvv":         "1",
        "pageHistory": "0",
        "fbzx":        fbzx or str(random.randint(-9999999999999999999, -1000000000000000000)),
    }
    for k, v in data.items():
        if isinstance(v, list):
            payload[k] = v
        else:
            payload[k] = v
    return payload

def _make_session(proxy=None):
    s = requests.Session()
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s

def _get_form_cookies(session, viewform_url, proxy=None):
    try:
        headers = {
            "User-Agent":      random.choice(USER_AGENTS),
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        session.get(viewform_url, headers=headers, timeout=CONFIG["timeout"], allow_redirects=True)
    except Exception:
        pass

def do_request(times, url, data, delay=0, show_output=True, referer_url=""):
    for _ in range(times):
        start   = time.time()
        status  = "FAILURE"
        code    = 0
        proxy   = get_proxy()
        session = _make_session(proxy)
        if referer_url:
            _get_form_cookies(session, referer_url, proxy)
        payload = _build_payload(data)
        try:
            r = session.post(
                url, data=payload,
                headers=get_submit_headers(referer_url),
                timeout=CONFIG["timeout"],
                allow_redirects=True,
            )
            code = r.status_code
            if code in (200, 201):
                status = "SUCCESS"
                with lock:
                    _successful[0] += 1
        except requests.exceptions.ProxyError:
            status = "PROXY_ERR"
        except requests.exceptions.Timeout:
            status = "TIMEOUT"
        except Exception:
            pass

        ms      = int((time.time() - start) * 1000)
        cool_id = f"FF-{generate_cool_id()}"
        color   = ConsoleColor.SUCCESS if status == "SUCCESS" else ConsoleColor.FAIL
        line    = f"  {cool_id}  {status:<10}  {ms:>5}ms  HTTP {code}"

        with lock:
            if status == "SUCCESS":
                log_success(line)
            else:
                log_fail(line)
            if show_output:
                print(color + line + ConsoleColor.ENDC)

        time.sleep(delay)

def spam_mode(answers, original_url, silent=False):
    reset_successful_requests()
    base         = original_url.split("?")[0].rstrip("/")
    viewform_url = base if base.endswith("/viewform") else base.replace("/formResponse", "") + "/viewform"
    base         = base.replace("/viewform", "")
    form_url     = base + "/formResponse"

    try:
        times = int(input(f"{ConsoleColor.HEADER}  How many submissions? {ConsoleColor.ENDC}").strip())
    except ValueError:
        print(f"{ConsoleColor.FAIL}  Invalid number.{ConsoleColor.ENDC}")
        return

    os.system('cls' if os.name == 'nt' else 'clear')
    C = ConsoleColor
    width = 68
    print(f"\n{C.OKCYAN}{'═'*width}{C.ENDC}")
    print(f"  {C.BOLD}{C.WARNING}FORMFORGE  ►  SPAM MODE ACTIVE{C.ENDC}")
    print(f"  {C.DIM}Target : {form_url}{C.ENDC}")
    print(f"  {C.DIM}Jobs   : {times}   Threads: {CONFIG['threads']}   Delay: {CONFIG['delay']}s{C.ENDC}")
    print(f"{C.OKCYAN}{'═'*width}{C.ENDC}\n")

    start        = time.time()
    thread_count = CONFIG["threads"]
    per_thread   = max(1, times // thread_count)
    threads      = []

    for _ in range(thread_count):
        t = threading.Thread(
            target=do_request,
            args=(per_thread, form_url, answers, CONFIG["delay"], not silent, viewform_url),
            daemon=True
        )
        threads.append(t)

    for t in threads: t.start()
    for t in threads: t.join()

    elapsed   = time.time() - start
    successes = get_successful_requests()
    print(f"\n{C.OKCYAN}{'═'*width}{C.ENDC}")
    print(f"  {C.BOLD}{C.OKGREEN}DONE{C.ENDC}  {successes}/{times} successful  |  {elapsed:.2f}s elapsed")
    log_info(f"Spam finished: {successes}/{times} successful in {elapsed:.2f}s")
    input(f"\n{C.OKCYAN}  Press Enter to return to menu...{C.ENDC}")
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading
import itertools
import string
import random
import time
import requests
from utils.logger import ConsoleColor, log_info, log_success, log_fail

CONFIG = {
    "delay":       0.35,
    "threads":     25,
    "use_proxies": False,
    "timeout":     20,
    "user_agent":  "random"
}

proxies      = []
proxy_cycle  = None
lock         = threading.Lock()
_successful  = [0]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

def get_successful_requests():
    return _successful[0]

def reset_successful_requests():
    _successful[0] = 0

def generate_cool_id():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(8))

def get_submit_headers(referer_url=""):
    ua = random.choice(USER_AGENTS) if CONFIG["user_agent"] == "random" else USER_AGENTS[0]
    return {
        "User-Agent":      ua,
        "Accept":          "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type":    "application/x-www-form-urlencoded",
        "Origin":          "https://docs.google.com",
        "Referer":         referer_url or "https://docs.google.com/forms/",
        "Connection":      "keep-alive",
        "Sec-Fetch-Dest":  "document",
        "Sec-Fetch-Mode":  "navigate",
        "Sec-Fetch-Site":  "same-origin",
    }

def get_random_headers():
    return get_submit_headers()

def get_proxy():
    global proxy_cycle
    if proxy_cycle and CONFIG["use_proxies"]:
        return next(proxy_cycle)
    return None

def load_proxies(filename=None):
    global proxies, proxy_cycle
    if filename is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filename = os.path.join(base, "data", "proxies.txt")
    try:
        with open(filename) as f:
            loaded = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        if loaded:
            proxies = loaded
            proxy_cycle = itertools.cycle(proxies)
            print(f"{ConsoleColor.OKGREEN}  {len(proxies)} proxies loaded from {filename}{ConsoleColor.ENDC}")
            log_info(f"Loaded {len(proxies)} proxies")
        else:
            print(f"{ConsoleColor.WARNING}  proxies.txt is empty.{ConsoleColor.ENDC}")
    except FileNotFoundError:
        print(f"{ConsoleColor.WARNING}  proxies.txt not found at {filename}{ConsoleColor.ENDC}")

def test_proxies():
    if not proxies:
        print(f"{ConsoleColor.FAIL}  No proxies loaded.{ConsoleColor.ENDC}")
        return
    print(f"\n{ConsoleColor.OKCYAN}  Testing {len(proxies)} proxies...{ConsoleColor.ENDC}")
    alive, dead = 0, 0
    for p in proxies:
        try:
            r = requests.get("https://api.ipify.org?format=json",
                             proxies={"http": p, "https": p}, timeout=8)
            if r.status_code == 200:
                print(f"  {ConsoleColor.OKGREEN}ALIVE{ConsoleColor.ENDC}  {p}  → {r.json().get('ip','?')}")
                alive += 1
            else:
                print(f"  {ConsoleColor.FAIL}DEAD {ConsoleColor.ENDC}  {p}")
                dead += 1
        except:
            print(f"  {ConsoleColor.FAIL}DEAD {ConsoleColor.ENDC}  {p}")
            dead += 1
    print(f"\n  Results: {ConsoleColor.OKGREEN}{alive} alive{ConsoleColor.ENDC}  /  {ConsoleColor.FAIL}{dead} dead{ConsoleColor.ENDC}")

def _build_payload(data, fbzx=None):
    payload = {
        "fvv":         "1",
        "pageHistory": "0",
        "fbzx":        fbzx or str(random.randint(-9999999999999999999, -1000000000000000000)),
    }
    for k, v in data.items():
        if isinstance(v, list):
            payload[k] = v
        else:
            payload[k] = v
    return payload

def _make_session(proxy=None):
    s = requests.Session()
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s

def _get_form_cookies(session, viewform_url, proxy=None):
    try:
        headers = {
            "User-Agent":      random.choice(USER_AGENTS),
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        session.get(viewform_url, headers=headers, timeout=CONFIG["timeout"], allow_redirects=True)
    except Exception:
        pass

def do_request(times, url, data, delay=0, show_output=True, referer_url=""):
    for _ in range(times):
        start   = time.time()
        status  = "FAILURE"
        code    = 0
        proxy   = get_proxy()
        session = _make_session(proxy)
        if referer_url:
            _get_form_cookies(session, referer_url, proxy)
        payload = _build_payload(data)
        try:
            r = session.post(
                url, data=payload,
                headers=get_submit_headers(referer_url),
                timeout=CONFIG["timeout"],
                allow_redirects=True,
            )
            code = r.status_code
            if code in (200, 201):
                status = "SUCCESS"
                with lock:
                    _successful[0] += 1
        except requests.exceptions.ProxyError:
            status = "PROXY_ERR"
        except requests.exceptions.Timeout:
            status = "TIMEOUT"
        except Exception:
            pass

        ms      = int((time.time() - start) * 1000)
        cool_id = f"FF-{generate_cool_id()}"
        color   = ConsoleColor.SUCCESS if status == "SUCCESS" else ConsoleColor.FAIL
        line    = f"  {cool_id}  {status:<10}  {ms:>5}ms  HTTP {code}"

        with lock:
            if status == "SUCCESS":
                log_success(line)
            else:
                log_fail(line)
            if show_output:
                print(color + line + ConsoleColor.ENDC)

        time.sleep(delay)

def spam_mode(answers, original_url, silent=False):
    reset_successful_requests()
    base         = original_url.split("?")[0].rstrip("/")
    viewform_url = base if base.endswith("/viewform") else base.replace("/formResponse", "") + "/viewform"
    base         = base.replace("/viewform", "")
    form_url     = base + "/formResponse"

    try:
        times = int(input(f"{ConsoleColor.HEADER}  How many submissions? {ConsoleColor.ENDC}").strip())
    except ValueError:
        print(f"{ConsoleColor.FAIL}  Invalid number.{ConsoleColor.ENDC}")
        return

    os.system('cls' if os.name == 'nt' else 'clear')
    C = ConsoleColor
    width = 68
    print(f"\n{C.OKCYAN}{'═'*width}{C.ENDC}")
    print(f"  {C.BOLD}{C.WARNING}FORMFORGE  ►  SPAM MODE ACTIVE{C.ENDC}")
    print(f"  {C.DIM}Target : {form_url}{C.ENDC}")
    print(f"  {C.DIM}Jobs   : {times}   Threads: {CONFIG['threads']}   Delay: {CONFIG['delay']}s{C.ENDC}")
    print(f"{C.OKCYAN}{'═'*width}{C.ENDC}\n")

    start        = time.time()
    thread_count = CONFIG["threads"]
    per_thread   = max(1, times // thread_count)
    threads      = []

    for _ in range(thread_count):
        t = threading.Thread(
            target=do_request,
            args=(per_thread, form_url, answers, CONFIG["delay"], not silent, viewform_url),
            daemon=True
        )
        threads.append(t)

    for t in threads: t.start()
    for t in threads: t.join()

    elapsed   = time.time() - start
    successes = get_successful_requests()
    print(f"\n{C.OKCYAN}{'═'*width}{C.ENDC}")
    print(f"  {C.BOLD}{C.OKGREEN}DONE{C.ENDC}  {successes}/{times} successful  |  {elapsed:.2f}s elapsed")
    log_info(f"Spam finished: {successes}/{times} successful in {elapsed:.2f}s")
    input(f"\n{C.OKCYAN}  Press Enter to return to menu...{C.ENDC}")
