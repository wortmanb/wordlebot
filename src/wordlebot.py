#!/usr/bin/env python3
#
# Wordlebot
# 
# 
import argparse
import re
import os
import numpy as np 
import networkx as nx

VALIDATION = '^[a-zA-Z\?]{5}$'
HOME = os.environ.get('HOME')
WORDLIST = f'{HOME}/git/wordlebot/data/wordlist'

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
        """
        # print(f'"{partial}"')
        self.pattern = ['.'] * 5
        self.known = []
        self.bad = []
        self.debug = debug
        with open(WORDLIST, 'r') as input:
            self.wordlist = [ word.strip() for word in input.readlines()]

    def help_msg(self):
        """
        Return a help/usage message.
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

    def guess(self, guess: str):
        """
        Handle this guess by adding each letter to the bad list for now. They
        can be removed during assessment of the response
        
        :param      guess:  The guess
        :type       guess:  str
        """
        for letter in guess:
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
                self.known.append(letter)
                if letter in self.bad:
                    self.bad.remove(letter)
            if re.match('[A-Z]', letter):
                letter = letter.lower()
                self.pattern[idx] = letter
                if letter in self.known:
                    self.known.remove(letter)
                if letter in self.bad:
                    self.bad.remove(letter)
        if self.debug:
            print(f'pattern: {self.pattern}')
            print(f'known: {self.known}')
            print(f'bad: {self.bad}')


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
            if self.debug:
                print(f'Considering {word}')
            # Does it match the pattern?
            pattern = ''.join(self.pattern)
            if not re.match(pattern, word):
                if self.debug:
                    print(f' {word} does not match {pattern}')
                # self.wordlist.remove(word)
                continue
            # Does it contain any letters in the bad letter list?
            matched = False
            for letter in word:
                if letter in self.bad:
                    if self.debug:
                        print(f' {word} contains "{letter}" but shouldn\'t')
                    matched = True
                    break
            if matched:
                # self.wordlist.remove(word)
                continue
            # Now, are all the letters in the known list present in the word?
            violated = False
            for letter in self.known:
                if letter not in word:
                    if self.debug:
                        print(f' {word} does not contain "{letter}"')
                    violated = True
                    break
            if violated:
                if self.debug:
                    print(f'Removing {word}')
                # self.wordlist.remove(word)
            else:
                candidates.append(word)
        if self.debug:
            print(f'candidates: {candidates}')
        self.wordlist = candidates
        return candidates

def main():
    """
    Main function
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_false", dest="usage", 
        default=True, help="Don't print the handy dandy usage message")
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