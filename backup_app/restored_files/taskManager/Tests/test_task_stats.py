import unittest
from TaskManager.task_stats import TaskStats
from TaskManager.task import Task


class TestTaskStats(unittest.TestCase):

    def setUp(self):
        # Przygotowanie obiektu statystyk i przykładowych zadań
        self.stats = TaskStats()
        self.tasks = [
            Task("Trening", "Siłownia", 1, status="done"),
            Task("Nauka", "Testowanie Oprogramowania", 2, status="todo"),
            Task("Sprzątanie", "Kuchni", 3, status="done"),
        ]

    def test_count_all(self):
        # Test sprawdza czy metoda poprawnie liczy wszystkie zadania
        self.assertEqual(self.stats.count_all(self.tasks), 3)

    def test_count_done(self):
        # Test sprawdza czy metoda liczy tylko zadania ze statusem "done"
        self.assertEqual(self.stats.count_done(self.tasks), 2)


if __name__ == "__main__":
    unittest.main()
