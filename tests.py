import unittest
from sorter import Sorter
import os


def get_text(file):
    tmp = []
    with open(file, 'r') as file:
        for line in file:
            tmp.append(line.replace('\n', ''))
    return tmp


class TestSorter(unittest.TestCase):
    def test_multisort(self):
        with open('file.txt', 'w')as file:
            for i in range(11):
                file.write(str(i) + '\n')

        s = Sorter('file.txt')
        s.sort()
        sorted = get_text('file.txt')
        self.assertEqual(sorted, ['0', '1', '10', '2', '3', '4', '5', '6', '7', '8', '9'])

        s = Sorter('file.txt', is_reversible=True)
        s.sort()
        sorted = get_text('file.txt')
        self.assertEqual(sorted, ['9', '8', '7', '6', '5', '4', '3', '2', '10', '1', '0'])

        os.remove('file.txt')

    def test_stable_sort(self):
        tmp = []
        with open('file.txt', 'w') as file:
            for i in range(11):
                file.write(str(i) + ' 1' + '\n')
                tmp.append(str(i) + ' 1')
        s = Sorter('file.txt', static_column=1)
        s.sort()
        sorted = get_text('file.txt')
        self.assertEqual(sorted, tmp)

        s = Sorter('file.txt', static_column=1, is_reversible=True)
        s.sort()
        sorted = get_text('file.txt')
        tmp.reverse()
        self.assertEqual(sorted, tmp)

        with open('file.txt', 'w') as file:
            for i in range(11):
                file.write(str(10 - i) + ' ' + str(i) + '\n')
        tmp = ['10 0', '9 1', '0 10', '8 2', '7 3', '6 4', '5 5', '4 6', '3 7', '2 8', '1 9']
        s = Sorter('file.txt', static_column=1)
        s.sort()
        sorted = get_text('file.txt')
        self.assertEqual(sorted, tmp)

        s = Sorter('file.txt', static_column=1, is_reversible=True)
        s.sort()
        sorted = get_text('file.txt')
        tmp.reverse()
        self.assertEqual(sorted, tmp)

        os.remove('file.txt')

    def test_million_strings(self):
        f = None
        try:
            f = open('million.txt', 'r')
        except:
            pass
        if f is not None:
            f.close()
            s = Sorter('million.txt')
            s.sort()
            f = open('million.txt', 'r')
            self.assertEqual(f.read(1), ' ')
            f.close()

            s = Sorter('million.txt',is_reversible=True)
            s.sort()
            f= open('million.txt', 'r')
            self.assertEqual(f.read(1), 'Z')
            f.close()


if __name__ == '__main__':
    unittest.main()
