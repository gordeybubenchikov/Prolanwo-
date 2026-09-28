# prolanwo++

**prolanwo++** — интерпретируемый язык программирования с уникальным синтаксисом, созданный для тех, кто хочет большего, чем обычные языки.

## 🎯 Философия

prolanwo++ — **не для простых**. Язык строгий, явный, со своим лицом. Здесь каждая команда говорит, что делает, а не намекает.

## ✨ Уникальные особенности

- **Явные команды**: variable, change variable, notchan
- **Защита переменных**: notchan — запрет на изменение
- **Память переменной**: savichan — вся история значений
- **Логика своим символом**: $$ (И), $# (ИЛИ)
- **Свои блоки**: < открыть, > закрыть
- **Ввод и вывод**: briout, input
- **Цикл**: replay ... begin { }
- **Функции**: function Имя(...) =( ... )
- **Массивы**: array[имя] [ ... ]
- **Выход из цикла**: stop, stopfurt
- **Комментарии**: \"..." и \$"..."$/

## 📦 Установка

### Способ 1: Python-версия

git clone https://github.com/gordeybubenchikov/prolanwo
cd prolanwo
python prolanwo.py пример.pw

### Способ 2: Веб-версия

1. Скачай prolanwo.html
2. Открой в браузере
3. Пиши код → жми «▶ Запустить»

## 🚀 Быстрый старт

\"Первая программа"/

variable line[name]_"Мир";
briout("Привет, " + name + "!");

Вывод:

Привет, Мир!

## 📚 Синтаксис

### Переменные

variable number[x]_5;
variable line[name]_"Гордей";
variable TruFal[ok]_True;
change variable[x]_10;

### Защита и память

notchan x;
variable number[hp]_savichan(100);
briout(history[hp]);
rollback variable[hp];

### Условия

if (x > 5) <
    briout("большое");
>
or if (x == 5) <
    briout("ровно 5");
>
or <
    briout("маленькое");
>

Логика: $$ — «И», $# — «ИЛИ».

### Циклы

variable number[i]_0;
replay (i < 10) begin {
    briout(i);
    change variable[i]_i + 1;
    if (i == 3) <
        stopfurt;
    >
    if (i == 7) <
        stop;
    >
}

### Функции

function Add(number[a], number[b]) =(
    return a + b;
)

briout(Add(3, 4));

### Массивы

array[names] [
    "Гордей";
    "Пётр";
    "Иван";
]

briout(array[names][0]);
new object array[names]_"Аня";

Безлимитный: array[names]_unlimited [ ]

### Рандом

import *random:random[object]*;

variable number[x]_random.number[1, 20];
variable line[name]_random.array[names];

### Комментарии

\"однострочный"/
\$"многострочный"$/

## 📄 Лицензия

MIT — см. файл LICENSE.

## 👤 Автор

Гордей
