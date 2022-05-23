#!/usr/bin/env python3
#
# Wordlebot
#
#
import argparse
import re
import os
import re

VALIDATION = '^[a-zA-Z?]{5}$'
HOME = os.environ.get('HOME')
WORDLIST = f'{HOME}/git/wordlebot/data/wordlist'


class KnownLetters:
    """
    Encapsulate a known letters list, also keeping track of the locations where
    we know each word is not.
    """

    def __init__(self):
        """
        Constructs a new instance.
        """
        self.data = {}

    def __repr__(self):
        rep = 'KnownLetters( ' + str(self.data) + ' )'
        return rep

    def store(self, letter: str, index: int):
        """
        Store a letter and location for future reference

        :param      letter:  The letter
        :type       letter:  str
        :param      index:   The index
        :type       index:   int
        """
        if letter not in self.data.keys():
            self.data[letter] = []
        self.data[letter].append(index)

    def keys(self) -> list[str]:
        """
        Return a list of all keys

        :returns:   List of current keys
        :rtype:     List of str
        """
        return self.data.keys()

    def remove(self, letter: str):
        """
        Removes the specified letter.

        :param      letter:  The letter
        :type       letter:  str
        """
        self.data.pop(letter)

    def has_letter(self, letter: str) -> bool:
        """
        Check to see if this letter has been seen before.

        :param      letter:  The letter
        :type       letter:  str

        :returns:   True or False
        :rtype:     bool
        """
        return letter in self.data.keys()

    def has_letter_at_index(self, letter: str, index: int) -> bool:
        """
        Check to see if this letter has been seen in this index before.

        :param      letter:  The letter
        :type       letter:  str
        :param      index:   The index
        :type       index:   int

        :returns:   True or False
        :rtype:     bool
        """
        if self.has_letter(letter):
            return index in self.data[letter]
        return False

    def indices(self, letter: str) -> list[int]:
        """
        Return a list of indices representing the locations where this letter
        has already been seen.

        :param      letter:  The letter
        :type       letter:  str

        :returns:   Prior locations
        :rtype:     List of integers
        """
        if self.has_letter(letter):
            return self.data[letter]
        return []


class Wordlebot:
    """
    This class describes a wordlebot.

    Since Wordle uses a restricted list of words which does not include all
    possible 5-letter words, this Wordlebot takes the response to a series of
    guesses and builds a (hopefully) ever-shortening list of possible next
    words, using only those from the canonical word list.
    """

    def __init__(self, debug: bool):
        """
        Create a new wordlebot

        :param      debug:  The debug
        :type       debug:  bool
        """
        # print(f'"{partial}"')
        self.pattern = ['.'] * 5
        self.known = KnownLetters()
        self.bad = []
        self.debug = debug
        with open(WORDLIST, 'r') as fp:
            self.wordlist = [word.strip() for word in fp.readlines()]

    def help_msg(self):
        """
        Return a help/usage message.

        :returns:   { description_of_the_return_value }
        :rtype:     { return_type_description }
        """

        return """
Wordlebot helps focus guesses by restricting the universe of 5-letter words
to just those on the Wordlebot word list. Enter guesses as a string of
lowercase letters, then give the response by adding green letters as capitals,
yellow letters as lowercase, and others as '?' or some other non-letter
character.

Example:

Enter guess: crane
Enter response: c??N?
Next guesses: cling, clink, clung, count, icing

"""

    def log(self, message: str):
        """
        Internal logging method

        :param      message:  The message
        :type       message:  String
        """
        if self.debug:
            print(message)

    def guess(self, guess: str):
        """
        Handle this guess by adding each letter to the bad list for now. They
        can be removed during assessment of the response

        :param      guess:  The guess
        :type       guess:  str
        """
        for letter in guess:
            if not self.known.has_letter(letter):
                self.bad.append(letter)

    def assess(self, response: str):
        """
        Assess the last response. Add any new greens to the pattern and any new
        yellows to the known list. This does not yet do anything to track
        letters known to not be part of the solution.

        :param      response:        The response
        :type       response:        str

        :raises     AssertionError:  { exception_description }
        """
        assert len(response) == 5
        assert re.match(VALIDATION, response)
        for idx, letter in enumerate(list(response)):
            if re.match('[a-z]', letter):
                self.known.store(letter, idx)
                if letter in self.bad:
                    self.bad.remove(letter)
            if re.match('[A-Z]', letter):
                letter = letter.lower()
                self.pattern[idx] = letter
                if letter in self.known.keys():
                    self.known.remove(letter)
                if letter in self.bad:
                    self.bad.remove(letter)
        self.log(f'pattern: {self.pattern}')
        self.log(f'known: {self.known}')
        self.log(f'bad: {self.bad}')

    def solve(self, response: str) -> list[str]:
        """
        Look for words that make good candidates given this response and prior
        ones as well.

        :param      response:  The last response
        :type       response:  str

        :returns:   List of matching words
        :rtype:     list[str]
        """
        self.assess(response)
        candidates = []
        for word in self.wordlist:
            self.log(f'Considering {word}')
            # Does it match the pattern?
            pattern = ''.join(self.pattern)
            if not re.match(pattern, word):
                self.log(f' {word} does not match {pattern}')
                # self.wordlist.remove(word)
                continue
            # Does it contain any letters in the bad letter list?
            matched = False
            for letter in word:
                if letter in self.bad:
                    self.log(f' {word} contains "{letter}" but shouldn\'t')
                    matched = True
                    break
            if matched:
                # self.wordlist.remove(word)
                continue
            # Now, are all the letters in the known list present in the word?
            violated = False
            for letter in self.known.keys():
                if letter not in word:
                    self.log(f' {word} does not contain "{letter}"')
                    violated = True
                    break
                for index in [_.start() for _ in re.finditer(letter, word)]:
                    if self.known.has_letter_at_index(letter, index):
                        self.log(f' {word} contains {letter} at {index}')
                        violated = True
                        break
            if not violated:
                self.log(f'{word} is still a candidate')
                candidates.append(word)
        self.log(f'candidates: {candidates}')
        self.wordlist = candidates
        return candidates


def main():
    """
    Main function
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", "-q", action="store_false", dest="usage",
                        default=True,
                        help="Don't print the handy dandy usage message")
    parser.add_argument("--debug", "-d", action="store_true", dest="debug",
                        default=False, help="Print extra debugging output")
    args = parser.parse_args()

    wb = Wordlebot(args.debug)
    if args.usage:
        print(wb.help_msg())

    while True:
        guess = input("Enter guess: ")
        wb.guess(guess)
        response = input("Enter response: ")
        solutions = wb.solve(response)
        sol = ', '.join(solutions)
        count = len(solutions)
        print(f'There are {count} possible guesses: {sol}')
        if len(solutions) <= 1:
            break


if __name__ == '__main__':
    main()
