"""Feature-flagged ML/LLM-assisted observers (Phase 1, DISABLED by default).

What this module is
-------------------
Assisted observers are *probabilistic indicators for human review*, never
findings. They emit the same gate-compatible observation contract as the
rule-based observers (neutral label, ``confidence.score`` in [0, 1],
non-empty versioned ``confidence.model_id``, ``method``, ``category``,
``evidence`` dict, deterministic ``cue_id``), plus provenance in the
evidence so a reviewer can see exactly what produced each cue.

What runs by default
---------------------
Nothing. Assisted observers are OFF by default: no adapter is registered
by importing this module, no network call is made, and no external model
is invoked. They run only when *both* of these hold:

1. an explicit opt-in is given for the run -- the ``enable_assisted``
   parameter on :class:`cueliez.observations.runner.ObservationRunner`
   (``default_runner(enable_assisted=True)`` / ``full_runner(...)``), the
   existing ``--enable-assisted`` CLI flag (which registers the baseline
   adapter and merges it), or ``enabled=True`` passed to
   :func:`run_assisted_observers` / :func:`merge_assisted_observations`;
   or the deployment env var ``CUELIEZ_ASSISTED_OBSERVERS=1``; and
2. an adapter is registered (or, for the runner default path, the
   deterministic multi-signal baseline described below).

The deterministic multi-signal baseline
----------------------------------------
:func:`make_multi_signal_assisted_adapter` is the real baseline adapter.
It is deterministic, stdlib-only, and makes no external ML/network call:
it counts hedging, vagueness, and distancing marker families in one
subject turn (reusing the linguistic pattern lists) and emits a single
neutral ``multi_signal_language_pattern`` observation only when at least
two distinct marker families converge on the same turn. Its score is a
deterministic signal-strength combination of the family count and the
marker counts (``0.4 + 0.12 * families + 0.02 * total_markers``, capped
at 1.0); it is *not* a probability of any finding. Evidence carries the
per-family counts, the matched markers, the quoted source text, and full
provenance (adapter name/version, model id, inputs used).

Fail-closed behaviour
---------------------
- Disabled / no adapter registered -> no assisted observations, and the
  rule-based run is unaffected.
- An adapter that raises, returns a non-``ObservationResult`` value, or
  returns no usable observations -> its output is dropped and the run
  continues with the rule-based observations.
- An adapter that returns verdict-shaped data (a forbidden label, or
  verdict-shaped keys/values in evidence, cue, or confidence) -> the
  offending observations are filtered out before they can reach a
  package; see :func:`is_verdict_shaped_observation`. A sealed package
  therefore never receives assisted verdict-shaped data from this path.

Future local-model path (documented here; no model is bundled)
--------------------------------------------------------------
To plug in a real local model later, implement the
:class:`AssistedObserver` protocol (or pass a plain callable with the
same shape) and register it with :func:`register_assisted_observer`:

1. Implement ``observe(transcript) -> ObservationResult``. The method
   must run locally (no network call to an unapproved service), must
   return only gate-compatible observations (neutral label, score in
   [0, 1], evidence dict), and must never return verdict-shaped data --
   this module filters such output, and the seal gate rejects it too.
2. Pin the model: give the observer a versioned ``method_id`` (for
   example ``cueliez.observations.assisted.<name>/v1``) and an
   :class:`AssistedModelProvenance` (provider, model, version, adapter
   version, optional prompt/adapter hash). The provenance is recorded
   in every emitted observation's evidence.
3. Register it at deployment time with
   ``register_assisted_observer(name, observer, provenance)`` and enable
   it explicitly per run (see above). Registration alone never enables
   anything.
4. If the model file/weights are absent, or the model fails to load,
   the observer must raise or return an empty result: the run then
   fails closed (no assisted observations) instead of substituting a
   guess. Never fall back to inventing a score.
5. Keep the model and its weights pinned by version; a version change
   is a new ``method_id``/provenance, never a silent swap.

No external ML calls happen in the default/production path, and this
module performs no network I/O at all.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Sequence, runtime_checkable

from .base import FORBIDDEN_LABELS, Observation, ObservationResult

# Feature flag: default OFF. Enable only via explicit deployment config
# (approved/on-prem controls) or an explicit per-run opt-in. The value is
# re-read from the environment on every call (see _env_enabled) so tests
# and deployments can toggle it without re-importing; the module-level
# name below is the import-time snapshot kept for backwards compatibility.
ASSISTED_OBSERVERS_ENABLED = os.environ.get("CUELIEZ_ASSISTED_OBSERVERS", "").strip() == "1"


def _env_enabled() -> bool:
    return os.environ.get("CUELIEZ_ASSISTED_OBSERVERS", "").strip() == "1"


def is_assisted_enabled(explicit: bool | None = None) -> bool:
    """Resolve the opt-in: an explicit per-run value wins, else the env flag."""
    if explicit is not None:
        return bool(explicit)
    return bool(ASSISTED_OBSERVERS_ENABLED or _env_enabled())


# --- Verdict-shaped output guard -------------------------------------------
# Tokens/keys that must never appear in assisted output. They are checked
# against labels, cue text, evidence keys/values, and confidence keys.
# (The words below appear here only as a rejection list, mirroring
# base.FORBIDDEN_LABELS and gates.FORBIDDEN_OBSERVATION_LABELS.)
_FORBIDDEN_WORDS = frozenset({"lying", "lie", "deception_confirmed", "guilty", "truthful", "deceptive", "dishonest", "honest", "diagnosis"})
_FORBIDDEN_KEYS = frozenset({"truth_score", "deception_confirmed", "guilty", "diagnosis", "verdict"})
_FORBIDDEN_WORD_RE = re.compile(r"\b(lying|deception_confirmed|guilty|truth_score|diagnosis)\b", re.I)


def _string_has_forbidden_word(value: Any) -> bool:
    return isinstance(value, str) and bool(_FORBIDDEN_WORD_RE.search(value))


def _mapping_has_forbidden_content(mapping: Mapping[str, Any]) -> bool:
    for key, value in mapping.items():
        k = str(key).strip().lower()
        if k in _FORBIDDEN_KEYS or k in _FORBIDDEN_WORDS:
            return True
        if _string_has_forbidden_word(value):
            return True
        if isinstance(value, Mapping) and _mapping_has_forbidden_content(value):
            return True
        if isinstance(value, (list, tuple)) and any(_string_has_forbidden_word(v) for v in value):
            return True
    return False


def is_verdict_shaped_observation(obs: Mapping[str, Any]) -> bool:
    """True if an observation dict is verdict-shaped and must be rejected.

    Checks the label, cue text, confidence keys, and evidence keys/values.
    """
    if not isinstance(obs, Mapping):
        return True
    label = str(obs.get("label") or "").strip().lower()
    if label in FORBIDDEN_LABELS or label in _FORBIDDEN_WORDS or _string_has_forbidden_word(label):
        return True
    if _string_has_forbidden_word(obs.get("cue")):
        return True
    conf = obs.get("confidence")
    if isinstance(conf, Mapping) and _mapping_has_forbidden_content(conf):
        return True
    evidence = obs.get("evidence")
    if isinstance(evidence, Mapping) and _mapping_has_forbidden_content(evidence):
        return True
    return False


# --- Provenance ------------------------------------------------------------

@dataclass(frozen=True)
class AssistedModelProvenance:
    provider: str
    model: str
    version: str
    adapter_version: str = "v0"
    prompt_hash: str = ""

    @property
    def model_id(self) -> str:
        base = f"{self.provider}/{self.model}@{self.version}#{self.adapter_version}"
        return f"{base}+{self.prompt_hash}" if self.prompt_hash else base

    def to_dict(self) -> Dict[str, str]:
        return {
            "provider": self.provider,
            "model": self.model,
            "version": self.version,
            "adapter_version": self.adapter_version,
            "prompt_hash": self.prompt_hash,
            "model_id": self.model_id,
        }


MULTI_SIGNAL_METHOD_ID = "cueliez.observations.assisted.multi_signal/v1"
MULTI_SIGNAL_ADAPTER_NAME = "multi_signal"
MULTI_SIGNAL_ADAPTER_VERSION = "v1"
MULTI_SIGNAL_PROVENANCE = AssistedModelProvenance(
    provider="cueliez",
    model="multi_signal",
    version="v1",
    adapter_version="v1",
)


def _provenance_dict(
    *,
    adapter_name: str,
    adapter_version: str,
    method_id: str,
    provenance: AssistedModelProvenance | None,
    inputs_used: Sequence[str],
) -> Dict[str, Any]:
    prov: Dict[str, Any] = {
        "adapter": adapter_name,
        "adapter_version": adapter_version,
        "method": method_id,
        "model_id": method_id,
        "version": (provenance.version if provenance is not None else adapter_version),
        "inputs_used": list(inputs_used),
    }
    if provenance is not None:
        prov["provider"] = provenance.provider
        prov["model"] = provenance.model
        prov["provenance_model_id"] = provenance.model_id
        if provenance.prompt_hash:
            prov["prompt_hash"] = provenance.prompt_hash
    return prov


def _attach_provenance(
    observation: Observation,
    *,
    adapter_name: str,
    adapter_version: str,
    method_id: str,
    provenance: AssistedModelProvenance | None,
    inputs_used: Sequence[str],
) -> None:
    """Stamp provenance onto an observation's evidence (in place)."""
    if observation.evidence is None:
        observation.evidence = {}
    prov = _provenance_dict(
        adapter_name=adapter_name,
        adapter_version=adapter_version,
        method_id=method_id,
        provenance=provenance,
        inputs_used=inputs_used,
    )
    observation.evidence.setdefault("assisted", True)
    observation.evidence.setdefault("adapter", adapter_name)
    observation.evidence.setdefault("adapter_version", adapter_version)
    observation.evidence.setdefault("model_id", method_id)
    observation.evidence["assisted_provenance"] = prov
    # inputs_used: keep the adapter's own list when present, else the
    # provenance-derived list.
    observation.evidence.setdefault("inputs_used", list(inputs_used))


