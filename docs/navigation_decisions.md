### `docs/navigation_decisions.md`

# Navigation Decision Algorithm

## Introduction

AutoSo's ability to accurately detect what the speaker is saying is only half of the equation. The other half is taking the right action based on that information: **Should it advance the slide (`forward`) or stay on the current one (`stay`)?**

This decision is made by a complex yet highly effective logic within the `_determine_navigation_action` method of the `RealtimeNavigator` class in `app.py`. This logic looks not only at the current match but also at the overall context of the presentation and potential future steps.

## The Decision-Making Mechanism

The decision algorithm uses Python's `match` statement to evaluate three main states and their sub-conditions. Each decision is based on the state of the following variables:

-   `is_current_source`: Is the source of the matched chunk the currently expected transcript?
-   `early_forward`: Is the `early_forward` flag of the current transcript `true`?
-   `is_next_source_different`: Does the next chunk come from a different transcript? (This indicates the end of the current transcript has been reached.)
-   `expected_idx`: The index of the transcript to which the matched chunk belongs.

### Case 1: `Stay` (Remain on the Current Slide)

This is the system's safest and default action. A `stay` decision is made in the following scenarios:

-   **Scenario A: Standard Flow**
    -   The matched chunk belongs to the current transcript.
    -   The speaker is talking about something in the middle of the slide (`is_next_source_different` is False).
    -   The `early_forward` flag is `false` or its conditions are not triggered.
    -   **Result:** The system understands that the speaker is continuing to talk about the current slide and does nothing.

-   **Scenario B: Backward Match**
    -   When the speaker hesitates and repeats a word from a previous sentence, the system might accidentally match a chunk belonging to a past transcript.
    -   The `current_idx < expected_idx` check in the code catches this. If the match comes from a past index (`expected_idx` is smaller than the current index), the system intelligently decides to `stay`, maintaining its current position instead of going backward in the presentation.

### Case 2: `Forward` (Direct Jump to a Future Transcript)

This case handles situations where the speaker jumps ahead in the script or skips some parts.

-   **Condition:** `is_current_source` is `False`, meaning the matched chunk is **not** from the current transcript but from a future one.
-   **Logic:** The system concludes, "This is not where I expected to be; the speaker has moved on to a future topic."
-   **Action:** The system advances the presentation directly to the slide of the transcript to which the matched chunk belongs. This ensures the presentation stays in sync with the speaker.

### Case 3: `Forward` (Triggering the `early_forward` Condition)

This is AutoSo's most advanced decision mechanism, designed to compensate for STT delays and provide a smooth presentation experience. For this decision to be made, the following **three conditions must be met simultaneously**:

1.  **`is_current_source` == `True`:** The match is within the current transcript. The speaker is still talking about the topic of the current slide.
2.  **`current_transcript.get("early_forward", False)` == `True`:** The current transcript has been marked by the LLM as "suitable for a quick transition." This means it's a fluid transition point without a need for a special pause.
3.  **`is_next_source_different` == `True`:** The matched chunk contains the final words of the current transcript. Technically, this is detected by the next chunk's source being a different `transcript_id`.

-   **Logic:** When these three conditions come together, the system concludes: "The speaker has just said the last sentence of a slide suitable for a quick transition. There's no need to waste time waiting to hear the first word of the next slide."
-   **Action:** The system proactively makes a `forward` decision and moves to the next slide. This ensures that the correct slide is already on the screen the moment the speaker utters the first word of the new slide, creating perfect synchronization.

This three-tiered decision mechanism makes AutoSo much more than a simple text matcher; it turns it into an autonomous operator that understands the context of the presentation and can make intelligent decisions.