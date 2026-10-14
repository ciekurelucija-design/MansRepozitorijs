---
id: CR-4
type: change-request
title: "Darbinieka reģistrācija un pieteikšanās"
status: DRAFT
priority: medium
reporter: "Reģistrācijas nodaļa (izdomāts)"
owner: "@<github-lietotājvārds>"
contract: "docs/openapi.yaml · POST /auth/register, POST /auth/login"
depends_on: []
exported: "<datums> · Ezermalas pieteikumu sistēma (simulācija)"
data_check: "<kas pārbaudīts pirms eksporta>"
---

# CR-4 · Darbinieka reģistrācija un pieteikšanās

> Noteikumi vienkāršoti mācību vajadzībām.

## Apraksts (description)

Darbiniekiem jāspēj izveidot kontu un pieteikties sistēmā, lai piekļūtu
iesniegumu apstrādei. Šobrīd sistēmā nav lietotāju kontu. Konta dati
jāsaglabā pastāvīgi, lai tie paliktu pieejami arī pēc sistēmas restartēšanas.

## Pieņemšanas kritēriji (acceptance criteria)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 1 | Reģistrācija ar derīgu e-pastu un paroli (≥ 8 rakstzīmes) | Konts izveidots, 201 |
| 2 | Reģistrācija ar jau reģistrētu e-pastu | 409, konts netiek dublēts |
| 3 | Reģistrācija ar nederīgu e-pastu | 400, `Error` |
| 4 | Reģistrācija ar paroli < 8 rakstzīmēm | 400, `Error` |
| 5 | Pieteikšanās ar pareizu e-pastu un paroli | 200, lietotājs pieteicies |
| 6 | Pieteikšanās ar nepareizu paroli | 401, vispārīgs ziņojums (neatklāj, vai e-pasts eksistē) |
| 7 | Pieteikšanās ar neeksistējošu e-pastu | 401, tāds pats ziņojums kā #6 |
| 8 | Parole datubāzē | Netiek glabāta atklātā tekstā (tikai jaucējvērtība) |
| 9 | Konts pēc servisa restartēšanas | Pieteikšanās joprojām izdodas |

## Precizējumi (clarifications)

| Jautājums | Atbilde | Kas atbildēja, kad |
|---|---|---|
| Kas drīkst reģistrēties: jebkurš vai tikai darbinieki ar iestādes e-pastu? | jebkurš|darbinieks |
| Kā pieteikšanās tiek uzturēta: sesijas sīkdatne vai žetons (token)? | sesijas sīkdatne| darbinieks|
| Vai vajag HTML formas, vai tikai API? | HTML formas|darbinieks |
| Kāda datubāze: SQLite pietiek mācību vajadzībām? | Jā, pietiek|darbinieks |

## Ārpus apjoma (out of scope)

- Paroles atjaunošana un e-pasta apstiprināšana
- Lomas un tiesības
- Divfaktoru autentifikācija
- Atteikšanās (logout) un konta dzēšana

## Komentāri (comments)

-