def _filter_and_stamp_result(
    result: ObservationResult,
    *,
    adapter_name: str,
    adapter_version: str,
    provenance: AssistedModelProvenance | None,
) -> ObservationResult:
    """Drop verdict-shaped observations, stamp provenance on the rest.

    Never raises for bad adapter output: filtering is fail-closed.
    """
    kept: List[Observation] = []
    dropped = 0
    for obs in result.observations or []:
        try:
            obs_dict = obs.to_dict()
        except Exception:
            dropped += 1
            continue
        if is_verdict_shaped_observation(obs_dict):
            dropped += 1
            continue
        method_id = str(obs_dict.get("method") or result.method or "")
        inputs = list((obs_dict.get("evidence") or {}).get("inputs_used") or ["transcript"])
        _attach_provenance(
            obs,
            adapter_name=adapter_name,
            adapter_version=adapter_version,
            method_id=method_id,
            provenance=provenance,
            inputs_used=inputs,
        )
        kept.append(obs)
    out = ObservationResult(method=result.method, observations=kept, notes=list(result.notes or []))
    if dropped:
        out.notes.append(f"assisted_verdict_shaped_filtered:{dropped}")
    return out


# --- Adapter interface ------------------------------------------------------

@runtime_checkable
class AssistedObserver(Protocol):
    """Protocol for a pluggable assisted observer (incl. a future local model).

    Implementations must: run locally with no unapproved network call;
    return only gate-compatible, neutral observations; never return
    verdict-shaped data (filtered here and rejected at seal); and fail
    closed (raise, or return an empty ObservationResult) when the model
    is absent or cannot run. ``method_id`` and ``provenance`` pin the
    exact model/adapter version so output is reproducible.
    """

    method_id: str

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        ...

    @property
    def provenance(self) -> AssistedModelProvenance | None:  # noqa: D102 - protocol
        ...


