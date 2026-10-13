# -*- coding: utf-8 -*-
"""
Валидатор варианта по матрице КИМ.

Проверяет, что вариант собран по спецификации: все 27 линий на месте,
тип ответа совпадает с матрицей, ключи непротиворечивы, баллы сходятся
в 50, тексты привязаны к нужным заданиям.

Запуск:  python3 -I tools/validate_variant.py bank/variants/v1.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# порядок записи символов не имеет значения в этих линиях (демоверсия 2027)
UNORDERED = {2, 3, 4, *range(9, 22), 23, 24, 26}
PARTIAL = {8, 22}            # 2 балла, частичный балл за 1–2 неверные позиции
ESSAY_MIN_WORDS = 150


def blank(value: str) -> str:
    """Нормализация под бланк: без пробелов и знаков."""
    return re.sub(r"[^a-zа-я0-9]", "", str(value).lower().replace("ё", "е"))


def check(variant_path: Path) -> int:
    spec = {r["no"]: r for r in json.loads((ROOT / "bank" / "spec.json").read_text("utf-8"))}
    v = json.loads(variant_path.read_text("utf-8"))
    tasks = {t["no"]: t for t in v["tasks"]}
    errors, warnings = [], []

    missing = sorted(set(range(1, 28)) - set(tasks))
    if missing:
        errors.append(f"нет заданий: {missing}")

    total = 0
    for no in sorted(tasks):
        t, s = tasks[no], spec.get(no)
        if not s:
            errors.append(f"{no}: нет в матрице")
            continue
        total += s["max"]
        typ = s["type"]

        if typ == "essay":
            if not t.get("problem"):
                errors.append(f"{no}: не сформулирована проблема")
            if not t.get("author_position"):
                warnings.append(f"{no}: не указана позиция автора (нужна для проверки К1)")
            continue

        keys = t.get("key")
        if not keys:
            errors.append(f"{no}: нет ключа")
            continue

        for k in keys:
            nk = blank(k)
            if not nk:
                errors.append(f"{no}: пустой ключ")
            elif typ == "word":
                if not re.fullmatch(r"[а-я]+", nk):
                    errors.append(f"{no}: ключ «{k}» не слово, а матрица ждёт слово")
            elif not re.fullmatch(r"[0-9]+", nk):
                errors.append(f"{no}: ключ «{k}» не цифры, а матрица ждёт цифры")

        # соответствие (8, 22): длина ключа = числу позиций слева
        if no in PARTIAL:
            left = t.get("left") or []
            if len(left) != len(blank(keys[0])):
                errors.append(
                    f"{no}: позиций слева {len(left)}, а в ключе {len(blank(keys[0]))} символов")
            right = t.get("right") or []
            for ch in blank(keys[0]):
                if not (1 <= int(ch) <= len(right)):
                    errors.append(f"{no}: ключ ссылается на вариант {ch}, которого нет в списке")

        # цифровые ключи не должны указывать на несуществующий вариант
        if typ == "digits" and t.get("opts") and t.get("match") != "exact":
            for ch in blank(keys[0]):
                if not (1 <= int(ch) <= len(t["opts"])):
                    errors.append(f"{no}: ключ ссылается на вариант {ch}, которого нет")

        # Ответ-одиночный номер предложения нельзя сверять без учёта порядка:
        # «17» и «71» при сортировке совпадут. Ловим формулировки в единственном числе.
        single = re.search(r"номер\s+(?:этого|данного)?\s*предложения", t.get("stem", ""))
        if single and t.get("match") != "exact" and len(blank(keys[0])) > 1:
            errors.append(
                f'{no}: ответ — один номер предложения («{keys[0]}»), нужен "match": "exact", '
                f"иначе зачтётся перевёрнутый ответ")

        if not t.get("stem"):
            errors.append(f"{no}: нет формулировки")

    # тексты
    for tid, tx in v.get("texts", {}).items():
        for no in tx.get("for", []):
            if tasks.get(no, {}).get("text") != tid:
                errors.append(f'текст {tid} заявлен для задания {no}, но задание на него не ссылается')
        n = len(tx.get("sentences", []))
        for no in tx.get("for", []):
            for m in re.finditer(r"предложени\w*\s+(\d+)", tasks.get(no, {}).get("stem", "")):
                if int(m.group(1)) > n:
                    errors.append(f"{no}: ссылка на предложение {m.group(1)}, а в тексте {tasks[no]['text']} их {n}")

    part1 = sum(spec[n]["max"] for n in range(1, 27))
    print(f"заданий: {len(tasks)}/27   часть 1: {part1}   часть 2: {spec[27]['max']}   итого: {total}")
    if total != 50 or part1 != 28:
        errors.append(f"баллы не сходятся: ожидается 28 + 22 = 50, получено {part1} + {spec[27]['max']} = {total}")

    for w in warnings:
        print("  предупреждение:", w)
    for e in errors:
        print("  ОШИБКА:", e)
    print("\nвариант валиден" if not errors else f"\nошибок: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__.strip())
        sys.exit(2)
    sys.exit(check(Path(sys.argv[1])))
