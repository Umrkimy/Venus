import numpy as np

from venus_node.voice.orb import Orb, motion
from venus_node.voice.status import IDLE, LISTENING, SLEEPING, SPEAKING, THINKING


def test_orb_is_invisible_when_idle():
    pixels = Orb(size=64, count=200).frame(IDLE, 1.0, 0.5)

    assert pixels.shape == (64, 64, 4)
    assert pixels[..., 3].max() == 0


def test_orb_frame_is_premultiplied_bgra():
    pixels = Orb(size=64, count=200).frame(LISTENING, 0.5, 0.3)

    assert pixels.dtype == np.uint8
    assert pixels[..., 3].max() > 0
    # Premultiplied: no color brighter than its own opacity.
    assert (pixels[..., :3].max(axis=2) <= pixels[..., 3]).all()


def test_your_voice_makes_the_orb_ripple_more():
    assert motion(LISTENING, 1.0, 0.0).wobble > motion(LISTENING, 0.0, 0.0).wobble


def test_louder_voice_makes_the_orb_bigger():
    assert motion(LISTENING, 1.0, 0.0).scale > motion(LISTENING, 0.0, 0.0).scale + 0.1


def test_thinking_spins_faster_than_listening():
    assert motion(THINKING, 0.0, 0.0).spin > motion(LISTENING, 0.0, 0.0).spin


def test_sleeping_orb_is_small_and_dim():
    sleeping, awake = motion(SLEEPING, 0.0, 0.0), motion(LISTENING, 0.0, 0.0)

    assert sleeping.scale < awake.scale and sleeping.glow < awake.glow


def test_orb_stays_inside_its_window_at_full_voice():
    orb = Orb(size=96)
    for state in (LISTENING, THINKING, SPEAKING):
        for seconds in (0.0, 0.2, 0.45, 1.3):
            alpha = orb.frame(state, 1.0, seconds)[..., 3]
            # Only the soft halo may reach the outermost pixels, never solid dots.
            edge = np.concatenate([alpha[0], alpha[-1], alpha[:, 0], alpha[:, -1]])
            assert edge.max() < 40
