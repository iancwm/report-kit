# Quiz example

True/false (circle one) and multiple-choice primitives from
`latex_templates/reportkit-quiz.sty`, used under `technical-report` x `default`.

- `quiz.tex` builds the student sheet (nothing marked).
- `quiz-key.tex` builds the same source as an answer key: the correct
  True/False word or choice letter is circled and `\quizexplain` text shows.

Primitives: `\quizheader`, `\quizsection{title}{directions}`,
`\quiztf{statement}{T|F}[why]`, `\begin{quizmc}{letter}{question}` with
`\quizopt{choice}`, `\quizexplain{text}`, `\quizscore`.

Load with `\usepackage{reportkit-quiz}` (or `[answers]`). All content is invented.
