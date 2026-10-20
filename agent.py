"""City Explorer agent - a hand-written ReAct loop on the Claude API.

ReAct = Reason + Act, repeated:

    user question
        |
        v
  +-> Claude THINKS, then either answers or asks for a tool (ACT)
  |       |
  |       v  stop_reason == "tool_use"
  |   WE run the tool in Python (OBSERVATION)
  |       |
  |       v
  +-- send the result back to Claude
          ...until stop_reason == "end_turn" -> final answer

Run:  python agent.py   (then type your question)
"""

import json
import logging

from pathlib import Path

import anthropic
from dotenv import load_dotenv

from tools import CITIES, TOOL_FUNCTIONS, TOOLS, ToolError

load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("city-explorer")

SYSTEM_PROMPT = """You are City Explorer, you MUST answer in a Kannada and in a poetic way

Use the tools to get facts about a city - never guess the weather or time.
Check the weather before suggesting attractions, so you can pick indoor
places for bad weather and outdoor places for good weather.
Keep the final answer short: 3-5 sentences."""


class CityExplorerAgent:
    def __init__(self, model: str = "claude-opus-5-5", max_steps: int = 8):
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        self.model = model
        self.max_steps = max_steps  # safety net: stop runaway loops

    # ---- the loop -------------------------------------------------------

    def run(self, question: str) -> str:
        # The API is stateless: this list IS the agent's memory. Every step
        # we resend the whole thing, plus whatever got added.
        messages = [{"role": "user", "content": question}]
        log.info("\n USER: %s", question)

        for step in range(1, self.max_steps + 1):
            log.info("\n========== STEP %d  (sending %d messages) ==========",
                     step, len(messages))

            # 1. REASON: ask Claude what to do next.
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
                # "summarized" makes Claude's reasoning readable in the logs.
                thinking={"type": "adaptive", "display": "summarized"},
                output_config={"effort": "low"},  # simple task, keep it cheap
                # If a safety check declines, the API retries on another model.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            self._log_response(response)

            # 2. Keep Claude's whole reply (thinking + text + tool calls) in
            #    the history. Thinking blocks must go back unchanged.
            messages.append({"role": "assistant", "content": response.content})

            # 3. Done? Claude answered without asking for a tool.
            if response.stop_reason == "end_turn":
                answer = "".join(b.text for b in response.content if b.type == "text")
                log.info("\n FINAL ANSWER after %d steps", step)
                return answer

            if response.stop_reason != "tool_use":
                raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")

            # 4. ACT: run every tool Claude asked for (it may ask for several
            #    at once), then send ALL results back in ONE user message.
            tool_results = [self._run_tool(b) for b in response.content
                            if b.type == "tool_use"]
            messages.append({"role": "user", "content": tool_results})
            # ...and loop: Claude now sees the observations and reasons again.

        raise RuntimeError(f"Gave up after {self.max_steps} steps")

    # ---- tool execution -------------------------------------------------

    def _run_tool(self, block) -> dict:
        """Run one tool_use block and return a tool_result block."""
        log.info(" ACT:     %s(%s)   [id=%s]", block.name,
                 json.dumps(block.input), block.id)
        result = {"type": "tool_result", "tool_use_id": block.id}  # ids must match
        try:
            func = TOOL_FUNCTIONS[block.name]
            output = func(**block.input)
            result["content"] = json.dumps(output)
            log.info(" OBSERVE: %s", result["content"])
        except (ToolError, KeyError, TypeError) as e:
            # Don't crash - tell Claude what went wrong so it can recover.
            result["content"] = f"Error: {e}"
            result["is_error"] = True
            log.info(" OBSERVE: (error) %s", e)
        return result

    # ---- logging --------------------------------------------------------

    def _log_response(self, response) -> None:
        for block in response.content:
            if block.type == "thinking" and block.thinking:
                log.info(" THINK:   %s", block.thinking.strip().replace("\n", " "))
            elif block.type == "text" and block.text.strip():
                log.info(" SAY:     %s", block.text.strip())
            elif block.type == "tool_use":
                log.info(" WANTS:   tool %s", block.name)
        u = response.usage
        log.info(" stop_reason=%s | tokens in=%d out=%d",
                 response.stop_reason, u.input_tokens, u.output_tokens)


def main() -> None:
    cities = ", ".join(c.title() for c in CITIES)
    print(f"City Explorer - I know about: {cities}")
    print("Ask about weather, local time or things to do. Type 'quit' to exit.")
    print("Examples:\n"
          "  - Is it a good day to visit Paris? What should I do?\n"
          "  - What time is it in Tokyo, and is it sunny?\n"
          "  - Compare the weather in Berlin and Paris.\n"
          "  - What can I do in Rome?   (not in the data - watch the error)")

    agent = CityExplorerAgent()
    while True:
        try:
            question = input("\nYour question> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"quit", "exit", "q"}:
            break
        if question:
            print("\n" + agent.run(question))


if __name__ == "__main__":
    main()
