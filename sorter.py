import re
import os
import time
import tempfile
import argparse
import help_strings
from tqdm import tqdm
from memory_profiler import memory_usage


class Sorter():
    def __init__(self, filename, separators=' \t', is_reversible=False, static_column=None,
                 strings_in_tmp_file=4000, tmp_dir=None):
        self.filename = filename
        self.is_reversible = is_reversible
        self.static_column = static_column
        self.strings_in_tmp_file = strings_in_tmp_file
        self.strings_counter = 0
        self.split_regexp = self.make_regexp(separators)
        self.tmp_dir = self.make_tmp_dir(tmp_dir)
        self.start_dir = os.getcwd()
        self.tmp_file_names = []
        self.tmp_files_count = 0
        self.merge_by_one_step = 10
        self.result_file = None
        self.is_small_file = False
        self.strings_count = get_strings_count(filename)

    def sort(self):
        """Основной метод сортировки"""
        self.split_file_to_sorted_tmp_files()
        self.merge_tmp_files()
        self.replace_input_file_with_result_file()
        self.delete_tmp_dir()

    def split_file_to_sorted_tmp_files(self):
        """Разбивает целый файл на несколько временных файлов поменьше и сортирует их"""
        current_dir = os.getcwd()
        os.chdir(self.start_dir)
        input_file = open(self.filename, 'r')
        os.chdir(self.tmp_dir)

        current_lines = 0
        tmp_text = ''

        for line in tqdm(input_file, desc='Splitting', total=self.strings_count):
            if current_lines != 0:
                tmp_text += "\n"
            current_lines += 1
            line = line.replace("\n", "")
            tmp_text += line

            if current_lines == self.strings_in_tmp_file:
                current_lines = 0
                self.process_tmp_file(tmp_text)
                tmp_text = ''
        if tmp_text != '' or self.tmp_files_count == 0:
            self.process_tmp_file(tmp_text)
        input_file.close()
        os.chdir(current_dir)

    def process_tmp_file(self, text):
        """Записывает отсортированный текст во временный файл"""
        tmp_file = open(str(self.tmp_files_count) + ".tmp", 'w')
        self.tmp_files_count += 1
        self.tmp_file_names.append(tmp_file.name)
        tmp_text = self.sort_text(text)
        tmp_file.write(tmp_text)
        tmp_file.close()

    def sort_text(self, text):
        """Сортирует строки временных файлов"""
        if text == '':
            return ''
        strings = text.split('\n')
        splitted_strings = []
        for i in range(len(strings)):
            self.strings_counter += 1
            splitted_strings.append([re.split(self.split_regexp, strings[i].lower()), self.strings_counter,
                                     strings[i]])
        if self.static_column is not None:
            sorted_strings = self.static_sort(splitted_strings)
        else:
            sorted_strings = self.multisort(splitted_strings)
        result = ""
        for string in sorted_strings:
            result += string[2] + "\n"
        return result[:-1]

    def sort_by_column(self, string):
        '''Способ стабильной сортировки'''
        if self.static_column >= len(string[0]):
            return ('', string[1])
        return (string[0][self.static_column], string[1])

    def static_sort(self, strings):
        strings.sort(key=self.sort_by_column, reverse=self.is_reversible)
        return strings

    def multisort(self, strings):
        strings.sort(reverse=self.is_reversible)
        return strings

    def merge_tmp_files(self):
        '''Объединяет все временные файлы в один'''
        if len(self.tmp_file_names) == 1:
            self.result_file = self.tmp_file_names[0]
            self.is_small_file = True
        else:
            tmp = self.get_total_merge()
            with tqdm(desc='Merging', total=tmp) as bar:
                while len(self.tmp_file_names) > 1:
                    count_of_merging = min(self.merge_by_one_step, len(self.tmp_file_names))
                    self.merge_part_of_tmp_files(count_of_merging, bar)

    def get_total_merge(self):
        tmp_list = []
        tmp = self.strings_count
        for _ in range(self.strings_count // self.strings_in_tmp_file):
            tmp_list.append(self.strings_in_tmp_file)
            tmp -= self.strings_in_tmp_file
        else:
            tmp_list.append(tmp)
        res = 0
        while len(tmp_list) > 1:
            merge_count = min(self.merge_by_one_step, len(tmp_list))
            sum = 0
            for _ in range(merge_count):
                sum += tmp_list.pop(0)
            tmp_list.append(sum)
            res += sum
        return res

    def merge_part_of_tmp_files(self, count, bar):
        '''Объединяет некоторое количество временных файлов в один'''
        os.chdir(self.tmp_dir)
        result_file = open(str(self.tmp_files_count) + ".tmp", 'w')
        self.tmp_file_names.insert(self.tmp_files_count, result_file.name)
        self.tmp_files_count += 1

        files = []
        strings = []
        for i in range(count):
            files.append(open(self.tmp_file_names[i], 'r'))
            current_string = files[i].readline()
            if current_string == "":
                name = files[i].name
                files[i].close()
                os.remove(name)
                self.tmp_file_names.remove(files[i].name)
                self.tmp_files_count -= 1
                files.remove(files[i])
                strings.append((None, i))
            else:
                current_string = current_string.replace('\n', '')
                strings.append((current_string, i))

        first_string = True
        while len(strings) > 0:
            if not first_string:
                result_file.write('\n')
            else:
                first_string = False

            id_smaller_string = self.get_smaller_string_id(strings)
            if id_smaller_string == 'END':
                strings = []
                break

            result_file.write(strings[id_smaller_string][0])
            bar.update(1)
            next_string = files[id_smaller_string].readline()
            if next_string == '':
                name = files[id_smaller_string].name
                files[id_smaller_string].close()
                os.remove(name)
                self.tmp_file_names.remove(files[id_smaller_string].name)
                files[id_smaller_string] = None
                strings[id_smaller_string] = (None, id_smaller_string)
            else:
                next_string = next_string.replace('\n', '')
                strings[id_smaller_string] = (next_string, id_smaller_string)

        for file in files:
            if file is not None:
                name = file.name
                file.close()
                os.remove(name)
                self.tmp_file_names.remove(name)

        self.result_file = result_file.name
        result_file.close()

    def get_smaller_string_id(self, strings):
        '''Возвращает позицию наименьшей по сортировке строки в массиве строк'''
        tmp_arr = []
        for string in strings:
            if string[0] is None:
                continue
            tmp_arr.append([re.split(self.split_regexp, string[0].lower()), string[1]])
        if self.static_column is not None:
            tmp_arr.sort(key=self.sort_by_column, reverse=self.is_reversible)
        else:
            tmp_arr.sort(reverse=self.is_reversible)
        if len(tmp_arr) == 0:
            return 'END'
        return int(tmp_arr[0][1])

    def replace_input_file_with_result_file(self):
        '''Заменяет исходный файл отсортированным'''
        os.chdir(self.tmp_dir)
        result_file = open(self.result_file, 'r')
        os.chdir(self.start_dir)
        input_file = open(self.filename, 'w')
        for line in result_file:
            input_file.write(line)
        input_file.close()
        result_file.close()

    def delete_tmp_dir(self):
        '''Удаляет временную директорию'''
        if not self.is_small_file:
            for i in self.tmp_file_names:
                path = os.path.join(self.tmp_dir, i)
                os.remove(path)
        else:
            os.remove(os.path.join(self.tmp_dir, str(0) + ".tmp"))
        os.rmdir(self.tmp_dir)

    @staticmethod
    def make_regexp(separators):
        '''Возвращает регулярное выражение для разбиения строк на столбцы'''
        if len(separators) == 1:
            if separators == '[':
                return re.compile('\[')
            if separators == ']':
                return re.compile('\]')
            return re.compile(separators)

        result = '['
        for symbol in separators:
            if symbol == '[' or symbol == ']':
                result += '\\'
            result += symbol
        result += ']'
        return re.compile(result)

    @staticmethod
    def make_tmp_dir(tmp_dir):
        '''Создаёт директорию для временных файлов'''
        if tmp_dir is None:
            return tempfile.mkdtemp()
        else:
            try:
                os.stat(tmp_dir)
            except IOError:
                os.mkdir(tmp_dir)
            return os.getcwd() + '/' + tmp_dir


def get_strings_count(filename):
    with open(filename, 'r') as f:
        return len(f.readlines())


def parse_args():
    '''Парсер аргументов командной строки'''
    parser = argparse.ArgumentParser(description='Sort big file.')
    parser.add_argument('filename', help=help_strings.FILENAME)
    parser.add_argument('-s', '--separators', help=help_strings.SEPARATORS,
                        default=' \t')
    parser.add_argument('-r', '--reverse', action='store_const', const=True,
                        default=False, help=help_strings.REVERSE)
    parser.add_argument('-c', '--column', help=help_strings.COLUMN,
                        type=int, default=0)
    parser.add_argument('-m', '--maxstrings', help=help_strings.MAX_COUNT_OF_STRINGS,
                        type=int, default=4000)
    parser.add_argument('-t', '--tmpdir', help=help_strings.TMP_DIR, default=None)
    return parser


def start():
    start_memory = memory_usage(-1)[0]
    start_time = time.time()
    parser = parse_args()
    args = parser.parse_args()
    print(args)
    count_of_strings = str(get_strings_count(args.filename))
    s = Sorter(filename=args.filename, separators=args.separators, is_reversible=args.reverse,
               static_column=args.column, strings_in_tmp_file=args.maxstrings, tmp_dir=args.tmpdir)
    s.sort()
    memory = str((memory_usage(-1)[0] - start_memory) * 1024)
    print('\n --- Отсортировано ' + count_of_strings + ' строк за ' + str(round(time.time() - start_time, 3)) + ' сек')
    print(' --- Потреблено памяти ' + memory + ' Kb')


if __name__ == '__main__':
    start()
