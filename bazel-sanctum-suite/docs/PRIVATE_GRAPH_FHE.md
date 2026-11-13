# Prywatny agregat grafu: Microsoft SEAL, PKCS#11 i Apache AGE

To opcjonalny, eksperymentalny przepływ do zapisania grafu sprawy w Apache AGE
z indywidualnie zaszyfrowanymi ocenami całkowitymi i zaszyfrowaną sumą.
Nie zastępuje analizy ryzyka, nie weryfikuje prawdziwości danych ani nie
zapewnia zgodności regulacyjnej.

## Granice zaufania

- **FHE:** Microsoft SEAL BFV szyfruje każdą ocenę kluczem publicznym i
  homomorficznie dodaje szyfrogramy. Klucz prywatny BFV pozostaje osobnym
  plikiem po stronie klienta. Nie jest wysyłany do AGE ani HSM.
- **HSM:** PKCS#11 używa oddzielnego klucza RSA w HSM do podpisu kanonicznego
  manifestu (`CKM_SHA256_RSA_PKCS`). HSM nie wykonuje operacji BFV i nie
  sprawdza znaczenia grafu ani ocen.
- **Apache AGE:** węzły, relacje, identyfikatory oraz ich zwykłe właściwości są
  przechowywane w czytelnej postaci. Właściwość `encrypted_score` zawiera
  szyfrogram BFV zakodowany Base64. Nie jest to szyfrowanie całego grafu ani
  ochrony metadanych.
- **Weryfikacja:** `privacy-graph-verify` sprawdza podpis względem przekazanego
  certyfikatu, zgodność odcisku certyfikatu w manifeście i SHA-256
  szyfrogramu sumy. Operator musi osobno ustanowić zaufanie do certyfikatu
  HSM i jego łańcucha; samo podanie certyfikatu nie tworzy zaufanego łańcucha.

## Instalacja i wymagania

Zainstaluj dodatkowe zależności w środowisku CLI:

```sh
python -m pip install ".[privacy-graph]"
```

Wymagane są dostępna biblioteka Microsoft SEAL dla platformy, działający
PostgreSQL z Apache AGE i biblioteka PKCS#11 dostawcy HSM. Użytkownik bazy
musi móc załadować rozszerzenie AGE oraz zapisywać w wybranym grafie. Dla
połączeń zdalnych Sanctum wymaga `sslmode=verify-full` i istniejącego
`sslrootcert`. Pliki sekretów powinny być dostępne wyłącznie dla operatora
polecenia; PIN HSM przekazuje się plikiem, nigdy argumentem procesu.

## Dane wejściowe

Graf jest obiektem JSON z identyfikatorem sprawy i tablicami `nodes` oraz
`edges`. Identyfikatory węzłów muszą być unikalne. Każda krawędź wskazuje
istniejące `source`, `target` oraz identyfikator `relation`.

```json
{
  "case_id": "case-2026-001",
  "nodes": [
    {"id": "address:chain:alice", "kind": "address"},
    {"id": "address:chain:bob", "kind": "address"}
  ],
  "edges": [
    {
      "source": "address:chain:alice",
      "target": "address:chain:bob",
      "relation": "OBSERVED_LINK"
    }
  ]
}
```

Oceny przekazuje się osobnym plikiem JSON jako tablicę unikalnych par
`node_id`/`score`:

```json
[
  {"node_id": "address:chain:alice", "score": 47},
  {"node_id": "address:chain:bob", "score": 18}
]
```

Dozwolone są maksymalnie 5 000 węzłów, 10 000 krawędzi oraz 5 000 ocen.
Każda ocena musi być liczbą całkowitą od 0 do 1 000. Zakres maksymalnej sumy
to 5 000 000 i mieści się w skonfigurowanym module plaintext BFV. Wartości
niecałkowite, wartości boolean oraz oceny spoza grafu są odrzucane.

## Przepływ CLI