# A plain callable with the same shape also counts as an adapter.
AssistedAdapter = Callable[[Sequence[Mapping[str, Any]]], ObservationResult]

_REGISTRY: List[tuple[str, AssistedAdapter, AssistedModelProvenance | None]] = []


def _normalize_adapter(
    name: str, adapter: Any
) -> tuple[AssistedAdapter, AssistedModelProvenance | None, str, str]:
    """Accept a callable or an AssistedObserver instance; return a callable.

    Returns (callable, provenance, adapter_version, method_id-or-"").
    """
    provenance: AssistedModelProvenance | None = None
    adapter_version = "v1"
    method_id = ""
    if hasattr(adapter, "observe") and callable(getattr(adapter, "observe")) and not callable(adapter):
        inst = adapter
        method_id = str(getattr(inst, "method_id", "") or "")
        prov = getattr(inst, "provenance", None)
        if isinstance(prov, AssistedModelProvenance):
            provenance = prov
            adapter_version = prov.adapter_version or adapter_version

        def _call(transcript: Sequence[Mapping[str, Any]], _inst: Any = inst) -> ObservationResult:
            return _inst.observe(transcript)

        return _call, provenance, adapter_version, method_id
    if not callable(adapter):
        raise ValueError("adapter must be callable or an AssistedObserver with .observe()")
    method_id = str(getattr(adapter, "method_id", "") or "")
    prov = getattr(adapter, "provenance", None)
    if isinstance(prov, AssistedModelProvenance):
        provenance = prov
        adapter_version = prov.adapter_version or adapter_version
    return adapter, provenance, adapter_version, method_id


