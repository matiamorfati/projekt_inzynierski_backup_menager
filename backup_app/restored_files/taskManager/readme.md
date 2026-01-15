Task Manager – aplikacja do zarządzania zadaniami

1. Ogólny opis działania programu
Task Manager to aplikacja konsolowa w języku Python umożliwiająca zarządzanie listą zadań. Dane zadań są zapisywane w bazie danych SQLite.

Użytkownik może:
- dodawać nowe zadania,
- wyświetlać listę zadań,
- edytować istniejące zadania,
- usuwać zadania,
- zmieniać status zadania.


2. Główne funkcjonalności
1. Dodawanie zadania:
   - tytuł,
   - opis,
   - priorytet (1–3),
   - domyślny status „todo”.

2. Wyświetlanie listy zadań:
   - czytelna lista w konsoli.

3. Edycja zadania:
   - zmiana tytułu, opisu, priorytetu lub statusu.

4. Usuwanie zadania:
   - usunięcie zadania po ID.

5. Zmiana statusu zadania:
   - oznaczenie zadania jako „done”.


3. Projekt klas i odpowiedzialności

1. Klasa Task
Reprezentuje pojedyncze zadanie.

Pola:
- id,
- title,
- description,
- priority,
- status.

Metody:
- mark_done() – oznacza zadanie jako wykonane,
- update(...) – aktualizuje dane zadania.

2. Klasa TaskDbManager
Odpowiada za komunikację z bazą danych SQLite.

Metody:
- add_task(task),
- get_tasks(),
- update_task(task),
- delete_task(task_id).

3. Klasa TaskList
Zawiera logikę zarządzania listą zadań.

Metody:
- add_task(data),
- edit_task(task_id, data),
- delete_task(task_id),
- mark_done(task_id),
- get_tasks().

4. Klasa TaskStats
Odpowiada za proste statystyki.

Metody:
- count_all(),
- count_done().

5. Klasa TaskApp
Interfejs konsolowy aplikacji.

Metody:
- run(),
- print_menu(),
- handle_choice().
