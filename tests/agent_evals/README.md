# Agent evaluation harness

The default pytest suite includes the harness self-test and excludes the CLI
scenarios. Run the deterministic oracle scenarios explicitly with:

```sh
python -m pytest -m agent_eval tests/agent_evals/test_scenarios.py
```

Real-model adapters can implement the `AgentDriver` protocol in `harness.py`.
Tests that call one must carry both `@pytest.mark.agent_eval` and
`@pytest.mark.real_agent_eval`, and require `REPORTKIT_AGENT_EVAL=1`:

```sh
REPORTKIT_AGENT_EVAL=1 python -m pytest -m "agent_eval and real_agent_eval" tests/agent_evals
```

No model provider is coupled to the harness. The checked-in oracle is fully
scripted and never reads credentials or makes network calls.
