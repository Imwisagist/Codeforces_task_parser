# Codeforces task parser

[![Python](https://img.shields.io/badge/-Python-464646?style=flat-square&logo=Python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/-PostgreSQL-464646?style=flat-square&logo=PostgreSQL)](https://www.postgresql.org/)

Синхронный скрипт codeforces_task_parser.py парсит задачи с сайта Codeforces и записывает в PostgreSQL.<br> 
Также он выявляет уникальные темы задач и сопутствующие уникальные уровни сложности.<br>
Разбивает все задачи на контесты тема/сложность по 10 задач(если столько имеется).<br>
Контесты также записывает в PostgreSQL.<br>
Задачи в контестах строго уникальные, тоесть каждой задаче принадлежит строго определённый контест.<br>
Контесты наполняются задачами начиная от самых редких тем\сложностей заканчивая самыми частыми чтобы обеспечить условно равномерное заполнение.<br>
Асинхронный скрипт bot.py является телеграм ботом и по запросу выдаёт:
1) Уникальные темы
2) Уникальные сложности для заданной темы
3) Все контесты по заданной теме и сложности
4) Все задачи из заданного контеста
5) Всю доступную информацию по заданной задаче

## Автор

- :white_check_mark: [Imwisagist](https://github.com/Imwisagist)

# Подготовка и запуск проекта в 4 шага
### 1)Склонировать репозиторий на локальную машину:
```
git clone https://github.com:Imwisagist/Codeforces_task_parser
```
### 2)Необходимые токены:
* Cоздайте .env файл в папке infra и впишите:
    ```
    cd infra/
    nano .env
    TELEGRAM_TOKEN=<Токен Вашего бота>
    TELEGRAM_CHAT_ID=<Идентификатор Вашего чата>
    ```
### 3)Не забудьте написать своему боту в лс иначе он не сможет написать Вам:
```
или моему(не гарантирую что он будет доступен:))
https://t.me/codeforce_parser_bot
@codeforce_parser_bot
```
### 4)Запустите Докер:
```
docker-compose up
```
* Если инициализация прошла успешно Вы получите сообщение о запуске бота в свой ТГ:
# Примеры ответов:
### Получить все доступные команды: /start
* Ответ на запрос: /start
```
Список доступных команд:

Уточнения некоторых моментов: /help
Получить все доступные темы контестов: /tags
Получить все доступные сложности для темы: /ratings tag
Получить контесты по теме и сложности: /contests tag rating
Получить задачи из контеста: /contest id_contest
Получить описание задачи: /task task_id
```
* Ответ на запрос: /help
```
Уточнения:

1)"0" среди рейтингов означает что у этой задачи рейтинг не задан.
2)Телеграм автора @Imwisagist
```
### Получить все доступные темы контестов: /tags
* Ответ на запрос: /tags
```
2-sat, meet-in-the-middle, БПФ, Бинарный-поиск, Битмаски, Геометрия, Графы, 
Два-указателя, Деревья, Динамическое-программирование, Жадные-алгоритмы, 
Задачи-без-тем, Игры, Интерактив, Китайская-теорема-об-остатках, Комбинаторика, 
Конструктив, Кратчайшие-пути, Математика, Матрицы, Особая-задача, Паросочетания, 
Перебор, Поиск-в-глубину-и-подобное, Потоки, Разбор-выражений, Разделяй-и-властвуй, 
Расписания, Реализация, СНМ, Сортировки, Строки, Строковые-суфф.-структуры, 
Структуры-данных, Теория-вероятностей, Теория-чисел, Хэши
```
### Получить все доступные сложности для темы: /ratings tag
* Ответ на запрос: /ratings Два-указателя
```
0, 800, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2100, 
2200, 2300, 2400, 2500, 2600, 2700, 2800, 2900, 3000, 3200, 3300, 3400, 3500
```
### Получить контесты по теме и сложности: /contests tag rating
* Ответ на запрос: /contests Математика 800
```
Идентификатор - 474
Номер контеста - 0
Тема - Математика
Сложность - 800

Идентификатор - 155
Номер контеста - 1
Тема - Математика
Сложность - 800

Идентификатор - 82
Номер контеста - 2
Тема - Математика
Сложность - 800

Идентификатор - 57
Номер контеста - 3
Тема - Математика
Сложность - 800

Идентификатор - 38
Номер контеста - 4
Тема - Математика
Сложность - 800

Идентификатор - 28
Номер контеста - 5
Тема - Математика
Сложность - 800

Идентификатор - 22
Номер контеста - 6
Тема - Математика
Сложность - 800

Идентификатор - 17
Номер контеста - 7
Тема - Математика
Сложность - 800

Идентификатор - 11
Номер контеста - 8
Тема - Математика
Сложность - 800

Идентификатор - 7
Номер контеста - 9
Тема - Математика
Сложность - 800
```
### Получить все задачи из контеста: /contest id_contest
* Ответ на запрос: /contest 55
```
Идентификатор задачи- 5575
Темы - (Математика)
Решено раз - 17864
Название - "Волшебная палочка"
Номер и индекс - 1257B
Сложность - 1000

Идентификатор задачи- 5581
Темы - (Математика)
Решено раз - 12924
Название - "Отопление"
Номер и индекс - 1260A
Сложность - 1000

Идентификатор задачи- 6032
Темы - (Математика)
Решено раз - 30707
Название - "Ходы на доске"
Номер и индекс - 1353C
Сложность - 1000

Идентификатор задачи- 6279
Темы - (Перебор, Математика)
Решено раз - 21790
Название - "Boboniu нравится раскрашивать шары"
Номер и индекс - 1395A
Сложность - 1000

Идентификатор задачи- 6381
Темы - (Математика)
Решено раз - 19134
Название - "Покупка факелов"
Номер и индекс - 1418A
Сложность - 1000

Идентификатор задачи- 8262
Темы - (Перебор, Математика)
Решено раз - 7345
Название - "Exchange"
Номер и индекс - 1765E
Сложность - 1000

Идентификатор задачи- 8435
Темы - (Перебор, Реализация, Математика)
Решено раз - 18263
Название - "Престановка "
Номер и индекс - 1790C
Сложность - 1000
```
### Получить описание задачи: /task task_id
* Ответ на запрос: /task 55
```
A. Числа
----------------
ограничение по времени на тест: 1 second
ограничение по памяти на тест: 64 megabytes
--------------------------------------------------
ввод: стандартный ввод
вывод: стандартный вывод
--------------------------------------------------
Маленький Петя очень любит числа. Недавно он определил, что 123 в системе
счисления по основанию 16 состоит из двух цифр: старшая равна 7, а младшая — 11. 
Следовательно, сумма цифр 123 по основанию 16 равна 18.Сейчас ему интересно, чему 
равно среднее арифметическое значение суммы цифр числа A, записанного во всех 
системах исчисления от 2 до A - 1, включительно.Все подсчеты следует производить 
в десятичной системе. Результат нужно вывести в виде несократимой дроби, записанной 
в десятичной системе исчисления.
--------------------------------------------------
Входные данные
--------------------------------------------------
На вход дается единственное число A (3 ≤ A ≤ 1000).
--------------------------------------------------
Выходные данные
--------------------------------------------------
Вывести искомое среднее арифметическое значение в виде несократимой дроби 
в формате «X/Y», где X — числитель, а Y — знаменатель.
--------------------------------------------------
Примеры
--------------------------------------------------
Входные данные
--------------------------------------------------
5
--------------------------------------------------
Выходные данные
--------------------------------------------------
7/3
--------------------------------------------------
Входные данные
--------------------------------------------------
3
--------------------------------------------------
Выходные данные
--------------------------------------------------
2/1
--------------------------------------------------
https://codeforces.com/problemset/problem/13/A?locale=ru
```
