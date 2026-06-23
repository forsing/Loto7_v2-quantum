# Quantum Loto7 v2 — Loto 7/39 (GHQ)


- Podrazumevani CSV: `/data/loto7hh_4636_k49.csv` (kolone `Num1`..`Num7`)
- Lutrija: `loto-739`
- Seed: `39`
- Podrazumevano: **1 tiket** (jedna kombinacija 7 brojeva)


## Okruženje

venv:


## Pokretanje

```bash
cd 
python3 cli.py list
python3 cli.py audit --date 2026-06-24
python3 cli.py predict --date 2026-06-24
```

Izlaz: `prediction.json`, `prediction.md`, `audit.json`, `audit.md`.




========================



predict — ne koristi 15 modela.
Koristi samo fiksni number_scores iz math_model.py (mešavina: ukupna frekvencija, recent, EWMA, gap parovi). To je u kodu isto što i model legacy_weighted.

audit — koristi svih 15 u walk-forward testu, pa bira jedan pobednik za tiket:

uniform
frequency_all
recent_frequency
ewma_recency
bayesian_dirichlet
gap_overdue
pair_centrality
anti_frequency
anti_recent
drift_recent_vs_old
stability
hybrid_gap_pair
hybrid_recency_pair
ensemble
legacy_weighted

Za generisanje kombinacije u audit ide samo best_model (onaj sa najboljim walk-forward rezultatom). 
Koji je to — piše u audit.md / audit.json 
pod selected_generation_model ili best_model.




=========================



Za svaki broj 1–39 izračunat skor iz istorije (number_scores):

ukupna frekvencija u CSV-u
frekvencija u poslednjih ~52 kola
eksponencijalno ponderisana „svežina“
razmak od poslednjeg pojavljivanja (gap)
učešće u parovima
optimize_tickets (1 kolona = 1 tiket):

na osnovu tih skorova generiše hiljade kandidata 
(7 brojeva) — teži brojevima koji su „jači“ po CSV-u
rangira ih (poklapanje sa istorijom, parovi/trojke, pokrivanje)
uzme najbolji jedan → [8, x, 23, y, 32, z, 39]


predict vs audit
predict — brže: skorovi + optimizator → 1 tiket.
audit — pun test (randomness, walk-forward, 15 modela) pa tek onda tiket.




=============================




python cli.py predict --date 2026-06-24

# Loto Serbia 7/39 - Quantum Lotto7

Draw date: `2026-06-24`
Columns: `1`

## Human-readable expectation

- Main jackpot chance for this ticket set is roughly `1 / 15.380.937`.
- Random baseline for at least one 2+ main hit: `36.88%`.
- Random baseline for at least one 3+ main hit: `9.38%`.
- Historical best-main average on the backtest window: `1.45`.
- Historical 2+ rate on the generated set: `46.50%`.
- Historical 3+ rate on the generated set: `17.20%`.
- Union coverage: `7/39`.
- Max pairwise overlap: `0`.

## Local qc25 Simulator

- Profile: `long`
- Backend: `aer_simulator`
- Qubits/layers/batch/shots: `25` / `4` / `4` / `8192`
- Repeat jobs: `1`
- Total shots: `32768`
- Encode values (pos 1–5): `[5, 10, 15, 20, 25]`
- Top quantum combo: `[1, x, 7, y, 22, z, 13]` (p=0.0015)
Lokalni Aer simulator (qc25, 5×5 kubita). Kolo ne „razume” loto — audit/backtest je sloj razumevanja.

## Tickets

01. main [8, x, 23, y, 31, z, 38]


 prediction.json
 prediction.md




================================




Puna (bez skraćivanja):

python cli.py audit --date 2026-06-24


Brža (bez tri stvari):

python cli.py audit --date 2026-06-24 --quantum-profile standard --nested-test-draws 10 --null-trials 100


=====================


Na mom setupu (M1, ~4638 izvlačenja, podrazumevani audit + kvant long):

Faza	Otprilike
Kalibracija (500 null)
2–5 min
Walk-forward (15 modela)
5–15 min
Nested backtest (52 testa)
20–60 min ← najsporije
Kvant (qc25, ~33k shots)
2–10 min
Tiket + backtest
1–3 min
Ukupno: ~30–90 min, ponekad do ~2 h ako je mašina opterećena.

Nema progress bara — izgleda kao da „visi”, a radi nested deo.

Brže:

python cli.py audit --date 2026-06-24 --quantum-profile standard --nested-test-draws 10 --null-trials 100
To obično padne na ~10–20 min.


U „brzoj” komandi skratio sam samo ovo (ostalo audit radi isto):

Flag	Podrazumevano	Skraćeno	Šta gubiš
--quantum-profile standard
long
manje slojeva / batch / shots
grublja kvantna distribucija, manje stabilan seed
--nested-test-draws 10
52
10 poslednjih test izvlačenja
slabija provera „da li tiket radi out-of-sample”
--null-trials 100
500
100 simulacija
manje pouzdane p-vrednosti u kalibraciji
Nisam skratio:

walk-forward na svih ~4638 izvlačenja (15 modela)
izbor best_model
generisanje tiketa
glavni randomness audit

Zato brza verzija i dalje može 20+ min — najveći deo je i dalje walk-forward na celoj istoriji.



Puna (bez skraćivanja):
python cli.py audit --date 2026-06-24



Brža (gore tri stvari):
python cli.py audit --date 2026-06-24 --quantum-profile standard --nested-test-draws 10 --null-trials 100


=====================================


Alat za Loto 7/39 (CSV Num1..Num7, seed 39, podrazumevano 1 tiket). Dve komande:

predict — brzo: jedan fiksni model skorova → optimizator → tiket.
audit — isto za tiket, ali pre toga pun test (randomness, walk-forward 15 modela, nested backtest).

Tok
CSV → skor po broju 1–39 → (qc25 Aer, osim --no-quantum) → bitovi mešaju RNG seed
     → ~6000 kandidata → rangiranje → 1 kombinacija → prediction.json/md ili audit.json/md
predict vs audit (bitna razlika)
predict	audit
Skor brojeva
uvek number_scores (= legacy_weighted)
pobednik od 15 modela iz walk-forward testa
Testovi
kratak backtest na kraju
randomness, fingerprint, walk-forward, nested backtest
Brzina
brže
sporije
predict ne bira model — uvek ista mešavina: ukupna frekvencija, recent (~52 kola), EWMA, gap, parovi.

Slojevi (šta rade, bez ocene)
number_scores / 15 modela — vektor težina za brojeve 1–39 iz istorije (frekvencija, recent, gap, parovi, Bajes, anti-, drift, hibridi, ensemble…). Audit ih poredi walk-forward i uzme najbolji po prosečnim pogocima.

optimize_tickets — generiše ~6000 kombinacija, rangira candidate_objective: zbir skorova brojeva + blaga struktura (parnost, raspon, uzastopni) + koliko bi kombinacija „pogodila“ u poslednjih ~157 kola istorije.

Kvantni qc25 — lokalni Aer, 5×5 kubita, enkoduje poslednje kolo iz CSV, QCBM kol, 6. i 7. broj izvedeni iz bitstringa. Rezultat merenja ne bira brojeve direktno — XOR-uje seed za RNG u optimizatoru. --no-quantum ga isključuje.

Randomness audit — chi-square frekvencija, gapovi, lift parova/trojki, fingerprint, null simulacije — pita da li CSV odstupa od uniformnog.

Validacija — walk-forward po modelima; nested backtest za ceo pipeline tiketa.

