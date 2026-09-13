"""
Full-application integration tests for Shark Tank AI, using Streamlit's
`AppTest` harness (`streamlit.testing.v1.AppTest`) to drive `app.py`
exactly the way a browser would, without a browser.

Unlike `tests/test_session_director.py` (which exercises
`SharkTankOrchestrator` directly, bypassing Streamlit entirely), these
tests catch bugs that only exist in the `ui/` <-> `orchestrator/` wiring
itself -- which is exactly where Release 0.4's proposal-persistence bug
lived (Release 0.4.1 spec section 4). Automated coverage here
significantly reduces, but does not replace, the manual test checklist
in the Release 0.4.1 spec section 18: `AppTest` runs each script pass
synchronously and cannot verify actual browser rendering (fonts,
layout, avatars rendering as emoji, etc.).
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

SAMPLE_PROPOSAL = "We sell eco-friendly packaging to grocery chains."

_APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


def _new_app() -> AppTest:
    return AppTest.from_file(_APP_PATH)


def _started_app() -> AppTest:
    """Launch the app, submit `SAMPLE_PROPOSAL` as text, and click Start."""
    at = _new_app()
    at.run(timeout=15)
    at.text_area[0].set_value(SAMPLE_PROPOSAL).run(timeout=15)
    at.button(key="start_session_button").click().run(timeout=15)
    assert not at.exception
    return at


def _answer(at: AppTest, text: str = "A thoughtful answer.") -> AppTest:
    at.chat_input(key="founder_chat_input").set_value(text).run(timeout=15)
    assert not at.exception
    return at


# ---------------------------------------------------------------------
# Proposal types (Audio/Video removal)
# ---------------------------------------------------------------------


def test_market_reality_summary_expander_renders_without_error():
    at = _started_app()
    assert not at.exception
    labels = [e.label for e in at.expander]
    assert "Market Reality Research" in labels


def test_only_text_and_pdf_proposal_types_are_offered():
    at = _new_app()
    at.run(timeout=15)
    assert at.radio[0].options == ["Text", "PDF"]


# ---------------------------------------------------------------------
# Proposal persistence (Release 0.4.1 spec section 4)
# ---------------------------------------------------------------------


def test_proposal_survives_start():
    at = _started_app()
    assert at.session_state["proposal_content"] == SAMPLE_PROPOSAL
    assert at.session_state["proposal_uploaded"] is True


def test_proposal_is_available_to_the_active_session():
    at = _started_app()
    director = at.session_state["_session_director"]
    assert director is not None
    # The Session Director's own Pitch (not just the UI's
    # proposal_content copy) is what the committee is actually
    # questioning -- confirm it was built from the founder's exact
    # submitted text, not empty/default/stale data.
    assert director.pitch is not None
    assert director.pitch.description == SAMPLE_PROPOSAL
    assert director.phase.value == "question_round"


def test_proposal_is_cleared_on_full_reset():
    at = _started_app()
    at.button(key="end_session_button").click().run(timeout=15)
    assert not at.exception
    assert at.session_state["proposal_content"] == ""
    assert at.session_state["proposal_uploaded"] is False


def test_new_session_does_not_inherit_old_proposal_after_reset():
    at = _started_app()
    at.button(key="end_session_button").click().run(timeout=15)

    # Start is disabled again until a new proposal is entered.
    assert at.button(key="start_session_button").disabled is True

    at.text_area[0].set_value("A completely different pitch about solar panels.").run(timeout=15)
    at.button(key="start_session_button").click().run(timeout=15)

    assert not at.exception
    assert at.session_state["proposal_content"] == "A completely different pitch about solar panels."


# ---------------------------------------------------------------------
# Chat state
# ---------------------------------------------------------------------


def test_messages_come_from_conversation_state_not_hardcoded_text():
    at = _started_app()
    from models.enums import SpeakerRole

    director = at.session_state["_session_director"]
    rendered_speakers = [m.name for m in at.chat_message]
    backend_speakers = [m.speaker.value for m in director.conversation]
    assert rendered_speakers == backend_speakers


def test_moderator_message_appears_in_chat():
    at = _started_app()
    assert any(m.name == "moderator" for m in at.chat_message)


def test_shark_message_appears_in_chat():
    at = _started_app()
    assert any(m.name == "conservative_vc" for m in at.chat_message)


def test_founder_message_appears_in_chat_after_submission():
    at = _started_app()
    before = len(at.chat_message)
    _answer(at, "We already have three signed distributors.")
    after = [m for m in at.chat_message if m.name == "founder"]
    assert len(after) == 1
    assert len(at.chat_message) > before


def test_messages_appear_in_correct_order():
    at = _started_app()
    _answer(at, "answer one")
    director = at.session_state["_session_director"]
    turn_indices = [m.turn_index for m in director.conversation]
    assert turn_indices == sorted(turn_indices)


# ---------------------------------------------------------------------
# Input state (chat input gating)
# ---------------------------------------------------------------------


def test_founder_input_available_after_start():
    at = _started_app()
    assert at.chat_input(key="founder_chat_input").disabled is False


def test_founder_input_disabled_before_any_proposal():
    at = _new_app()
    at.run(timeout=15)
    assert at.chat_input(key="founder_chat_input").disabled is True


def test_submitting_response_then_input_reflects_next_turn():
    at = _started_app()
    _answer(at, "answer one")
    # A second Shark has now asked its question and it is the founder's
    # turn again -- input should be enabled, not left disabled.
    assert at.chat_input(key="founder_chat_input").disabled is False


def test_input_remains_unavailable_after_completion():
    at = _started_app()
    _answer(at, "a")
    _answer(at, "b")
    _answer(at, "c")
    assert at.session_state["current_phase"] == "session_complete"
    assert at.chat_input(key="founder_chat_input").disabled is True


# ---------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------


def test_session_reaches_session_complete():
    at = _started_app()
    _answer(at, "a")
    _answer(at, "b")
    _answer(at, "c")
    assert at.session_state["current_phase"] == "session_complete"


def test_running_flag_becomes_inactive_on_natural_completion():
    at = _started_app()
    _answer(at, "a")
    _answer(at, "b")
    _answer(at, "c")
    assert at.session_state["session_running"] is False


def test_completed_conversation_remains_visible():
    at = _started_app()
    _answer(at, "a")
    _answer(at, "b")
    _answer(at, "c")
    assert len(at.chat_message) > 0


def test_start_is_enabled_and_end_is_disabled_after_natural_completion():
    at = _started_app()
    _answer(at, "a")
    _answer(at, "b")
    _answer(at, "c")
    assert at.button(key="start_session_button").disabled is False
    assert at.button(key="end_session_button").disabled is True


def test_new_start_after_completion_clears_old_completed_session():
    at = _started_app()
    _answer(at, "a")
    _answer(at, "b")
    _answer(at, "c")
    old_director = at.session_state["_session_director"]

    at.button(key="start_session_button").click().run(timeout=15)

    assert not at.exception
    new_director = at.session_state["_session_director"]
    assert new_director is not old_director
    assert at.session_state["current_phase"] == "question_round"


# ---------------------------------------------------------------------
# Stop / reset
# ---------------------------------------------------------------------


def test_active_session_can_be_stopped():
    at = _started_app()
    assert at.button(key="end_session_button").disabled is False
    at.button(key="end_session_button").click().run(timeout=15)
    assert not at.exception
    assert at.session_state["current_phase"] == "idle"


def test_stop_clears_conversation_turn_and_director_state():
    at = _started_app()
    at.button(key="end_session_button").click().run(timeout=15)
    assert at.session_state["_session_director"] is None
    # The example placeholder transcript is reseeded once history is
    # empty -- confirm it's the example, not leftover real messages.
    from ui.conversation import get_example_conversation

    example_speakers = [m.speaker for m in get_example_conversation()]
    current_speakers = [m.speaker for m in at.session_state["conversation_history"]]
    assert current_speakers == example_speakers


def test_end_session_disabled_while_idle():
    at = _new_app()
    at.run(timeout=15)
    assert at.button(key="end_session_button").disabled is True


def test_new_session_works_after_stop():
    at = _started_app()
    at.button(key="end_session_button").click().run(timeout=15)
    at.text_area[0].set_value("Another pitch entirely.").run(timeout=15)
    at.button(key="start_session_button").click().run(timeout=15)
    assert not at.exception
    assert at.session_state["current_phase"] == "question_round"


# ---------------------------------------------------------------------
# HTML safety (Release 0.4.1 spec section A5)
# ---------------------------------------------------------------------


def test_founder_proposal_html_is_escaped_not_interpreted():
    """A founder typing an HTML tag into the proposal box must see it
    rendered as literal text in the locked "Submitted Proposal" summary,
    not interpreted as markup -- ui.proposal._render_locked_proposal_summary()
    renders that text with unsafe_allow_html=True for shared card
    styling, so it must escape the text first."""
    at = _new_app()
    at.run(timeout=15)
    at.text_area[0].set_value("<b>bold</b> and <script>alert(1)</script>").run(timeout=15)
    at.button(key="start_session_button").click().run(timeout=15)
    assert not at.exception

    markdown_html = "".join(m.value for m in at.markdown)
    assert "&lt;script&gt;" in markdown_html
    assert "<script>alert(1)</script>" not in markdown_html


def test_pdf_upload_extracts_real_text_not_just_filename():
    """Release 0.6: a PDF's actual text content must reach
    `proposal_content`, not just its filename (spec Part P)."""
    import io

    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "We sell eco-friendly packaging to grocery chains.")
    c.save()
    pdf_bytes = buf.getvalue()

    at = _new_app()
    at.run(timeout=15)
    at.radio[0].set_value("PDF").run(timeout=15)
    at.file_uploader[0].upload("pitch.pdf", pdf_bytes, "application/pdf").run(timeout=15)

    assert not at.exception
    assert "eco-friendly packaging" in at.session_state["proposal_content"]
    assert at.session_state["proposal_content"] != "pitch.pdf"
    assert at.session_state["proposal_uploaded"] is True


def test_pdf_with_no_extractable_text_is_not_marked_uploaded():
    """A scanned/blank PDF must not silently pass through as an
    accepted empty proposal (spec Part P/Q)."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    import io

    buf = io.BytesIO()
    writer.write(buf)
    blank_pdf_bytes = buf.getvalue()

    at = _new_app()
    at.run(timeout=15)
    at.radio[0].set_value("PDF").run(timeout=15)
    at.file_uploader[0].upload("blank.pdf", blank_pdf_bytes, "application/pdf").run(timeout=15)

    assert not at.exception
    assert at.session_state["proposal_uploaded"] is False
    assert at.button(key="start_session_button").disabled is True
