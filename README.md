# City Explorer Agent

A small learning project: a hand-written **ReAct loop** (Reason → Act → Observe) on the Claude API, with logging at every step so you can see exactly how tool calls work.

- `agent.py`: system prompt and the `CityExplorerAgent` class. `run()` is the loop and `_run_tool()` runs the tools.
- `tools.py`: dummy data for Paris, Berlin and Tokyo, plus three tools: `get_weather`, `get_local_time`, `find_attractions`.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # then put your ANTHROPIC_API_KEY in .env
.venv/bin/python agent.py
```

Type a question, for example "Is it a good day to visit Paris? What should I do?". Type `quit` to exit.
