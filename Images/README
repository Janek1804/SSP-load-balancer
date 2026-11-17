# Obrazy Docker klienta i serwera

## 1. Struktura katalogu Images

```text
Images
├── client/
│   ├── Dockerfile        # obraz klienta; bash do współpracy z Containernet
│   ├── requirements.txt  # aiohttp
│   └── load.py           # asynchroniczny generator HTTP/HTTPS
├── server/
│   ├── Dockerfile        # obraz serwera
│   ├── requirements.txt  # gunicorn, flask
│   ├── start.sh          # uruchamia Flaska; obsługuje certyfikat TLS
│   └── flask_app.py      # /health, /work, /stats
├── topology/
│   └── containernet_example.py
├── certs/                 # certyfikaty lokalne (poza repo)
├── results/               # logi CSV (poza repo)
└── compose.yaml           # test obu obrazów bez SDN
```

## 2. Wstęp

- **Image** zawiera jedynie runtime, narzędzia (`bash`, `ip`, `ping`, `curl`) i kod
  aplikacji. Nie wbudowuje limitów CPU/RAM ani adresu IP.
- **Uruchomiony kontener** ma limity cgroups (`cpu_quota`, `mem_limit`), nadane przez
  Docker/Containernet, i zmienne środowiskowe symulujące profil pracy.
- **Łącze w Containernet** ma `bw`, `delay` i opcjonalnie `loss` z `TCLink`.

### 3. Parametry środowiskowe serwera

| Zmienna | Domyślnie | Znaczenie |
|---|---:|---|
| `SERVER_ID` | hostname | ID zwracane przez `X-Server-Id` |
| `SERVER_PORT` | 8080 | Port nasłuchu HTTP lub HTTPS |
| `WORKERS` | 2 | Liczba procesów Gunicorn |
| `SERVER_TIMEOUT` | 60 | Timeout workera (sekundy) |
| `WORK_CPU_MS` | 20 | Czas procesora na żądanie w milisekundach |
| `WORK_MEM_MB` | 0 | Pamięć przydzielana na żądanie (MiB) |
| `WORK_IO_KB` | 0 | Zapis dyskowy na żądanie (KiB) |
| `WORK_SLEEP_MS` | 0 | Sztuczna opóźnienie aplikacji (ms) |
| `WORK_RESPONSE_KB` | 0 | Dodatkowa wielkość odpowiedzi (KiB) |
| `LOG_ACCESS` | 0 | `1` logi Gunicorna |
| `TLS_CERT_FILE` | brak | Ścieżka do certyfikatu PEM (w kontenerze) |
| `TLS_KEY_FILE` | brak | Ścieżka do klucza PEM (w kontenerze) |
| `DATA_DIR` | /data | Katalog plików dla workload I/O |

Dla `/work` profil można też zmienić *w konkretnym żądaniu*, bez restartu:
`/work?cpu_ms=40&mem_mb=8&io_kb=128&sleep_ms=10&response_kb=4`.
Limity bezpieczeństwa: do 30 s CPU i sleep, 512 MiB RAM, 128 MiB I/O, 1 MiB
odpowiedzi oraz 16 MiB body na żądanie.

### 4. Endpointy

- `GET /health` — sprawdzenie działania.
- `GET /stats` — best-effort odczyt cgroups v2 lub v1 (CPU quota, zużycie CPU,
  pamięć). `cpu_usage_usec` jest wartością narastającą: do szacowania procentu CPU
  oblicz przyrost między odczytami; `memory_current_bytes` jest chwilowe.
- `GET /work` i `POST /work` — żądanie pracy; wynik JSON z `server_id`,
  `processing_ms` i parametrami profilu. Każda odpowiedź ma `X-Server-Id`.

## 5. Budowanie obrazów

W katalogu `Images`:

```bash
docker build -t sdn-server:1.0 -f ./server/Dockerfile.server ./server
docker build -t sdn-client:1.0 -f ./client/Dockerfile.client ./client
docker images
```

