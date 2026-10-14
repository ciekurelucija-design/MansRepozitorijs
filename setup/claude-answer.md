# Explain what make test does

`make test` palaiž `Makefile` mērķi `test`, kas izpilda komandu:

```bash
pytest -q
```

- `pytest` atrod un palaiž visus testus mapē `tests/` (failus `test_*.py`).
- `-q` (quiet) saīsina izvadi: katram testam punkts, beigās kopsavilkums,
  piemēram, `2 passed`.
- Šobrīd tiek palaisti smoke testi `tests/test_smoke.py`:
  - `test_openapi_document_can_be_loaded` pārbauda, ka `docs/openapi.yaml`
    ir nolasāms YAML, OpenAPI versija ir 3.x un ir definēti ceļi (`paths`);
  - `test_participant_files_are_present` pārbauda, ka repozitorijā ir
    obligātie faili (`CLAUDE.md`, `Makefile`, `tracker/CR-2.md` u. c.).
- Ja visi testi iziet, komanda beidzas ar kodu 0. Ja kāds tests neiztur,
  `pytest` parāda kļūdu, un `make` beidzas ar kļūdas kodu.

`make test` nepārbauda kursa līguma noteikumus. Tam ir `make lint-contract`.
