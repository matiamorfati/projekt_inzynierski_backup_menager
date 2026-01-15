from .task_list import TaskList
from .task_stats import TaskStats


class TaskApp:
    def __init__(self, task_list: TaskList):
        self.task_list = task_list
        self.stats = TaskStats()

    def run(self):
        running = True
        while running:
            self.print_menu()
            choice = input("Wybierz opcję: ").strip()
            running = self.handle_choice(choice)

    def print_menu(self):
        print("\n--- TASK MANAGER ---")
        print("1. Dodaj zadanie")
        print("2. Pokaż zadania")
        print("3. Edytuj zadanie")
        print("4. Usuń zadanie")
        print("5. Oznacz jako wykonane")
        print("6. Statystyki")
        print("7. Wyjście")

    def handle_choice(self, choice):
        if choice == "1":
            self.add_task()
        elif choice == "2":
            self.show_tasks()
        elif choice == "3":
            self.edit_task()
        elif choice == "4":
            self.delete_task()
        elif choice == "5":
            self.mark_done()
        elif choice == "6":
            self.show_stats()
        elif choice == "7":
            print("Koniec programu.")
            return False
        else:
            print("Niepoprawna opcja.")
        return True

    def add_task(self):
        title = input("Tytuł: ").strip()
        if not title:
            print("Tytuł jest wymagany.")
            return

        description = input("Opis: ").strip()
        try:
            priority = int(input("Priorytet (1-3): ").strip())
        except ValueError:
            print("Priorytet musi być liczbą.")
            return

        self.task_list.add_task(title, description, priority)
        print("Zadanie dodane.")

    def show_tasks(self):
        tasks = self.task_list.get_tasks()
        if not tasks:
            print("Brak zadań.")
            return

        for task in tasks:
            print(task.format_for_console())

    def edit_task(self):
        self.show_tasks()
        try:
            task_id = int(input("Podaj ID zadania do edycji: ").strip())
        except ValueError:
            print("Niepoprawne ID.")
            return

        title = input("Nowy tytuł: ").strip()
        description = input("Nowy opis: ").strip()
        priority_raw = input("Nowy priorytet: ").strip()
        status = input("Nowy status (todo lub done): ").strip()

        data = {}
        if title:
            data["title"] = title
        if description:
            data["description"] = description
        if priority_raw:
            try:
                data["priority"] = int(priority_raw)
            except ValueError:
                print("Priorytet musi być liczbą.")
                return
        if status:
            data["status"] = status

        if self.task_list.edit_task(task_id, data):
            print("Zadanie zaktualizowane.")
        else:
            print("Nie znaleziono zadania.")

    def delete_task(self):
        try:
            task_id = int(input("Podaj ID zadania do usunięcia: ").strip())
        except ValueError:
            print("Niepoprawne ID.")
            return

        self.task_list.delete_task(task_id)
        print("Zadanie usunięte.")

    def mark_done(self):
        try:
            task_id = int(input("Podaj ID zadania: ").strip())
        except ValueError:
            print("Niepoprawne ID.")
            return

        if self.task_list.mark_done(task_id):
            print("Zadanie oznaczone jako wykonane.")
        else:
            print("Nie znaleziono zadania.")

    def show_stats(self):
        tasks = self.task_list.get_tasks()
        print("Liczba wszystkich zadań:", self.stats.count_all(tasks))
        print("Liczba wykonanych zadań:", self.stats.count_done(tasks))