def register_assisted_observer(
    name: str,
    adapter: Any,
    provenance: AssistedModelProvenance | None = None,
) -> None:
    """Register an assisted adapter (deployment-time). No effect unless enabled.

    Re-registering the same name replaces the previous adapter (so a
    repeated opt-in, e.g. one CLI run after another, never stacks
    duplicate adapters). Accepts a plain callable or an AssistedObserver
    instance. An explicit ``provenance`` overrides any provenance carried
    by the adapter itself.
    """
    if not name or (not callable(adapter) and not callable(getattr(adapter, "observe", None))):
        raise ValueError("name and callable adapter (or AssistedObserver) required")
    _callable, adapter_prov, _version, _method = _normalize_adapter(str(name), adapter)
    prov = provenance if provenance is not None else adapter_prov
    if prov is not None and not str(prov.model_id).strip():
        raise ValueError("provenance.model_id must be non-empty")
    # Attach provenance/version to the stored callable so the runner can
    # stamp it onto observations even for plain callables.
    try:
        setattr(_callable, "_assisted_provenance", prov)  # type: ignore[attr-defined]
    except Exception:
        pass
    _REGISTRY[:] = [entry for entry in _REGISTRY if entry[0] != str(name)]
    _REGISTRY.append((str(name), _callable, prov))


def clear_assisted_registry() -> None:
    _REGISTRY.clear()


class AssistedObserverPrototype:
    """Base for future assisted observers. Disabled by default; no network/ML execution."""

    method_id = "cueliez.observations.assisted.prototype/v0"
    enabled_flag_name = "ASSISTED_OBSERVERS_ENABLED"

    def is_enabled(self) -> bool:
        return bool(is_assisted_enabled())

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        # Fail closed: no external calls; emit nothing unless explicitly enabled and implemented.
        result = ObservationResult(method=self.method_id)
        if not self.is_enabled():
            result.notes.append("assisted_observers_disabled")
            return result
        result.notes.append("assisted_observer_not_implemented")
        return result


