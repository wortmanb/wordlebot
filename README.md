# Name

Wordlebot, the handy Wordle assistant

# Description
Wordlebot won't solve the puzzles for you, but after any guess and response from Wordle, it will help you whittle down the list of candidate words to just those that fit the current pattern, bad letters, and known letters, using the official Wordle word list.

## Installation

Clone the repository into $HOME/git/. You can clone it elsewhere, but will need to modify the WORDLIST definition in the code to point to your chosen location.

## Usage

usage: wordlebot.py [-h] [--quiet]

optional arguments:
  -h, --help  show this help message and exit
  --quiet     Don't print the handy dandy usage message

Wordlebot will prompt for your first guess and the response from Wordle before giving you a list of possible next words.

## Support

Hahahahahahaha. Right.

## Roadmap

I'd love to reimplement the wordlist using a tree, but clearly not for performance reasons. I just think it'd be cool.

## Authors and acknowledgment

Bret Wortman, (C) 2022

## License

Beerware (V. 42)

## Project status

It works. I don't plan to mess with it much more except as intellectual exercise.