1. Klient generuje zestaw parametrów i kluczy BFV. Klucz prywatny należy
   zachować po stronie klienta, w chronionym magazynie lub na nośniku
   kontrolowanym przez organizację:

   ```sh
   sanctum fhe-keygen \
     --public-key-file fhe-public.seal \
     --private-key-file fhe-private.seal \
     --parameters-file fhe-parameters.json
   ```

2. Przekaż **klucz publiczny**, parametry, graf i wejściowe oceny do
   operatora procesu importu. Operator konfiguruje AGE, HSM, moduł PKCS#11,
   identyfikator tokena i klucza podpisującego oraz chronione pliki DSN/PIN.
   Import szyfruje oceny, zapisuje graf i szyfrogramy, a następnie tworzy
   podpisany bundle:

   ```sh
   sanctum privacy-graph-import \
     --graph-file graph.json \
     --scores-file scores.json \
     --case-id case-2026-001 \
     --public-key-file fhe-public.seal \
     --parameters-file fhe-parameters.json \
     --dsn-file age-dsn \
     --graph-name sanctum \
     --pkcs11-module /path/to/vendor-pkcs11.so \
     --token-label sanctum \
     --signing-key-label graph-manifest \
     --pin-file hsm-pin \
     --certificate-file hsm-certificate.pem \
     --output-directory private-graph-bundle
   ```

3. Odbiorca weryfikuje podpis manifestu oraz digest sumy, dostarczając
   certyfikat zaufany według własnej procedury:

   ```sh
   sanctum privacy-graph-verify \
     --manifest-file private-graph-bundle/manifest.json \
     --signature-file private-graph-bundle/manifest.sig \
     --ciphertext-file private-graph-bundle/aggregate.seal \
     --certificate-file hsm-certificate.pem
   ```

4. Tylko klient posiadający pasujący klucz prywatny odszyfrowuje sumę:

   ```sh
   sanctum fhe-decrypt-sum \
     --parameters-file fhe-parameters.json \
     --private-key-file fhe-private.seal \
     --ciphertext-file private-graph-bundle/aggregate.seal
   ```

Nie kopiuj klucza prywatnego ani do hosta AGE, ani do HSM używanego do
podpisywania. Ogranicz dostęp do pliku ocen, DSN, PIN-u, manifestu oraz
bundle'a zgodnie z modelem zagrożeń organizacji. Nie umieszczaj sekretów
w argumentach poleceń, repozytorium, logach ani artefaktach CI.

## Ograniczenia i obsługa awarii

- Schemat BFV obsługuje w tym przepływie dodawanie ograniczonych liczb
  całkowitych, nie dowolne obliczenia na grafie. Odszyfrowana suma jest
  wynikiem arytmetycznym dla danych dostarczonych przez operatora, a nie
  oceną Sanctum, werdyktem ryzyka ani dowodem poprawności wejść.
- Manifest wiąże digest oryginalnego wejścia grafowego i szyfrogramu sumy.
  Weryfikacja nie pobiera ani nie poświadcza aktualnego stanu AGE, wszystkich
  węzłów/krawędzi lub indywidualnych szyfrogramów.
- Podpis dowodzi, że manifest podpisał odpowiadający podanemu certyfikatowi
  klucz. Nie ustanawia zaufania do certyfikatu, nie potwierdza statusu
  certyfikatu i nie dowodzi poprawności grafu.
- Zapis do bazy i publikacja lokalnego bundle'a nie są jedną transakcją
  rozproszoną. Jeśli zapis bundle'a nie powiedzie się po imporcie grafu,
  AGE może zawierać dane bez odpowiadającego lokalnego bundle'a. Operator
  powinien sprawdzić stan bazy i wykonać uzgodnioną procedurę odzyskiwania.
- Testy automatyczne używają rzeczywistego Microsoft SEAL oraz mocków AGE i
  PKCS#11. Nie dowodzą zgodności z konkretną wersją serwera AGE ani
  zachowania fizycznego HSM; przed użyciem należy przeprowadzić test
  akceptacyjny na docelowym serwerze i urządzeniu.