### 6. Szybki lokalny test (bez Ryu i Containernet)

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8081/health
curl http://localhost:8082/stats
docker compose exec client python /app/load.py \
  --url 'http://server1:8080/work' --duration 10 --rps 30 \
  --concurrency 20 --output /results/server1.csv \
  --summary /results/server1.json
docker compose exec client python /app/load.py \
  --url 'http://server2:8080/work' --duration 10 --rps 30 \
  --concurrency 20 --output /results/server2.csv \
  --summary /results/server2.json
docker compose down
```

Wyniki zapisywane są w folderze `./results/`. `--rps 30` jest *celem*, a nie gwarancją
uzyskania 30 RPS: gdy serwer nie nadąża, ograniczeniem są `--concurrency`,
timeout i zasoby. Powolna instancja powinna wykazywać większe opóźnienia
lub niższą przepustowość, zwłaszcza przy większym obciążeniu. Domyślnie
klient zapisuje CSV i wypisuje podsumowanie p50/p95/p99 dla odpowiedzi 2xx.
Zwraca kod 1, jeśli wystąpi jakikolwiek błąd (nawet dla pojedyńczego żądania) lub nie zostaną wykonane żądania.

### 7. Klient - opcje

```text
--url           URL serwera albo VIP, http:// lub https://
--duration      czas generowania nowych żądań [s]
--rps           żądania/s (0 = bez limitu)
--concurrency   maksymalna liczba aktywnych żądań
--timeout       timeout każdego żądania [s]
--method        GET lub POST
--body-kb       rozmiar payload POST [KiB]
--insecure      bez weryfikacji TLS, wyłącznie LAB
--output        wynik CSV (pusta ścieżka wyłącza zapis)
--summary       opcjonalne podsumowanie JSON
```

### Dodanie klienta i serwera do topologii

```python

results_dir = Path(__file__).resolve().parents[1] / 'results'
results_dir.mkdir(parents=True, exist_ok=True)

client = net.addDocker('cli1', dimage='sdn-client:1.0',
                               ip='10.0.0.10/24', dcmd='/bin/bash',
                               volumes=[f'{results_dir}:/results:rw'])

fast = net.addDocker('srv1', dimage='sdn-server:1.0',
                     ip='10.0.0.11/24',
                     cpu_period=100000, cpu_quota=200000,
                     mem_limit='1g', memswap_limit='1g',
                     environment={'SERVER_ID': 'srv1', 'WORKERS': '2',
                                  'WORK_CPU_MS': '20', 'SERVER_PORT': '8080'})

slow = net.addDocker('srv2', dimage='sdn-server:1.0',
                     ip='10.0.0.12/24',
                     cpu_period=100000, cpu_quota=50000,
                     mem_limit='256m', memswap_limit='256m',
                     environment={'SERVER_ID': 'srv2', 'WORKERS': '2',
                                  'WORK_CPU_MS': '20', 'SERVER_PORT': '8080'})

net.addLink(client, sw, cls=TCLink, bw=100, delay='1ms')
net.addLink(fast, sw, cls=TCLink, bw=100, delay='5ms')
net.addLink(slow, sw, cls=TCLink, bw=20, delay='40ms')

net.start()
fast.start()
slow.start()

```

- Klient (cli1) 
- Serwer srv1 - wydajniejszy serwer z limitem 2 CPU i 1 GB RAM.
- Serwer srv2 - słabszy serwer z limitem 0,5 CPU i 256 MB RAM.

Oba serwery korzystają z tego samego obrazu Docker i mają identyczną konfigurację aplikacji (WORKERS=2, WORK_CPU_MS=20). Różnią się przydzielonymi zasobami oraz parametrami łączy sieciowych.

Za pomocą TCLink definiowana jest przepustowość (bw w Mb/s) oraz opóźnienie (delay) połączeń z przełącznikiem Open vSwitch.

Na końcu net.start() uruchamia topologię sieciową, a fast.start() i slow.start() uruchamiają aplikacje HTTP na serwerach.
