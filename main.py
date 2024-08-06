import requests
from concurrent.futures import ThreadPoolExecutor
import os
import threading
import time
import ctypes
import sys

RESET = "\033[0m"
BLUE = "\033[94m"
PINK = "\033[95m"
GREEN = "\033[92m"
RED = "\033[91m"

class ProxyFetcher:
    @staticmethod
    def fetch_proxies(url):
        try:
            res = requests.get(url)
            if res.status_code == 200:
                return res.text.splitlines()
            else:
                print(f"{RED}Error: Unable to fetch proxies from the URL. Status code: {res.status_code}{RESET}")
                exit(1)
        except requests.RequestException as e:
            print(f"{RED}Error: {e}{RESET}")
            exit(1)

class ProxyChecker:
    def __init__(self, num_threads):
        self.valid = set()
        self.invalid = set()
        self.lock = threading.Lock()
        self.start_time = None
        self.num_threads = num_threads

    def _check_proxy(self, p):
        start = time.time()
        try:
            res = requests.get('https://httpbin.org/ip', proxies={'http': p, 'https': p}, timeout=5)
            response_time = time.time() - start
            if res.status_code == 200:
                with self.lock:
                    self.valid.add((p, response_time))
                    self._save_proxy(p, response_time)
                return p, response_time, True
            else:
                with self.lock:
                    self.invalid.add(p)
                return p, response_time, False
        except requests.RequestException:
            response_time = time.time() - start
            with self.lock:
                self.invalid.add(p)
            return p, response_time, False

    def check_proxies(self, proxies, cb):
        self.valid.clear()
        self.invalid.clear()
        self.start_time = time.time()
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            futures = {executor.submit(self._check_proxy, p.strip()): p.strip() for p in proxies}
            for future in futures:
                p, response_time, result = future.result()
                cb(self.valid, self.invalid, self.calculate_rps(), time.time() - self.start_time)
        total_time = time.time() - self.start_time
        rps = len(self.valid) / total_time if total_time > 0 else 0
        cb(self.valid, self.invalid, rps, total_time)

    def calculate_rps(self):
        return len(self.valid) / (time.time() - self.start_time) if self.start_time else 0

    def _save_proxy(self, proxy, response_time):
        with open(os.path.join('valid', 'valid_proxies.txt'), 'a') as f:
            f.write(proxy.strip() + '\n')

class TerminalUpdater:
    def __init__(self):
        self.stop_update = threading.Event()
        self.update_thread = threading.Thread(target=self._update_terminal_title)
        self.num_valid = 0
        self.num_invalid = 0
        self.rps = 0
        self.total_time = 0

    def start_update_thread(self):
        self.update_thread.start()

    def stop_update_thread(self):
        self.stop_update.set()
        self.update_thread.join()

    def _update_terminal_title(self):
        while not self.stop_update.is_set():
            if self.num_valid is not None and self.num_invalid is not None and self.rps is not None and self.total_time is not None:
                title = (f"» @0xnyxo | ProxyChecker | Valid: {self.num_valid} | Invalid: {self.num_invalid} | RPS: {self.rps:.2f}")
                ctypes.windll.kernel32.SetConsoleTitleW(title)
            time.sleep(1)

    def update_stats(self, num_valid, num_invalid, rps, total_time):
        self.num_valid = num_valid
        self.num_invalid = num_invalid
        self.rps = rps
        self.total_time = total_time

class ResultsDisplayer:
    def __init__(self):
        self.terminal_updater = TerminalUpdater()
        self.previous_results = set()

    def start_display(self):
        self.terminal_updater.start_update_thread()

    def stop_display(self):
        self.terminal_updater.stop_update_thread()

    def display_results(self, valid, invalid, rps, total_time):
        num_valid = len(valid)
        num_invalid = len(invalid)
        duration = f"{total_time:.3f}s"
        self.terminal_updater.update_stats(num_valid, num_invalid, rps, total_time)
        new_results = []
        for p, response_time in valid:
            if p not in self.previous_results:
                self.previous_results.add(p)
                new_results.append(f"[{PINK}{BLUE}{time.strftime('%H:%M')}{RESET}] {RESET}{p.strip()} [{PINK}{BLUE}{response_time:.3f}s{RESET}]{RESET}")
        self._print_results(new_results)

    def _print_results(self, new_results):
        for line in new_results:
            print(f"    {line}")
        sys.stdout.flush()

class ProxyCheckerApp:
    @staticmethod
    def run():
        num_threads = int(input("    ↪ Threads: "))
        proxy_url = 'https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&proxy_format=protocolipport&format=text&timeout=30000'
        proxies = ProxyFetcher.fetch_proxies(proxy_url)
        proxy_checker = ProxyChecker(num_threads)
        results_displayer = ResultsDisplayer()
        ProxyCheckerApp.print_initial_display(num_threads)
        print(f"{PINK}Starting proxy checks...{RESET}")
        time.sleep(2)
        sys.stdout.write("\033[F")
        sys.stdout.flush()
        results_displayer.start_display()
        proxy_checker.check_proxies(proxies, results_displayer.display_results)
        results_displayer.stop_display()

    @staticmethod
    def print_initial_display(num_threads):
        os.system('cls' if os.name == 'nt' else 'clear')
        logo = f"""
{BLUE}      _  _  _  _  _  _  _____
     ( \( )( \/ )( \/ )(  _  )
      )  (  \  /  )  (  )(_)( 
     (_)\_) (__) (_/\_)(_____)
{RESET}
        """
        print(f"{logo}{PINK}  ↪ Threads: {num_threads}{RESET}\n")

if __name__ == "__main__":
    ProxyCheckerApp.run()
