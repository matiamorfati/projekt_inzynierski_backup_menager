from .task import Task


class TaskStats:
    def count_all(self, tasks: list[Task]):
        # Zwraca łączną liczbę zadań
        return len(tasks)

    def count_done(self, tasks: list[Task]):
        # Zwraca liczbę ukończonych zadań
        return sum(1 for t in tasks if t.status == "done")