# --- Deterministic multi-signal baseline adapter ----------------------------

def make_multi_signal_assisted_adapter(
    provenance: AssistedModelProvenance | None = None,
):
    """Factory for a deterministic, no-external-ML assisted adapter.

    Combines hedging + vagueness + distancing markers into a single
    multi-signal cue when at least two distinct marker families are
    present on one subject turn. No network/ML calls; safe to register
    only in approved deployments. Score is a deterministic signal
    strength (see module docstring), not a probability of any finding.
    """
    from .base import is_subject_turn, make_observation, source_span
    from .linguistic import (
        DISTANCING_PATTERNS,
        VAGUE_PATTERNS,
        _WEAK_VAGUE_PATTERNS,
        _count_patterns,
        _hedge_count_adjusted,
        _words,
    )

    prov = provenance if provenance is not None else MULTI_SIGNAL_PROVENANCE

    def adapter(transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=MULTI_SIGNAL_METHOD_ID)
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            from .base import text_of

            text = text_of(turn)
            words = _words(text)
            if len(words) < 6:
                continue
            # Hedge count excludes time approximations ("around nine-thirty"),
            # matching the HedgingObserver hardening.
            hc, hf = _hedge_count_adjusted(text)
            vc, vf = _count_patterns(text, VAGUE_PATTERNS)
            dc, df = _count_patterns(text, DISTANCING_PATTERNS)
            # Weak vague fillers alone do not count as the vagueness family.
            strong_vague = [p for p in vf if p not in _WEAK_VAGUE_PATTERNS]
            families_present: List[str] = []
            if hc > 0:
                families_present.append("hedging")
            if strong_vague:
                families_present.append("vagueness")
            if dc > 0:
                families_present.append("distancing")
            if len(families_present) < 2:
                continue
            total = hc + vc + dc
            score = min(1.0, 0.4 + 0.12 * len(families_present) + 0.02 * total)
            ev: Dict[str, Any] = {
                "hedge_count": hc,
                "vague_count": vc,
                "distancing_count": dc,
                "families": len(families_present),
                "families_present": list(families_present),
                "word_count": len(words),
                "hedge_markers": hf[:10],
                "vague_markers": vf[:10],
                "distancing_markers": df[:10],
                "inputs_used": list(families_present),
                "assisted": True,
                "adapter": MULTI_SIGNAL_ADAPTER_NAME,
                "adapter_version": MULTI_SIGNAL_ADAPTER_VERSION,
                "model_id": MULTI_SIGNAL_METHOD_ID,
            }
            ev.update(source_span(turn, i))
            ev["assisted_provenance"] = _provenance_dict(
                adapter_name=MULTI_SIGNAL_ADAPTER_NAME,
                adapter_version=MULTI_SIGNAL_ADAPTER_VERSION,
                method_id=MULTI_SIGNAL_METHOD_ID,
                provenance=prov,
                inputs_used=families_present,
            )
            result.observations.append(make_observation(
                label="multi_signal_language_pattern",
                score=score,
                method_id=MULTI_SIGNAL_METHOD_ID,
                category="linguistic",
                evidence=ev,
                cue="Multiple linguistic marker families appear in one response; consider probing for specifics.",
                turn_index=i,
                priority="normal",
            ))
        return result

    adapter.method_id = MULTI_SIGNAL_METHOD_ID  # type: ignore[attr-defined]
    adapter.adapter_name = MULTI_SIGNAL_ADAPTER_NAME  # type: ignore[attr-defined]
    adapter.adapter_version = MULTI_SIGNAL_ADAPTER_VERSION  # type: ignore[attr-defined]
    adapter.provenance = prov  # type: ignore[attr-defined]
    return adapter


