from venus_node.voice.conversation import VoiceChat


def test_voice_chat_continues_the_chat_core_made():
    calls = []

    def fake_chat(message, conversation_id):
        calls.append((message, conversation_id))
        return {"reply": f"ok {len(calls)}", "conversation_id": "c1"}

    voice = VoiceChat(fake_chat)

    assert voice.ask("open spotify") == "ok 1"
    assert voice.ask("now youtube") == "ok 2"
    # First message starts a chat; the next one continues it.
    assert calls == [("open spotify", None), ("now youtube", "c1")]


def test_voice_chat_empty_reply_is_empty_text():
    voice = VoiceChat(lambda message, conversation_id: {"reply": None, "conversation_id": "c1"})

    assert voice.ask("hmm") == ""
