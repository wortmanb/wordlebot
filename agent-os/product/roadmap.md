# Product Roadmap

1. [ ] Information Gain Calculator — Implement entropy-based scoring that calculates expected information gain for each candidate word, measuring how effectively each guess partitions the solution space. Include API to compute partition sizes and entropy values for ranking. `M`

2. [ ] AI Strategy Core — Integrate Claude API to power strategic decision-making, including prompt engineering for guess evaluation, context management for game state, and structured output parsing for suggestions with reasoning. `L`

3. [ ] Multi-Step Lookahead Engine — Build minimax evaluation system that simulates 2-3 moves ahead, evaluating expected guess counts across different response scenarios to identify optimal paths that minimize worst-case outcomes. `L`

4. [ ] Explainable AI Interface — Create display system that shows AI reasoning, information metrics (entropy, partition sizes), alternative comparisons, and trade-off analysis so users understand why suggestions are optimal. `M`

5. [ ] Strategy Mode Selection — Implement configurable strategy modes (aggressive, safe, balanced) that adjust decision weights between minimizing average guesses versus worst-case scenarios, with YAML-based configuration. `S`

6. [ ] Performance Analytics Dashboard — Build tracking and analysis for game statistics including guess distribution, AI vs manual comparison, strategy effectiveness metrics, and historical performance trends with CSV export. `M`

7. [ ] Hard Mode Compliance — Add validation and filtering logic to enforce Wordle hard mode rules, ensuring all revealed hints (green/yellow) are used in subsequent guesses with appropriate constraint tracking. `S`

8. [ ] Partition Visualization — Create visual display of how candidate guesses split the solution space into different response patterns, showing bucket sizes and distribution to inform strategic choices. `M`

9. [ ] Adaptive Strategy Learning — Implement feedback loop that tracks AI suggestion outcomes and adjusts weighting factors based on observed performance patterns across multiple games. `XL`

10. [ ] Response Simulator — Build automated testing system that simulates complete games against word list, benchmarking different strategies and measuring average/worst-case performance across all solutions. `M`

11. [ ] Custom Dictionary Support — Extend configuration to support multiple word lists (Wordle variants, different word lengths, custom dictionaries) with per-list COCA mapping and frequency data. `S`

12. [ ] Interactive Strategy Tuning — Create interface for users to adjust strategy parameters in real-time, see immediate impact on suggestions, and save personalized strategy profiles. `M`

> Notes
> - Items ordered to build foundational AI capabilities first, then add sophistication and user features
> - Information gain calculation (item 1) is prerequisite for AI strategy engine (item 2)
> - Lookahead engine (item 3) depends on information gain and AI core being functional
> - Analytics and visualization features (items 6, 8) enhance but don't block core AI functionality
> - Each item represents end-to-end functionality that can be tested independently
> - Strategy modes (item 5) and hard mode (item 7) are relatively independent and can be prioritized flexibly
