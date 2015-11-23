__author__ = 'Anton Osten'

from argparse import ArgumentParser
from collections import Counter, defaultdict
import csv
import itertools
import math
from pathlib import Path
from pprint import pformat, pprint
import re

# def find_trigrams_word(word, all_words):
#     indexes = np.where(all_words == word)[0]
#
#     bigrams = set()
#     for index in indexes:
#         bigram = all_words[index - 1], all_words[index + 1]
#         if bigram not in bigrams:
#             trigram = bigram[0], word, bigram[1]
#             yield trigram, bigram


def get_corpus_bigrams(words):
    bigrams = Counter()

    for i in range(1, len(words)):
        bigrams[(words[i - 1], words[i])] += 1

    return bigrams

def find_trigrams(freq_words, all_words):
    trigrams = defaultdict(Counter)

    for n, word in enumerate(all_words):
        if word in freq_words:
            try:
                bigram = all_words[n - 1], all_words[n + 1]
                trigrams[word][bigram] += 1
            except IndexError:
                # this is probably a one-off character
                continue

    return trigrams


def get_middle_ratios(trigrams, all_bigrams, words, detailed_output=False):
    real_bigrams = {bigram for bigram in itertools.chain.from_iterable(trigrams.values())
                    if bigram in all_bigrams}

    successful_contexts = Counter()
    num_words = len(words)
    mi_words = {}

    detailed_info = defaultdict(list)

    # calculate the ratios
    for middle_word, bigrams in trigrams.items():

        for bigram, trigram_count in bigrams.items():
            # print('trigram count', trigram_count)
            ratio_with_middle = trigram_count * num_words
            # print('ratio with', ratio_with_middle)


            bigram_count = all_bigrams[bigram]
            ratio_without_middle = bigram_count * words[middle_word]

            try:
                combined_ratio = ratio_with_middle / ratio_without_middle
                if combined_ratio > 1:
                    word_frequencies = words[bigram[0]] * words[middle_word] * words[bigram[1]]
                    successful_contexts[middle_word] += 1

                    mutual_information = math.log2(trigram_count / word_frequencies)
                    mi_words[middle_word] = mutual_information

                    if detailed_output:
                        trigram = bigram[0], middle_word, bigram[1]
                        this_bigram_output = trigram, trigram_count, ratio_with_middle
                        this_trigram_output = bigram, bigram_count, ratio_without_middle

                        detailed_info[middle_word].append((*this_bigram_output,
                                                           *this_trigram_output,
                                                           combined_ratio,
                                                           mutual_information))


            except ZeroDivisionError:
                # no real bigrams
                #exit('oh no')
                continue


    middle_ratios = {word: (successes / len(trigrams[word]))
                     for word, successes in successful_contexts.items()}

    return middle_ratios, real_bigrams, detailed_info


def run(corpus, freq_threshold=10, detailed_output=False):
    all_words = re.findall(r"\w+'\w+|\w+|[.,;]", corpus)
    counted_words = Counter(all_words)

    print('getting most frequent words...')
    freq_words = {word for word, count in counted_words.items() if count >= freq_threshold}

    print('getting all bigrams from the corpus...')
    # we need this to check if the (w1, w3) exists the corpus by itself
    all_bigrams = get_corpus_bigrams(all_words)

    print('finding trigrams...')
    trigrams = find_trigrams(freq_words, all_words)

    print('finding the middle ratios...')
    middle_ratios, real_bigrams, detailed_info = get_middle_ratios(trigrams, all_bigrams,
                                                                   counted_words,
                                                                   detailed_output=detailed_output)

    return middle_ratios, real_bigrams, detailed_info

def print_output(corpus_name, ratios, real_bigrams, detailed_info=None):
    results_path = Path('results', corpus_name)
    print('printing results to', results_path)
    if not results_path.exists():
        results_path.mkdir(parents=True)

    output_path_ratios = Path(results_path, 'ratios.csv')
    output_path_real_bigrams = Path(results_path, 'real_bigrams.txt')

    with output_path_ratios.open('w') as out_file:
       writer = csv.writer(out_file, delimiter=',')
       for item in ratios.items():
               # print('{:15}\t{:.3f}\n{}'.format(word, ratio, pformat(bigrams)), file=out_file)
            writer.writerow((item))

    with output_path_real_bigrams.open('w') as out_file:
        pprint(real_bigrams, stream=out_file)

    if detailed_info:
        print('printing detailed output')
        output_path_words = Path(results_path, 'words')
        if not output_path_words.exists():
            output_path_words.mkdir()

        header = ('trigram', 'trigram count', 'count * k',
                  'bigram', 'bigram count', 'count * [word]', 'ratio')
        for word, info in detailed_info.items():
            word_info_path = Path(output_path_words, word + '.csv')
            with word_info_path.open('w') as out_file:
                writer = csv.writer(out_file, delimiter=',')
                writer.writerow(header)
                for row in info:
                    writer.writerow(row)



if __name__ == '__main__':
    arg_parser = ArgumentParser()
    arg_parser.add_argument('corpus', help='corpus file to use for computing the ratios')
    arg_parser.add_argument('--detailed-output', action='store_true',
                            help='detailed output on each word')
    args = arg_parser.parse_args()

    file = Path(args.corpus)

    with file.open() as corpus_file:
        corpus = corpus_file.read().casefold()

    ratios, real_bigrams, detailed_info = run(corpus, detailed_output=args.detailed_output)

    corpus_name = file.stem
    print_output(corpus_name, ratios, real_bigrams, detailed_info=detailed_info)

