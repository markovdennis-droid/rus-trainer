# -*- coding: utf-8 -*-
"""
Извлечение языкового инвентаря из тематического архива заданий.

Берём ТОЛЬКО факты о языке: нормативное ударение, пары паронимов,
нормативные формы слова. Формулировки заданий, тексты и пояснения
не извлекаются и в банк не попадают — см. bank/README.md.

Запуск:  python3 -I tools/extract_inventory.py <путь к папке 01_Текущий_формат>
"""
import json
import re
import sys
from pathlib import Path

import pypdf

OUT = Path(__file__).resolve().parent.parent / "bank" / "inventory"
VOWELS = "АЕЁИОУЫЭЮЯ"


def read_pdf(path: Path) -> str:
    return "\n".join((p.extract_text() or "") for p in pypdf.PdfReader(str(path)).pages)


def find_pdf(base: Path, prefix: str) -> Path:
    for d in sorted(base.iterdir()):
        if d.is_dir() and d.name.startswith(prefix):
            pdf = next(d.glob("*.pdf"), None)
            if pdf:
                return pdf
    raise FileNotFoundError(f"не найдена папка {prefix}* в {base}")


def stress(base: Path):
    """Линия 4. Ударение берём только у вариантов, подтверждённых ответом.

    В условии задания заглавной буквой помечены и верные, и намеренно
    неверные ударения. Различить их можно лишь по ключу: «Ответ: 24»
    означает, что верны варианты 2 и 4.
    """
    text = read_pdf(find_pdf(base, "04_"))
    confirmed, parsed = {}, 0
    for block in re.split(r"Тип 4 № \d+", text)[1:]:
        body = block.split("Пояснение")[0]
        opts = dict(re.findall(r"^\s*([1-5])\)\s*([А-Яа-яЁё]+)\s*$", body, re.M))
        key = re.search(r"Ответ:\s*([1-5]{1,5})", body)
        if not key or len(opts) < 4:
            continue
        parsed += 1
        right = set(key.group(1))
        for num, word in opts.items():
            if num not in right:
                continue
            caps = [i for i, c in enumerate(word) if c.isupper()]
            if len(caps) != 1 or word[caps[0]] not in VOWELS:
                continue
            confirmed[word.lower()] = caps[0]
    rows = [
        {"word": w, "stress": p, "marked": w[:p] + w[p].upper() + w[p + 1:]}
        for w, p in sorted(confirmed.items())
    ]
    return rows, f"линия 4: {len(rows)} слов, разобрано заданий {parsed}"


def paronyms(base: Path):
    """Линия 5. Верная форма — из ключа; неверная — однокоренная ей из условия."""
    text = read_pdf(find_pdf(base, "05_"))
    pairs, inventory, missed = {}, set(), 0
    for block in re.split(r"Тип 5 № \d+", text)[1:]:
        body = block.split("Пояснение")[0]
        caps = [
            c.lower()
            for c in re.findall(r"\b([А-ЯЁ]{4,})\b", body)
            if c not in ("НЕВЕРНО", "ЗАПИШИТЕ", "ОТВЕТ")
        ]
        inventory.update(caps)
        key = re.search(r"Ответ:\s*([а-яё]{4,})", block)
        if not key:
            continue
        correct = key.group(1)
        inventory.add(correct)
        same_root = [
            c for c in caps
            if c != correct and (c[:4] == correct[:4] or c[:3] == correct[:3])
        ]
        if same_root:
            pairs[max(same_root, key=len)] = correct
        else:
            missed += 1
    data = {
        "pairs": [{"wrong": k, "correct": v} for k, v in sorted(pairs.items())],
        "inventory": sorted(inventory),
    }
    return data, (f"линия 5: {len(pairs)} пар, словарь {len(inventory)} слов, "
                  f"не сопоставлено {missed}")


def forms(base: Path):
    """Линия 7. Нормативная форма слова — это и есть ключ задания."""
    text = read_pdf(find_pdf(base, "07_"))
    found = {}
    for block in re.split(r"Тип 7 № \d+", text)[1:]:
        key = re.search(r"Ответ:\s*([а-яё]{3,}(?:\s+[а-яё]+)?)", block)
        if not key:
            continue
        wrong = re.search(r"([А-ЯЁ]{3,})\b[^\n]{0,80}?(?:неверн|ошибк)", block)
        found[key.group(1).strip()] = wrong.group(1).lower() if wrong else None
    rows = [{"correct": k, "wrong": v} for k, v in sorted(found.items())]
    return rows, f"линия 7: {len(rows)} форм"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip())
        return 2
    base = Path(sys.argv[1]).expanduser()
    if not base.is_dir():
        print(f"нет такой папки: {base}")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("stress", stress), ("paronyms", paronyms), ("forms", forms)):
        data, note = fn(base)
        (OUT / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(note, "->", (OUT / f"{name}.json").name)
    print("\nИнвентарь требует вычитки: извлечение из PDF местами склеивает слова.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