class MultiSignalAssistedObserver:
    """AssistedObserver-protocol wrapper around the multi-signal baseline.

    Lets the runner (or a future deployment) use the baseline as a proper
    observer object with a pinned method id and provenance, instead of a
    bare callable.
    """

    method_id = MULTI_SIGNAL_METHOD_ID

    def __init__(self, provenance: AssistedModelProvenance | None = None) -> None:
        self._provenance = provenance if provenance is not None else MULTI_SIGNAL_PROVENANCE
        self._adapter = make_multi_signal_assisted_adapter(self._provenance)

    @property
    def provenance(self) -> AssistedModelProvenance:
        return self._provenance

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        return self._adapter(transcript)


# --- Running / merging -------------------------------------------------------

def _run_one_adapter(
    name: str, adapter: AssistedAdapter, provenance: AssistedModelProvenance | None, transcript: Sequence[Mapping[str, Any]]
) -> ObservationResult | None:
    try:
        res = adapter(transcript)
    except Exception:
        # Fail closed for assisted path: do not break the rule-based run.
        return None
    if not isinstance(res, ObservationResult):
        return None
    prov = provenance
    if prov is None:
        stored = getattr(adapter, "_assisted_provenance", None)
        if isinstance(stored, AssistedModelProvenance):
            prov = stored
        else:
            carried = getattr(adapter, "provenance", None)
            if isinstance(carried, AssistedModelProvenance):
                prov = carried
    adapter_version = str(getattr(adapter, "adapter_version", "") or (prov.adapter_version if prov else "v1") or "v1")
    return _filter_and_stamp_result(res, adapter_name=name, adapter_version=adapter_version, provenance=prov)


def run_assisted_observers(transcript: Sequence[Mapping[str, Any]], *, enabled: bool | None = None) -> List[ObservationResult]:
    """Run registered assisted adapters only when explicitly enabled.

    Default: empty (no external ML). Registry-only: if nothing is
    registered, returns [] even when enabled -- use
    :func:`run_default_assisted_observers` for the runner path, which
    falls back to the deterministic multi-signal baseline.
    """
    on = is_assisted_enabled(enabled)
    if not on or not _REGISTRY:
        return []
    out: List[ObservationResult] = []
    for name, adapter, prov in list(_REGISTRY):
        filtered = _run_one_adapter(name, adapter, prov, transcript)
        if filtered is not None:
            out.append(filtered)
    return out


def run_default_assisted_observers(
    transcript: Sequence[Mapping[str, Any]], *, enabled: bool | None = None
) -> List[ObservationResult]:
    """Runner path: registered adapters if any, else the multi-signal baseline.

    Still off unless explicitly enabled. The baseline fallback means
    ``ObservationRunner(enable_assisted=True)`` works end-to-end without
    the caller having to register anything, and without mutating the
    global registry.
    """
    on = is_assisted_enabled(enabled)
    if not on:
        return []
    if _REGISTRY:
        return run_assisted_observers(transcript, enabled=True)
    adapter = make_multi_signal_assisted_adapter()
    filtered = _run_one_adapter(
        MULTI_SIGNAL_ADAPTER_NAME, adapter, MULTI_SIGNAL_PROVENANCE, transcript
    )
    return [filtered] if filtered is not None else []


def merge_assisted_observations(
    observations: List[Dict[str, Any]],
    transcript: Sequence[Mapping[str, Any]],
    *,
    enabled: bool | None = None,
) -> List[Dict[str, Any]]:
    """Opt-in merge of registered assisted observations (default off). Additive; no external ML by default."""
    results = run_assisted_observers(transcript, enabled=enabled)
    out = list(observations)
    for r in results:
        out.extend(r.to_dicts())
    return out


def merge_default_assisted_observations(
    observations: List[Dict[str, Any]],
    transcript: Sequence[Mapping[str, Any]],
    *,
    enabled: bool | None = None,
) -> List[Dict[str, Any]]:
    """Opt-in merge using registered adapters, or the multi-signal baseline if none are registered (default off)."""
    results = run_default_assisted_observers(transcript, enabled=enabled)
    out = list(observations)
    for r in results:
        out.extend(r.to_dicts())
    return out
