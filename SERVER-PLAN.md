# Перенос демо на сервер

## Граница сборки

GitHub Pages отдаёт статические страницы и не запускает сервер. Демонстрационная сборка сохраняет bank/db.js и открытые ключи. До продаж нужен отдельный API и база; страницы подключаются к API через HTTPS.

## Данные

- users: id, role, name, verified_email, password_hash, created_at. Сессии: session_hash, user_id, expires_at, revoked_at. Пароли хешируются Argon2id, сессия в HttpOnly Secure SameSite cookie.
- subjects: id, title, base_price_kopecks, invitation_price_kopecks, enabled. rus: 99000/84000, soc выключен до банка.
- teacher_subjects: teacher_id, subject_id, commission_percent. В демо 30%, решение фиксируется на момент платежа.
- invitations: id, token_hash, teacher_id, subject_id, optional_student_name, expires_at, used_by. Групповые и персональные приглашения имеют разные правила повторного использования.
- enrollments: id, student_id, teacher_id nullable, subject_id, status, expires_at. Уникальность student_id + subject_id.
- payments: id, enrollment_id, provider_payment_id unique, idempotency_key unique, amount_kopecks, status, commission_kopecks, paid_at.
- variants: id, subject_id, revision, public_payload. variant_keys: variant_id, revision, private_answers и правила начисления; доступен только серверу.
- submissions: id, enrollment_id, variant_id, revision, answers, essay, status, submitted_at. submission_scores: server_part1, machine_draft, reviewed_scores, reviewed_at, reviewer_id. annotations: submission_id, start_offset, end_offset, criterion, note. Хранится исходный неизменный текст и система координат UTF-16 для совпадения с браузером.
- commissions: payment_id unique, teacher_id, amount_kopecks, payout_batch_id nullable. payouts: id, teacher_id, amount_kopecks, status, paid_at, reference. Отмена оплаты создаёт сторнирующее начисление.

## API

- POST /auth/register, /auth/login, /auth/logout; POST /auth/recovery/request и /auth/recovery/confirm; GET /me. Лимиты запросов, одноразовые токены восстановления и проверка email.
- POST /teacher/invitations; GET /invitations/:token возвращает преподавателя, предмет и рассчитанную сервером цену.
- POST /checkout принимает только предмет и токен приглашения. Сервер вычисляет цену, создаёт платёж ЮKassa с idempotency key и возвращает redirect URL. Клиент не может задать сумму или процент.
- POST /payments/webhook подтверждает оплату после проверки уведомления через серверный запрос к провайдеру; сумма, валюта, получатель и payment ID должны совпасть. Одна транзакция активирует доступ и записывает комиссию. Redirect после оплаты сам доступ не выдаёт.
- GET /student/access; GET /variants/:id возвращает только публичное условие, варианты ответа и исходные тексты. Не выдаёт key, exp с ответом, тренировочные правильные буквы или запятые.
- POST /submissions принимает ответы и сочинение; сервер проверяет доступ и предмет, загружает ключи, вычисляет часть 1. Повторная отправка с тем же idempotency key возвращает ту же работу.
- GET /student/submissions и /student/submissions/:id: только собственные работы. Эталоны и объяснения возвращаются после сдачи по установленному режиму просмотра.
- GET /teacher/students?subject=rus; GET /teacher/submissions?subject=rus: только связанные с преподавателем ученики.
- PATCH /teacher/submissions/:id/review: черновик К7–К10 и замечания. POST /teacher/submissions/:id/complete проверяет шкалы, объём сочинения и все обязательные оценки, затем публикует результат ученику. Изменения проверяются по revision для защиты от перезаписи.
- GET /teacher/commissions?subject=rus: оплачено, начислено, выплачено, остаток. Реестр выплат выгружается администратором, перевод выполняется вручную.

## Проверка и ИИ

Перенести scoreOf из trainer.html на сервер. tools/validate_variant.py проверяет структуру варианта, но не заменяет проверку ответов ученика. Нормализация, альтернативные ключи, порядок символов, частичные баллы и ограничение длины должны иметь серверные регрессионные тесты.

Сначала сервер разбивает исходное сочинение на предложения, считает слова и хранит границы. При объёме ниже установленного минимума — нули по всем критериям. Модель получает пронумерованные предложения, возвращает номера и черновую разметку. Ответ проверяется схемой и границами; модель не управляет общим баллом и не получает права на базу. К7–К10 выставляет преподаватель. Необходима сверка всех шкал по официальным материалам целевого года.

## Порядок переноса

1. API, миграции, роли и сессии; затем adapter вместо DB.
2. Разделение варианта на публичные условия и приватные ключи; удалить ключи из всех клиентских JS, JSON и карт исходников. Приватный банк не хранить в публичной ветке.
3. Отправка и серверная проверка работ; кабинеты и замечания с проверкой владения.
4. ЮKassa в тестовом режиме, идемпотентность и webhook; активация доступа, начисления и ручной реестр.
5. Настоящий ИИ при явном включении, очередь задач и лимиты расходов.
6. Приёмка на разных устройствах, резервные копии и восстановление базы, затем запуск продаж.

## Приёмка

Ученик и преподаватель на разных устройствах проходят весь путь. Без приглашения — 990 ₽; с корректным — 840 ₽. Повторный webhook не дублирует доступ и комиссию. Изменённые на клиенте цена, баллы и student_id не принимаются. Чужие работы и купленный другой предмет недоступны. Ключей нет в ответах API и статических ресурсах. После проверки ученик видит рассчитанный итог, все критерии и точные фрагменты замечаний.
