# Product Mission

## Pitch
Wordlebot AI is an intelligent Wordle solver that helps players minimize their guess count through strategic AI-powered decision-making. Unlike simple frequency-based assistants, it combines information theory, multi-step lookahead, and strategic reasoning to select optimal guesses that maximize information gain while minimizing total attempts.

## Users

### Primary Customers
- **Competitive Wordle Players**: Players seeking to improve their average score and maintain long win streaks
- **Strategy Enthusiasts**: People interested in optimal game-playing strategies and learning from AI reasoning
- **Wordle Analysts**: Users who want to understand and analyze different solving approaches

### User Personas

**Competitive Player** (25-45)
- **Role:** Daily Wordle player tracking personal statistics
- **Context:** Plays every day, compares scores with friends, maintains active win streaks
- **Pain Points:** Inconsistent guess counts, difficulty maintaining sub-4 average, occasional streak-breaking failures
- **Goals:** Lower average guess count, maintain 100% win rate, understand why certain guesses are optimal

**Strategy Learner** (30-55)
- **Role:** Casual player interested in optimal solving techniques
- **Context:** Plays multiple word games, enjoys understanding game theory
- **Pain Points:** Relies on intuition rather than strategy, unsure if choices are optimal, wants to improve skills
- **Goals:** Learn strategic principles, understand information theory application, see reasoning behind AI decisions

## The Problem

### Suboptimal Guess Selection
Current frequency-based assistants suggest common words but don't consider strategic positioning for future guesses. Players often waste guesses on words that provide minimal new information, leading to higher average guess counts and occasional failures. A single poor guess can mean the difference between solving in 3 versus 5 attempts.

**Our Solution:** We employ AI-powered strategic analysis that evaluates each potential guess based on expected information gain, worst-case scenarios, and multi-step lookahead. The AI explains its reasoning, helping users understand not just what to guess, but why that guess is optimal.

### Lack of Strategic Depth
Existing tools use static scoring based on letter/word frequency without considering the dynamic game state or future implications of each guess.

**Our Solution:** We implement information theory principles (entropy maximization) combined with AI reasoning to select guesses that partition the remaining solution space most effectively. The system considers worst-case scenarios and evaluates multi-step paths to minimize maximum guess count.

### No Learning or Adaptation
Traditional assistants apply the same scoring algorithm regardless of context, failing to adapt strategies based on game state or learned patterns.

**Our Solution:** We integrate AI that can adjust strategy based on current constraints, learn from patterns in the solution space, and provide contextual reasoning for each decision.

## Differentiators

### AI-Powered Strategic Reasoning
Unlike purely algorithmic tools that score words by frequency, we provide AI-driven strategic analysis that evaluates information gain, considers future moves, and explains the reasoning behind each suggestion. This results in measurably lower average guess counts and better worst-case performance.

### Information Theory Optimization
We calculate expected information gain (entropy reduction) for each candidate guess, ensuring every move maximally narrows the solution space. This mathematical foundation provides a significant advantage over heuristic-based approaches.

### Explainable AI Decisions
Rather than presenting a list of suggestions without context, we explain why specific guesses are optimal at each stage. Users learn strategic principles and understand the trade-offs between exploring new letters versus confirming likely solutions.

### Multi-Step Lookahead
Our AI evaluates not just the immediate guess but considers optimal follow-up moves for different response scenarios. This minimax approach minimizes worst-case guess counts and handles edge cases that trip up simpler algorithms.

## Key Features

### Core Features
- **AI Strategy Engine:** Intelligent agent that suggests optimal guesses using information theory and multi-step analysis to minimize expected guess count
- **Information Gain Calculator:** Real-time entropy calculations showing which guesses provide maximum information about the solution
- **Word Filter with Constraints:** Efficient filtering based on green/yellow/gray letter feedback with pattern matching validation
- **COCA Frequency Integration:** Leverage corpus linguistics data to prioritize common words when multiple optimal choices exist

### Strategic Features
- **Multi-Step Lookahead:** Evaluate potential guess sequences to minimize worst-case scenarios and average guess count
- **Partition Analysis:** Show how each candidate guess divides the remaining solution space into subsets
- **Minimax Strategy:** Identify guesses that minimize the maximum remaining candidates in worst-case scenarios
- **Strategy Modes:** Switch between aggressive (minimize average), safe (minimize worst-case), and balanced approaches

### Explainability Features
- **Decision Reasoning:** Clear explanations of why the AI recommends specific guesses at each stage
- **Information Metrics Display:** Show entropy, expected remaining candidates, and other decision factors
- **Alternative Analysis:** Compare AI suggestion against user's preferred alternatives with quantitative differences
- **Historical Performance:** Track and display statistics comparing AI-guided games versus manual play

### Advanced Features
- **Performance Analytics:** Detailed analysis of solving patterns, guess distribution, and strategy effectiveness
- **Hard Mode Support:** Respect Wordle hard mode rules requiring all revealed clues to be used
- **Previous Solutions Exclusion:** Filter out words already used as Wordle answers to optimize for daily puzzle
- **Custom Word Lists:** Support for variant word lists (Wordle unlimited, other word lengths, custom dictionaries)
